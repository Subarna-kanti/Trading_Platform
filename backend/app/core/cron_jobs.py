from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from app.db import data_model as models
from app.core.order_matching import match_orders
from app.core.broadcasts import (
    get_order_book_snapshot,
    broadcast_order_book,
    get_trade_snapshot,
    broadcast_trade_book,
)


def process_pending_orders_job():
    """Background cron job to process pending orders."""
    db = SessionLocal()
    try:
        pending_orders = (
            db.query(models.Order)
            .filter(models.Order.status == "pending")
            .order_by(models.Order.created_at.asc())
            .all()
        )

        total_trades = 0
        for order in pending_orders:
            trades = match_orders(db, order)
            db.commit()
            db.refresh(order)
            for t in trades:
                db.refresh(t)
            total_trades += len(trades)

        if total_trades > 0:
            # Broadcast after batch
            order_book = get_order_book_snapshot(db)
            broadcast_order_book(order_book)
            trade_book = get_trade_snapshot(db)
            broadcast_trade_book(trade_book)
    finally:
        db.close()
