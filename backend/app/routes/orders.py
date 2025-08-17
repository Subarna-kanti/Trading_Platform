# app/routes/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import data_model as models
from app.schemas import order_schema as schemas
from app.websocket import broadcast_wallet_update
from app.core import order_matching

router = APIRouter()


@router.post("/", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == order.user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Reserve funds for limit BUY
    remaining_quantity = order.quantity
    if order.type == models.OrderType.buy:
        if order.order_type == "limit":
            if not order.price:
                raise HTTPException(status_code=400, detail="Price required for limit buy")
            total_cost = order.price * order.quantity
            if wallet.balance < total_cost:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            wallet.balance -= total_cost
            wallet.reserved_balance += total_cost
            db.commit()

    db_order = models.Order(**order.dict(), remaining_quantity=remaining_quantity)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Broadcast wallet after reserving
    await broadcast_wallet_update(wallet.user_id, wallet.balance, wallet.reserved_balance)

    # Match orders
    order_matching.match_orders(db, db_order)

    return db_order


@router.get("/", response_model=list[schemas.OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).all()
    return orders
