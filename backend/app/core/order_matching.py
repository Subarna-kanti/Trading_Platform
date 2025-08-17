# app/core/order_matching.py
from sqlalchemy.orm import Session
from app.db import data_model as models
from app.websocket import broadcast_trade_update, broadcast_wallet_update
import asyncio


def match_orders(db: Session, new_order: models.Order):
    opposite_type = models.OrderType.sell if new_order.type == models.OrderType.buy else models.OrderType.buy

    if new_order.type == models.OrderType.buy:
        opposite_orders = (
            db.query(models.Order)
            .filter(models.Order.type == opposite_type, models.Order.status == models.StatusType.pending)
            .order_by(models.Order.price.asc(), models.Order.created_at.asc())
            .all()
        )
    else:
        opposite_orders = (
            db.query(models.Order)
            .filter(models.Order.type == opposite_type, models.Order.status == models.StatusType.pending)
            .order_by(models.Order.price.desc(), models.Order.created_at.asc())
            .all()
        )

    for o_order in opposite_orders:
        # Price match check
        if new_order.order_type == "limit" and o_order.order_type == "limit":
            if new_order.type == models.OrderType.buy and new_order.price < o_order.price:
                continue
            if new_order.type == models.OrderType.sell and new_order.price > o_order.price:
                continue

        trade_qty = min(new_order.remaining_quantity, o_order.remaining_quantity)
        trade_price = o_order.price if o_order.order_type == "limit" else new_order.price or o_order.price

        # Create trade
        trade = models.Trade(
            buy_order_id=new_order.id if new_order.type == models.OrderType.buy else o_order.id,
            sell_order_id=new_order.id if new_order.type == models.OrderType.sell else o_order.id,
            price=trade_price,
            quantity=trade_qty,
        )
        db.add(trade)

        # Update orders
        new_order.remaining_quantity -= trade_qty
        o_order.remaining_quantity -= trade_qty

        if o_order.remaining_quantity <= 0:
            o_order.status = models.StatusType.executed
        if new_order.remaining_quantity <= 0:
            new_order.status = models.StatusType.executed

        # Wallet updates
        buy_order = new_order if new_order.type == models.OrderType.buy else o_order
        sell_order = new_order if new_order.type == models.OrderType.sell else o_order

        buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == buy_order.user_id).first()
        seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == sell_order.user_id).first()

        total_cost = trade_price * trade_qty

        if buyer_wallet:
            # Deduct reserved_balance first
            buyer_wallet.reserved_balance -= total_cost
            # In case of market buy, deduct from balance if needed
            if buyer_wallet.reserved_balance < 0:
                buyer_wallet.balance += buyer_wallet.reserved_balance  # negative number
                buyer_wallet.reserved_balance = 0.0

        if seller_wallet:
            seller_wallet.balance += total_cost

        db.commit()
        db.refresh(new_order)
        db.refresh(o_order)
        db.refresh(trade)
        if buyer_wallet:
            db.refresh(buyer_wallet)
        if seller_wallet:
            db.refresh(seller_wallet)

        # Broadcast
        asyncio.create_task(broadcast_trade_update(trade.id, trade_price, trade_qty))
        if buyer_wallet:
            asyncio.create_task(
                broadcast_wallet_update(buyer_wallet.user_id, buyer_wallet.balance, buyer_wallet.reserved_balance)
            )
        if seller_wallet:
            asyncio.create_task(
                broadcast_wallet_update(seller_wallet.user_id, seller_wallet.balance, seller_wallet.reserved_balance)
            )

        if new_order.remaining_quantity <= 0:
            break
