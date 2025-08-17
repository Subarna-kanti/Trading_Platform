from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.data_model import OrderType, StatusType


# ---- Base ----
class OrderBase(BaseModel):
    type: OrderType
    order_type: str = "limit"
    price: Optional[float] = None
    quantity: float


# ---- Create ----
class OrderCreate(OrderBase):
    user_id: int


# ---- Update ----
class OrderUpdate(BaseModel):
    price: Optional[float] = None
    quantity: Optional[float] = None
    status: Optional[StatusType] = None


# ---- Response ----
class OrderResponse(OrderBase):
    id: int
    user_id: int
    status: StatusType
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
