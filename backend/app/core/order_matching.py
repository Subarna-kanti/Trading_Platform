# app/core/order_matching.py
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.db import data_model as models
from app.websocket import broadcast_wallet_update, broadcast_trade_update
import asyncio
from typing import List


class OrderMatchingEngine:
    """
    Simple matching engine for limit orders.
    Matches buy orders (highest price first) with sell orders (lowest price first).
    """

    def __init__(self, db: Session):
        self.db = db

    async def match_orders(self) -> List[models.Trade]:
        trades: List[models.Trade] = []

        # Fetch all pending buy and sell orders
        buy_orders = (
            self.db.query(models.Order)
            .filter(
                models.Order.type == models.OrderType.buy,
                models.Order.status == models.StatusType.pending,
            )
            .order_by(desc(models.Order.price), models.Order.created_at)
            .all()
        )
        sell_orders = (
            self.db.query(models.Order)
            .filter(
                models.Order.type == models.OrderType.sell,
                models.Order.status == models.StatusType.pending,
            )
            .order_by(asc(models.Order.price), models.Order.created_at)
            .all()
        )

        for buy in buy_orders:
            for sell in sell_orders:
                # Match only if buy price >= sell price
                if buy.price >= sell.price:
                    # Determine trade quantity
                    trade_qty = min(buy.quantity, sell.quantity)
                    trade_price = (
                        sell.price
                    )  # Price follows sell order (common convention)

                    # Create Trade
                    trade = models.Trade(
                        buy_order_id=buy.id,
                        sell_order_id=sell.id,
                        price=trade_price,
                        quantity=trade_qty,
                    )
                    self.db.add(trade)

                    # Update buy/sell orders
                    buy.quantity -= trade_qty
                    sell.quantity -= trade_qty

                    if buy.quantity == 0:
                        buy.status = models.StatusType.executed
                    if sell.quantity == 0:
                        sell.status = models.StatusType.executed

                    # Update wallets
                    buyer_wallet = (
                        self.db.query(models.Wallet)
                        .filter(models.Wallet.user_id == buy.user_id)
                        .first()
                    )
                    seller_wallet = (
                        self.db.query(models.Wallet)
                        .filter(models.Wallet.user_id == sell.user_id)
                        .first()
                    )

                    total_cost = trade_price * trade_qty

                    if buyer_wallet:
                        # Buyer's reserved funds decrease only for executed amount
                        buyer_wallet.balance -= 0  # Already reserved at order creation
                        # Optionally track holdings if implemented

                    if seller_wallet:
                        seller_wallet.balance += total_cost  # Seller receives money

                    self.db.commit()
                    self.db.refresh(trade)

                    # Broadcast updates
                    await broadcast_trade_update(trade.id, trade.price, trade.quantity)
                    if buyer_wallet:
                        await broadcast_wallet_update(buy.user_id, buyer_wallet.balance)
                    if seller_wallet:
                        await broadcast_wallet_update(
                            sell.user_id, seller_wallet.balance
                        )

                    trades.append(trade)

                    # Remove fully executed sell order from loop
                    if sell.quantity == 0:
                        sell_orders.remove(sell)

                    # Break if buy fully executed
                    if buy.quantity == 0:
                        break

        return trades


async def run_matching_loop(db: Session, interval: float = 1.0):
    """
    Optional: Background loop that continuously matches orders.
    """
    engine = OrderMatchingEngine(db)
    while True:
        await engine.match_orders()
        await asyncio.sleep(interval)
