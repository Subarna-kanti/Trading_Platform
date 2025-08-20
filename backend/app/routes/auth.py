# app/api/routes/auth.py
from datetime import timedelta
from fastapi import Depends, HTTPException, status, APIRouter, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import data_model as models
from app.schemas import user_schema as schemas
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_token,
)
from app.core.config import settings

router = APIRouter()


# ---- Register (signup) ----
@router.post("/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role="user",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    wallet = models.Wallet(user_id=new_user.id, balance=0.0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    return new_user


# ---- Login ----
@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = (
        db.query(models.User).filter(models.User.username == form_data.username).first()
    )
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ---- Refresh token endpoint ----
@router.post("/refresh-token", response_model=schemas.Token)
async def refresh_token(refresh_token: str = Body(...), db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Issue new access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ---- Helpers ----
def get_user_by_id(user_id: int, db: Session) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


# ---- Dependency: get current user with auto-refresh ----
def get_current_user(
    token: str = Depends(settings.oauth2_scheme),
    refresh_token: str = None,
    db: Session = Depends(get_db),
) -> models.User:
    """
    Extract user from access token; if expired, auto-refresh using refresh token
    """
    try:
        payload = decode_token(token)
    except HTTPException:
        # Token expired: try refresh token
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Access token expired")
        payload = decode_token(refresh_token)
        user_id: str = payload.get("sub")
        user = get_user_by_id(int(user_id), db)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Issue new access token automatically
        new_access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        # Attach to response (client should read `X-New-Access-Token` header or body)
        user.new_access_token = new_access_token  # attach dynamically
        return user

    user_id: str = payload.get("sub")
    user = get_user_by_id(int(user_id), db)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---- Dependency: admin check ----
def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user
