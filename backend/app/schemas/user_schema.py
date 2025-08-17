from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ---- User Base ----
class UserBase(BaseModel):
    username: str
    role: str = "trader"


# ---- Create ----
class UserCreate(UserBase):
    password: str


# ---- Update ----
class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


# ---- Response ----
class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
