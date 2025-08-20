# app/core/order_matching.py
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.db import data_model as models
from decimal import Decimal


def _best_opposite_query(db: Session, side, order_kind_field="order_kind"):
    """
    Returns a query for the best opposite pending order with FOR UPDATE SKIP LOCKED.
    We fetch only ONE row (the best) each loop.
    """

    base_query = (
        db.query(models.Order)
        .filter(
            models.Order.status == models.StatusType.pending
        )  # ✅ only pending orders
        .with_for_update(skip_locked=True)
    )

    if side == models.OrderType.buy:
        # new is BUY -> we need best SELL (lowest price first, FIFO on tie)
        q = base_query.filter(models.Order.type == models.OrderType.sell).order_by(
            asc(models.Order.price), asc(models.Order.created_at)
        )
    else:
        # new is SELL -> we need best BUY (highest price first, FIFO on tie)
        q = base_query.filter(models.Order.type == models.OrderType.buy).order_by(
            desc(models.Order.price), asc(models.Order.created_at)
        )
    return q


def _compatible_prices(new_order: models.Order, opp: models.Order) -> bool:
    """Return True if limit prices cross or if either is market."""
    nk = getattr(new_order, "order_kind", "limit")
    ok = getattr(opp, "order_kind", "limit")

    # If both market: you need a price discovery rule. We choose to **not** match.
    if nk == "market" and ok == "market":
        return False

    # If either is market: always compatible
    if nk == "market" or ok == "market":
        return True

    # Both limit: must cross
    if new_order.type == models.OrderType.buy:
        return Decimal(str(new_order.price)) >= Decimal(str(opp.price))
    else:
        return Decimal(str(new_order.price)) <= Decimal(str(opp.price))


def _execution_price(new_order: models.Order, opp: models.Order) -> Decimal:
    """
    Price rules:
      - If opposite is limit -> trade at opposite's price.
      - Else if new is limit  -> trade at new's price.
      - Else (both market)    -> should not happen (blocked earlier).
    """
    nk = getattr(new_order, "order_kind", "limit")
    ok = getattr(opp, "order_kind", "limit")

    if ok == "limit":
        return Decimal(str(opp.price))
    if nk == "limit":
        return Decimal(str(new_order.price))
    raise ValueError("Both orders are market; no execution price defined.")


def match_orders(db: Session, new_order: models.Order):
    """
    Match a newly inserted order against the opposite side atomically and safely.
    Assumes the order has already reserved funds/holdings at placement time.
    """

    # We collect async broadcasts to run after commit
    wallet_broadcasts = []
    trade_broadcasts = []
    executed_trades = []
    order_book_broadcast = None

    # Lock the new order row to stabilize its state during matching
    new_order = (
        db.query(models.Order)
        .filter(models.Order.id == new_order.id)
        .with_for_update()
        .one()
    )

    # Keep matching while we still have quantity
    while (
        new_order.status == models.StatusType.pending
        and new_order.remaining_quantity > 0
    ):
        # Fetch the single best opposite order with row lock
        opp = _best_opposite_query(db, new_order.type).first()
        if not opp:
            break  # no liquidity on the other side

        # If both are market or prices don’t cross, skip this opposite and exit
        if not _compatible_prices(new_order, opp):
            # If both are limit but don't cross, no further matches possible
            nk = getattr(new_order, "order_kind", "limit")
            ok = getattr(opp, "order_kind", "limit")
            if nk == "limit" and ok == "limit":
                break
            # If both market was the case, also break because incompatible
            break

        # Determine trade quantity and price
        trade_qty = min(
            Decimal(str(new_order.remaining_quantity)),
            Decimal(str(opp.remaining_quantity)),
        )
        if trade_qty <= 0:
            break

        trade_price = _execution_price(new_order, opp)
        total_cost = trade_price * trade_qty

        # Identify buyer/seller orders for wallet effects
        buy_order = new_order if new_order.type == models.OrderType.buy else opp
        sell_order = new_order if new_order.type == models.OrderType.sell else opp

        if buy_order.user_id == sell_order.user_id:
            continue

        # Lock the two wallets we are about to mutate
        buyer_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == buy_order.user_id)
            .with_for_update()
            .one_or_none()
        )
        seller_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == sell_order.user_id)
            .with_for_update()
            .one_or_none()
        )

        # --- Sanity checks to avoid negatives (should be guaranteed by placement) ---
        if buyer_wallet:
            if Decimal(str(buyer_wallet.reserved_balance)) < total_cost:
                # Not enough reserved USD — abort this match cleanly
                break
        else:
            break  # cannot settle

        if seller_wallet:
            if Decimal(str(seller_wallet.reserved_holdings)) < trade_qty:
                # Not enough reserved asset — abort this match
                break
        else:
            break  # cannot settle

        # --- Create trade record ---
        trade = models.Trade(
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            price=float(trade_price),
            quantity=float(trade_qty),
        )
        executed_trades.append(trade)
        db.add(trade)
        db.flush()  # get trade.id

        # --- Update order fills ---
        new_order.remaining_quantity = float(
            Decimal(str(new_order.remaining_quantity)) - trade_qty
        )
        opp.remaining_quantity = float(Decimal(str(opp.remaining_quantity)) - trade_qty)

        if new_order.remaining_quantity <= 0:
            new_order.status = models.StatusType.executed
        if opp.remaining_quantity <= 0:
            opp.status = models.StatusType.executed

        # --- Wallet transfers ---
        # Buyer pays USD (reserved_balance ↓), receives asset (holdings ↑)
        buyer_wallet.reserved_balance = float(
            Decimal(str(buyer_wallet.reserved_balance)) - total_cost
        )
        buyer_wallet.holdings = float(Decimal(str(buyer_wallet.holdings)) + trade_qty)

        # Seller delivers asset (reserved_holdings ↓), receives USD (balance ↑)
        seller_wallet.reserved_holdings = float(
            Decimal(str(seller_wallet.reserved_holdings)) - trade_qty
        )
        seller_wallet.balance = float(Decimal(str(seller_wallet.balance)) + total_cost)

        db.flush()

        # Queue async broadcasts for after commit
        trade_broadcasts.append((trade.id, float(trade_price), float(trade_qty)))
        wallet_broadcasts.append(
            (
                buyer_wallet.user_id,
                buyer_wallet.balance,
                buyer_wallet.reserved_balance,
                buyer_wallet.holdings,
                buyer_wallet.reserved_holdings,
            )
        )
        wallet_broadcasts.append(
            (
                seller_wallet.user_id,
                seller_wallet.balance,
                seller_wallet.reserved_balance,
                seller_wallet.holdings,
                seller_wallet.reserved_holdings,
            )
        )

        # If new_order is done, stop matching
        if new_order.status == models.StatusType.executed:
            break
    return executed_trades
