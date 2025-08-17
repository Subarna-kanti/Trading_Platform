# app/core/order_matching.py
from sqlalchemy.orm import Session
from app.db import data_model as models
from app.websocket import broadcast_trade_update, broadcast_wallet_update


def match_orders(db: Session, new_order: models.Order):
    """
    Match incoming order against existing orders in the order book.
    Executes trades and updates order status and wallets.
    """
    # Determine opposite order type
    opposite_type = (
        models.OrderType.sell
        if new_order.type == models.OrderType.buy
        else models.OrderType.buy
    )

    # Fetch active opposite orders sorted by price & time
    if new_order.type == models.OrderType.buy:
        # Buy wants lowest sell price first
        opposite_orders = (
            db.query(models.Order)
            .filter(
                models.Order.type == opposite_type,
                models.Order.status == models.StatusType.pending,
            )
            .order_by(models.Order.price.asc(), models.Order.created_at.asc())
            .all()
        )
    else:
        # Sell wants highest buy price first
        opposite_orders = (
            db.query(models.Order)
            .filter(
                models.Order.type == opposite_type,
                models.Order.status == models.StatusType.pending,
            )
            .order_by(models.Order.price.desc(), models.Order.created_at.asc())
            .all()
        )

    for o_order in opposite_orders:
        # Only match if price conditions are met (for limit orders)
        if new_order.order_type == "limit" and o_order.order_type == "limit":
            if (
                new_order.type == models.OrderType.buy
                and new_order.price < o_order.price
            ):
                continue
            if (
                new_order.type == models.OrderType.sell
                and new_order.price > o_order.price
            ):
                continue

        # Determine trade quantity
        trade_qty = min(new_order.quantity, o_order.quantity)
        trade_price = (
            o_order.price if o_order.order_type == "limit" else new_order.price
        )

        # Create trade
        trade = models.Trade(
            buy_order_id=(
                new_order.id if new_order.type == models.OrderType.buy else o_order.id
            ),
            sell_order_id=(
                new_order.id if new_order.type == models.OrderType.sell else o_order.id
            ),
            price=trade_price,
            quantity=trade_qty,
        )
        db.add(trade)

        # Update orders quantity
        new_order.quantity -= trade_qty
        o_order.quantity -= trade_qty

        if o_order.quantity <= 0:
            o_order.status = models.StatusType.executed
        if new_order.quantity <= 0:
            new_order.status = models.StatusType.executed

        # Update wallets
        buy_order = new_order if new_order.type == models.OrderType.buy else o_order
        sell_order = new_order if new_order.type == models.OrderType.sell else o_order

        buyer_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == buy_order.user_id)
            .first()
        )
        seller_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == sell_order.user_id)
            .first()
        )

        total_cost = trade_price * trade_qty

        # Adjust buyer and seller balances
        if buyer_wallet:
            buyer_wallet.balance -= total_cost  # funds already reserved for limit buy
        if seller_wallet:
            seller_wallet.balance += total_cost

        db.commit()
        db.refresh(new_order)
        db.refresh(o_order)
        db.refresh(trade)

        # Broadcast trade & wallet updates
        import asyncio

        asyncio.create_task(broadcast_trade_update(trade.id, trade_price, trade_qty))
        if buyer_wallet:
            asyncio.create_task(
                broadcast_wallet_update(
                    buyer_wallet.user_id, buyer_wallet.balance, holdings=0
                )
            )
        if seller_wallet:
            asyncio.create_task(
                broadcast_wallet_update(
                    seller_wallet.user_id, seller_wallet.balance, holdings=0
                )
            )

        if new_order.quantity <= 0:
            break
