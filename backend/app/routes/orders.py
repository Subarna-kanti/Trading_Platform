from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal


from app.db.session import get_db
from app.db import data_model as models
from app.schemas import order_schema as schemas
from app.auth import get_current_user, get_current_admin
from app.core.broadcasts import get_order_book_snapshot, broadcast_order_book

router = APIRouter()


# ---- Create an order (user only) ----
@router.post("/", response_model=schemas.OrderResponse)
async def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    try:
        # ---- Buy order ----
        if order.type == models.OrderType.buy:
            if order.order_kind == schemas.OrderKind.limit:
                if order.price is None:
                    raise HTTPException(
                        status_code=400, detail="Price required for limit buy"
                    )
                total_cost = Decimal(order.price) * Decimal(order.quantity)
                if Decimal(wallet.balance) < total_cost:
                    raise HTTPException(status_code=400, detail="Insufficient balance")
                wallet.balance -= float(total_cost)
                wallet.reserved_balance += float(total_cost)
            else:
                raise HTTPException(
                    status_code=400, detail="Market buy not implemented yet"
                )

        # ---- Sell order ----
        elif order.type == models.OrderType.sell:
            if Decimal(wallet.holdings) < Decimal(order.quantity):
                raise HTTPException(
                    status_code=400, detail="Insufficient asset holdings"
                )
            wallet.holdings -= order.quantity
            wallet.reserved_holdings += order.quantity

        # ---- Save order ----
        db_order = models.Order(
            **order.model_dump(), remaining_quantity=order.quantity, status="pending"
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        # ---- Broadcast updated order book ----
        order_book = get_order_book_snapshot(db)
        broadcast_order_book(order_book)

        return db_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ---- Get a single order (user or admin) ----
@router.get("order_id/{order_id}", response_model=schemas.OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role != "admin" and db_order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db_order


# ---- List current user's orders ----
@router.get("/me", response_model=List[schemas.OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Order).filter(models.Order.user_id == current_user.id).all()


# ---- List all orders (admin only) ----
@router.get("/all", response_model=List[schemas.OrderResponse])
def list_all_orders(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    return db.query(models.Order).all()


# ---- Cancel an order (user/admin) ----
@router.delete("/{order_id}")
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only owner or admin can cancel
    if current_user.role != "admin" and db_order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == db_order.user_id)
        .first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    try:
        # ---- Release reserved balances ----
        if db_order.type == models.OrderType.buy:
            if db_order.price is None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot cancel market order with undefined price",
                )
            total_cost = db_order.price * db_order.remaining_quantity
            wallet.balance += total_cost
            wallet.reserved_balance -= total_cost
        elif db_order.type == models.OrderType.sell:
            wallet.holdings += db_order.remaining_quantity
            wallet.reserved_holdings -= db_order.remaining_quantity

        # ---- Delete the order ----
        db.delete(db_order)
        db.commit()

        # ---- Broadcast updated order book ----
        order_book = get_order_book_snapshot(db)
        broadcast_order_book(order_book)

        return {"message": "Order cancelled successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cancelling order: {str(e)}")
