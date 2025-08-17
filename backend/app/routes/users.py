from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import data_model as models
from app.schemas import user_schema as schemas
from app.websocket import broadcast_wallet_update  # broadcasting

router = APIRouter()


@router.post("/", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing_user = (
        db.query(models.User).filter(models.User.username == user.username).first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create new user (hashing can be added later)]
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    new_user = models.User(
        username=user.username,
        password_hash=pwd_context.hash(user.password), ## hashed password
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # --- Create wallet for the user ---
    wallet = models.Wallet(user_id=new_user.id, balance=0.0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    # Broadcast wallet creation
    await broadcast_wallet_update(new_user.id, wallet.balance)

    return new_user


@router.get("/", response_model=list[schemas.UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in user.dict(exclude_unset=True).items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)

    # Wallet unchanged; no broadcast needed
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete wallet first
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()
    if wallet:
        db.delete(wallet)

    db.delete(db_user)
    db.commit()

    # Broadcast wallet deletion
    await broadcast_wallet_update(user_id, 0.0)

    return {"message": "User and wallet deleted"}
