from sqlalchemy.orm import Session
from app.db import data_model as models
from app.websocket import broadcast_wallet_update, broadcast_trade_update
import asyncio


async def match_orders(db: Session, new_order: models.Order):
    """
    Match the new order against existing orders.
    """
    if new_order.type == models.OrderType.buy:
        opposite_orders = (
            db.query(models.Order)
            .filter(
                models.Order.type == models.OrderType.sell,
                models.Order.status == models.StatusType.pending,
            )
            .order_by(models.Order.price.asc(), models.Order.created_at.asc())
            .all()
        )
    else:
        opposite_orders = (
            db.query(models.Order)
            .filter(
                models.Order.type == models.OrderType.buy,
                models.Order.status == models.StatusType.pending,
            )
            .order_by(models.Order.price.desc(), models.Order.created_at.asc())
            .all()
        )

    for order in opposite_orders:
        if new_order.status != models.StatusType.pending:
            break

        # Determine if prices match (for limit orders)
        if new_order.order_type == "limit" and order.order_type == "limit":
            if new_order.type == models.OrderType.buy and new_order.price < order.price:
                continue
            if (
                new_order.type == models.OrderType.sell
                and new_order.price > order.price
            ):
                continue

        trade_qty = min(new_order.quantity, order.quantity)
        trade_price = (
            order.price
            if order.order_type == "limit"
            else new_order.price or order.price
        )

        # Update quantities
        new_order.quantity -= trade_qty
        order.quantity -= trade_qty

        # Mark orders executed if fully filled
        if new_order.quantity == 0:
            new_order.status = models.StatusType.executed
        if order.quantity == 0:
            order.status = models.StatusType.executed

        # Update wallets
        buyer_order = new_order if new_order.type == models.OrderType.buy else order
        seller_order = new_order if new_order.type == models.OrderType.sell else order

        buyer_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == buyer_order.user_id)
            .first()
        )
        seller_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == seller_order.user_id)
            .first()
        )

        total_cost = trade_qty * trade_price
        buyer_wallet.holdings += trade_qty
        seller_wallet.balance += total_cost

        # Save trade
        trade = models.Trade(
            buy_order_id=buyer_order.id,
            sell_order_id=seller_order.id,
            price=trade_price,
            quantity=trade_qty,
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)

        # Broadcast updates
        await broadcast_wallet_update(
            buyer_wallet.user_id, buyer_wallet.balance, buyer_wallet.holdings
        )
        await broadcast_wallet_update(
            seller_wallet.user_id, seller_wallet.balance, seller_wallet.holdings
        )
        await broadcast_trade_update(trade.id, trade_price, trade_qty)

        # Commit updated orders
        db.commit()
