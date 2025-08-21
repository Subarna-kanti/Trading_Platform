# app/api/routes/users.py
import re
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import data_model as models
from app.schemas import user_schema as schemas
from app.auth import get_current_user, get_current_admin
from app.core.security import get_password_hash
from app.core.logs import logger


router = APIRouter()


# ---- Helper functions ----
def validate_email(email: str):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, email):
        raise HTTPException(status_code=400, detail="Invalid email format")


def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters long"
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter",
        )
    if not re.search(r"[0-9]", password):
        raise HTTPException(
            status_code=400, detail="Password must contain at least one number"
        )
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character",
        )


# ---- Create user (admin only) ----
@router.post("/", response_model=schemas.UserResponse)
async def create_user(
    user: schemas.UserCreate,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        if db.query(models.User).filter(models.User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(models.User).filter(models.User.email == user.email).first():
            raise HTTPException(status_code=400, detail="Email already exists")

        validate_email(user.email)
        validate_password(user.password)

        new_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
            role=user.role,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        wallet = models.Wallet(user_id=new_user.id, balance=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        return new_user
    except Exception as e:
        logger.error(f"❌ Error creating order: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ---- List users (admin only) ----
@router.get("/", response_model=list[schemas.UserResponse])
def list_users(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.User).all()


# ---- Get current user info (auto-refresh) ----
@router.get("/me", response_model=schemas.UserResponse)
def get_me(
    response: Response,
    current_user: models.User = Depends(get_current_user),
):
    try:
        # Attach new access token if auto-refreshed
        if hasattr(current_user, "new_access_token"):
            response.headers["X-New-Access-Token"] = current_user.new_access_token
        return current_user
    except Exception as e:
        logger.error(f"❌ Error fetching user details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ---- Update current user's own info (auto-refresh) ----
@router.put("/me", response_model=schemas.UserResponse)
async def update_me(
    user_update: schemas.UserSelfUpdate,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        update_data = user_update.model_dump(exclude_unset=True)

        if "password" in update_data:
            validate_password(update_data["password"])
            current_user.hashed_password = get_password_hash(
                update_data.pop("password")
            )
        if "email" in update_data:
            validate_email(update_data["email"])
            current_user.email = update_data.pop("email")

        db.commit()
        db.refresh(current_user)

        if hasattr(current_user, "new_access_token"):
            response.headers["X-New-Access-Token"] = current_user.new_access_token

        return current_user
    except Exception as e:
        logger.error(f"❌ Error updating user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ---- Update user (admin only) ----
@router.put("/update/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = user.model_dump(exclude_unset=True)
        if "password" in update_data:
            validate_password(update_data["password"])
            db_user.hashed_password = get_password_hash(update_data.pop("password"))
        if "email" in update_data:
            validate_email(update_data["email"])

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        logger.error(f"❌ Error Updating User: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ---- Delete user (admin only) ----
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        wallet = (
            db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()
        )
        if wallet:
            db.delete(wallet)

        db.delete(db_user)
        db.commit()
        return {"message": "User and wallet deleted"}
    except Exception as e:
        logger.error(f"❌ Error deleting order: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
