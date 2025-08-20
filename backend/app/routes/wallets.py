# app/api/routes/wallet.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.session import get_db
from app.db import data_model as models
from app.schemas.wallet_schema import WalletResponse
from app.auth import get_current_user

router = APIRouter()


# ---- Get current user's wallet info ----
@router.get("/me", response_model=WalletResponse)
def get_my_wallet(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


# ---- Top-up wallet balance ----
@router.post("/topup")
async def topup_wallet(
    amount: Decimal,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet.balance += float(amount)
    db.commit()
    db.refresh(wallet)

    return {"message": f"Wallet topped up by {amount}", "balance": wallet.balance}


# ---- Deduct wallet balance ----
@router.post("/deduct")
async def deduct_wallet(
    amount: Decimal,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if wallet.balance < float(amount):
        raise HTTPException(status_code=400, detail="Insufficient balance")

    wallet.balance -= float(amount)
    db.commit()
    db.refresh(wallet)

    return {"message": f"Wallet deducted by {amount}", "balance": wallet.balance}


# ---- Add BTC holdings ----
@router.post("/add_btc")
async def add_btc(
    quantity: Decimal,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet.holdings += float(quantity)
    db.commit()
    db.refresh(wallet)

    return {
        "message": f"Added Wallet holdings by {quantity} BTC",
        "holdings": wallet.holdings,
    }


# ---- Withdraw BTC holdings ----
@router.post("/withdraw_btc")
async def withdraw_btc(
    quantity: Decimal,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    wallet = (
        db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if wallet.holdings < float(quantity):
        raise HTTPException(status_code=400, detail="Insufficient Assets")

    wallet.holdings -= float(quantity)
    db.commit()
    db.refresh(wallet)

    return {
        "message": f"Added Wallet holdings by {quantity} BTC",
        "holdings": wallet.holdings,
    }
