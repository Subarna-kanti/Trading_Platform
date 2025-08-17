# app/schemas/order_schema.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.db.data_model import OrderType, StatusType


class OrderBase(BaseModel):
    type: OrderType
    order_type: str = "limit"
    price: Optional[float] = None
    quantity: float


class OrderCreate(OrderBase):
    user_id: int


class OrderUpdate(BaseModel):
    price: Optional[float] = None
    quantity: Optional[float] = None
    status: Optional[StatusType] = None


class OrderResponse(OrderBase):
    id: int
    user_id: int
    status: StatusType
    remaining_quantity: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
