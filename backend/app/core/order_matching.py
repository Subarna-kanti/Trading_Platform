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
    Scan the whole opposite order book once for this new_order.
    Match as much as possible in price-time priority.
    """

    wallet_broadcasts = []
    trade_broadcasts = []
    executed_trades = []

    # Lock the new order row
    new_order = (
        db.query(models.Order)
        .filter(models.Order.id == new_order.id)
        .with_for_update()
        .one()
    )

    # Fetch ALL opposite orders in priority order
    opposite_orders = _best_opposite_query(db, new_order.type).all()

    for opp in opposite_orders:
        if (
            new_order.status != models.StatusType.pending
            or new_order.remaining_quantity <= 0
        ):
            break  # new_order fully executed

        # Price compatibility check
        if not _compatible_prices(new_order, opp):
            break  # since book is sorted, no further orders can match

        # Skip self-trade (important: break, don’t continue → avoids infinite loop)
        if new_order.user_id == opp.user_id:
            continue

        trade_qty = min(
            Decimal(str(new_order.remaining_quantity)),
            Decimal(str(opp.remaining_quantity)),
        )
        if trade_qty <= 0:
            continue

        trade_price = _execution_price(new_order, opp)
        total_cost = trade_price * trade_qty

        # Identify buyer/seller
        buy_order = new_order if new_order.type == models.OrderType.buy else opp
        sell_order = new_order if new_order.type == models.OrderType.sell else opp

        # Lock wallets
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
        if not buyer_wallet or not seller_wallet:
            continue

        # Sanity checks
        if Decimal(str(buyer_wallet.reserved_balance)) < total_cost:
            continue
        if Decimal(str(seller_wallet.reserved_holdings)) < trade_qty:
            continue

        # --- Create trade ---
        trade = models.Trade(
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            price=float(trade_price),
            quantity=float(trade_qty),
        )
        executed_trades.append(trade)
        db.add(trade)
        db.flush()

        # --- Update orders ---
        new_order.remaining_quantity = float(
            Decimal(str(new_order.remaining_quantity)) - trade_qty
        )
        opp.remaining_quantity = float(Decimal(str(opp.remaining_quantity)) - trade_qty)
        if new_order.remaining_quantity <= 0:
            new_order.status = models.StatusType.executed
        if opp.remaining_quantity <= 0:
            opp.status = models.StatusType.executed

        # --- Wallet updates ---
        buyer_wallet.reserved_balance = float(
            Decimal(str(buyer_wallet.reserved_balance)) - total_cost
        )
        buyer_wallet.holdings = float(Decimal(str(buyer_wallet.holdings)) + trade_qty)
        seller_wallet.reserved_holdings = float(
            Decimal(str(seller_wallet.reserved_holdings)) - trade_qty
        )
        seller_wallet.balance = float(Decimal(str(seller_wallet.balance)) + total_cost)

        db.flush()

        # Queue broadcasts
        trade_broadcasts.append((trade.id, float(trade_price), float(trade_qty)))
        wallet_broadcasts.extend(
            [
                (
                    buyer_wallet.user_id,
                    buyer_wallet.balance,
                    buyer_wallet.reserved_balance,
                    buyer_wallet.holdings,
                    buyer_wallet.reserved_holdings,
                ),
                (
                    seller_wallet.user_id,
                    seller_wallet.balance,
                    seller_wallet.reserved_balance,
                    seller_wallet.holdings,
                    seller_wallet.reserved_holdings,
                ),
            ]
        )

    return executed_trades
