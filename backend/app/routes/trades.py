# backend/app/routes/trades.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import data_model as models
from app.auth import get_current_user
from app.core.order_matching import match_orders
from app.core.broadcasts import (
    broadcast_order_book,
    broadcast_trade_book,
    get_order_book_snapshot,
    get_trade_snapshot,
)


router = APIRouter()


# ---- Create a trade by executing an existing order against opposite order ----
@router.post("/")
async def create_trade(order_id: str, db: Session = Depends(get_db)):
    """
    Execute trades for a given order_id using the centralized match_orders logic.
    This ensures all wallet updates, order status, and trade broadcasting are handled consistently.
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Use core order matching logic
    trades = match_orders(db, db_order)

    # Refresh order after matching
    db.commit()
    db.refresh(db_order)
    for t in trades:
        db.refresh(t)

    # Broadcast updated order book after trades
    order_book = get_order_book_snapshot(db)
    broadcast_order_book(order_book)
    trade_book = get_trade_snapshot(db)
    broadcast_trade_book(trade_book)

    return JSONResponse(
        {
            "success": True,
            "trades_executed": len(trades),
            "order_id": order_id,
            "status": db_order.status,
        }
    )


# ---- Get current user's trades ----
@router.get("/my")
def get_my_trades(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Trades where user was buyer or seller
    trades = (
        db.query(models.Trade)
        .join(
            models.Order,
            (models.Trade.buy_order_id == models.Order.id)
            | (models.Trade.sell_order_id == models.Order.id),
        )
        .filter(models.Order.user_id == current_user.id)
        .all()
    )

    results = []
    for t in trades:
        # Check if current user was buyer or seller
        if t.buy_order.user_id == current_user.id:
            trade_type = "buy"
            client_name = t.sell_order.user.username  # other party
        else:
            trade_type = "sell"
            client_name = t.buy_order.user.username  # other party

        results.append(
            {
                "id": t.id,
                "client_name": client_name,
                "trade_type": trade_type,
                "price": t.price,
                "quantity": t.quantity,
                "created_at": t.created_at.isoformat(),
            }
        )

    return results
