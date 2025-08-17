# app/routes/wallets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import data_model as models
from app.schemas import wallet_schema as schemas
from app.websocket import broadcast_wallet_update

router = APIRouter()


@router.post("/", response_model=schemas.WalletResponse)
async def create_wallet(wallet: schemas.WalletCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == wallet.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(models.Wallet).filter(models.Wallet.user_id == wallet.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has a wallet")

    db_wallet = models.Wallet(user_id=wallet.user_id, balance=wallet.balance or 0.0)
    db.add(db_wallet)
    db.commit()
    db.refresh(db_wallet)

    await broadcast_wallet_update(wallet.user_id, db_wallet.balance, holdings=0)
    return db_wallet


@router.get("/{wallet_id}", response_model=schemas.WalletResponse)
def get_wallet(wallet_id: int, db: Session = Depends(get_db)):
    db_wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    if not db_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return db_wallet


@router.put("/{wallet_id}", response_model=schemas.WalletResponse)
async def update_wallet(wallet_id: int, wallet: schemas.WalletUpdate, db: Session = Depends(get_db)):
    db_wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    if not db_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    for field, value in wallet.dict(exclude_unset=True).items():
        setattr(db_wallet, field, value)

    db.commit()
    db.refresh(db_wallet)

    await broadcast_wallet_update(db_wallet.user_id, db_wallet.balance, holdings=0)
    return db_wallet


@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: int, db: Session = Depends(get_db)):
    db_wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    if not db_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    user_id = db_wallet.user_id
    db.delete(db_wallet)
    db.commit()

    await broadcast_wallet_update(user_id, 0.0, holdings=0)
    return {"message": "Wallet deleted"}
