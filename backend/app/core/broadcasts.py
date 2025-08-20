from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.ws_manager import manager
from app.db import data_model as models


async def broadcast_trade_book(trade_book: dict):
    await manager.broadcast(f"Top Trades: {trade_book}")


async def broadcast_order_book(order_book: dict):
    await manager.broadcast(f"Top Orders: {order_book}")


def get_order_book_snapshot(db: Session):
    """
    Returns current pending buy/sell orders (best price first).
    """
    buy_orders = (
        db.query(models.Order)
        .filter(
            models.Order.type == models.OrderType.buy,
            models.Order.status == models.StatusType.pending,
        )
        .order_by(models.Order.price.desc(), models.Order.created_at.asc())
        .limit(3)
        .all()
    )
    sell_orders = (
        db.query(models.Order)
        .filter(
            models.Order.type == models.OrderType.sell,
            models.Order.status == models.StatusType.pending,
        )
        .order_by(models.Order.price.asc(), models.Order.created_at.asc())
        .limit(3)
        .all()
    )

    def to_row(o):
        return {
            "price": o.price,
            "remaining_quantity": o.remaining_quantity,
            "created_at": o.created_at.isoformat(),
            "order_kind": getattr(o, "order_kind", "limit"),
        }

    return {
        "buy_orders": [to_row(o) for o in buy_orders],
        "sell_orders": [to_row(o) for o in sell_orders],
    }


def get_trade_snapshot(db: Session, limit=5):
    """
    Returns top trades globally sorted by total trade amount (price * quantity) using SQL.
    """
    trades = (
        db.query(
            models.Trade.price,
            models.Trade.quantity,
            (models.Trade.price * models.Trade.quantity).label("total_amount"),
            models.Trade.created_at,
        )
        .order_by(desc("total_amount"))
        .limit(limit)
        .all()
    )

    # Convert to list of dicts
    return [
        {
            "price": t.price,
            "quantity": t.quantity,
            "total_amount": t.total_amount,
            "created_at": t.created_at.isoformat(),
        }
        for t in trades
    ]
