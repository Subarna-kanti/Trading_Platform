# app/schemas/user_schema.py
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
import re


# ---- Common password validator ----
def validate_password(v: str) -> str:
    if v is None:
        return v
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("Password must contain at least one special character")
    return v


# ---- Token schema ----
class Token(BaseModel):
    access_token: str
    token_type: str


# ---- Base user schema ----
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: Optional[str] = "user"


# ---- User creation schema (used in signup + admin create) ----
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    _validate_password = field_validator("password")(validate_password)


# ---- Login schema ----
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


# ---- Basic user (for nested responses like Trade, Wallet) ----
class UserBasic(BaseModel):
    id: str
    username: str
    email: Optional[EmailStr] = None

    model_config = {"from_attributes": True}


# ---- Full user response ----
class UserResponse(UserBase):
    id: str
    model_config = {"from_attributes": True}


# ---- User update by admin ----
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[str] = None

    _validate_password = field_validator("password")(validate_password)


# ---- Self update schema (current user only) ----
class UserSelfUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)

    _validate_password = field_validator("password")(validate_password)
