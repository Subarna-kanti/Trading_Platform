from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.db import data_model as models
from app.schemas import trade_schema as schemas
from app.websocket import broadcast_wallet_update

router = APIRouter()


@router.post("/", response_model=schemas.TradeResponse)
async def create_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    # Validate buy and sell orders
    buy_order = (
        db.query(models.Order).filter(models.Order.id == trade.buy_order_id).first()
    )
    sell_order = (
        db.query(models.Order).filter(models.Order.id == trade.sell_order_id).first()
    )

    if not buy_order or not sell_order:
        raise HTTPException(status_code=400, detail="Invalid order IDs")

    # Validate wallets
    # buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == buy_order.user_id).first()
    # seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == sell_order.user_id).first()

    buy_order = (
        db.query(models.Order)
        .options(joinedload(models.Order.user))
        .get(trade.buy_order_id)
    )
    sell_order = (
        db.query(models.Order)
        .options(joinedload(models.Order.user))
        .get(trade.sell_order_id)
    )
    buyer_wallet = buy_order.user.wallet
    seller_wallet = sell_order.user.wallet

    if not buyer_wallet or not seller_wallet:
        raise HTTPException(status_code=404, detail="Buyer or seller wallet not found")

    total_cost = trade.price * trade.quantity

    if buyer_wallet.balance < total_cost:
        raise HTTPException(status_code=400, detail="Buyer has insufficient balance")

    # Deduct from buyer, add to seller
    buyer_wallet.balance -= total_cost
    seller_wallet.balance += total_cost

    # Create trade record
    db_trade = models.Trade(
        buy_order_id=trade.buy_order_id,
        sell_order_id=trade.sell_order_id,
        price=trade.price,
        quantity=trade.quantity,
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)

    # Broadcast wallet updates
    await broadcast_wallet_update(buy_order.user_id, buyer_wallet.balance)
    await broadcast_wallet_update(sell_order.user_id, seller_wallet.balance)

    return db_trade


@router.get("/", response_model=list[schemas.TradeResponse])
def list_trades(db: Session = Depends(get_db)):
    return db.query(models.Trade).all()


@router.get("/{trade_id}", response_model=schemas.TradeResponse)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    db_trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return db_trade
