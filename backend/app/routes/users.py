from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import data_model as models
from app.schemas import user_schema as schemas
from app.websocket import broadcast_wallet_update  # <- new import

router = APIRouter()


@router.post("/", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # check if username exists
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = models.User(
        username=user.username,
        password_hash=user.password,  # ⚠️ hashing to be added
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # --- create wallet for new user ---
    wallet = models.Wallet(user_id=new_user.id, balance=0.0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    # --- broadcast wallet creation event ---
    await broadcast_wallet_update(new_user.id, wallet.balance)

    return new_user


@router.get("/", response_model=list[schemas.UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).get(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).get(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in user.dict(exclude_unset=True).items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)

    # If password/role updates happen, wallet unchanged (no broadcast)
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).get(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # delete wallet first
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()
    if wallet:
        db.delete(wallet)

    db.delete(db_user)
    db.commit()

    # --- optionally broadcast wallet deletion event ---
    await broadcast_wallet_update(user_id, 0.0)

    return {"message": "User and wallet deleted"}
