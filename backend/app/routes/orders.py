from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import data_model as models
from app.schemas import order_schema as schemas
from app.websocket import broadcast_wallet_update

router = APIRouter()


@router.post("/", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch user wallet
    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == order.user_id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Reserve funds for BUY orders
    if order.type == models.OrderType.buy:
        if not order.price:
            raise HTTPException(
                status_code=400, detail="Price required for limit buy orders"
            )
        total_cost = order.price * order.quantity
        if wallet.balance < total_cost:
            raise HTTPException(
                status_code=400, detail="Insufficient balance to place buy order"
            )
        wallet.balance -= total_cost  # reserve funds

    db_order = models.Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Broadcast wallet update if funds reserved
    if order.type == models.OrderType.buy:
        await broadcast_wallet_update(order.user_id, wallet.balance)

    return db_order


@router.get("/", response_model=list[schemas.OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()


@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@router.put("/{order_id}", response_model=schemas.OrderResponse)
async def update_order(
    order_id: int, order: schemas.OrderUpdate, db: Session = Depends(get_db)
):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    for field, value in order.dict(exclude_unset=True).items():
        setattr(db_order, field, value)

    db.commit()
    db.refresh(db_order)

    # Optionally: handle wallet changes if order type/price/quantity changed
    # (currently not implemented)

    return db_order


@router.delete("/{order_id}")
async def delete_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Refund reserved balance for pending BUY orders
    if (
        db_order.type == models.OrderType.buy
        and db_order.status == models.StatusType.pending
    ):
        wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == db_order.user_id)
            .first()
        )
        if wallet:
            refund = db_order.price * db_order.quantity
            wallet.balance += refund
            await broadcast_wallet_update(db_order.user_id, wallet.balance)

    db.delete(db_order)
    db.commit()

    return {"message": "Order deleted"}
