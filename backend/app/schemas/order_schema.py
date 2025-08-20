# app/schemas/order_schema.py
from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum
from app.db.data_model import OrderType, StatusType
from app.schemas.user_schema import UserResponse


# ---- Order kind (market/limit) ----
class OrderKind(str, Enum):
    limit = "limit"
    market = "market"


# ---- Base order schema ----
class OrderBase(BaseModel):
    type: OrderType  # Enum: buy/sell from DB
    order_kind: OrderKind = OrderKind.limit
    price: Optional[float] = None
    quantity: float = Field(..., gt=0)  # quantity must be > 0

    @model_validator(mode="before")
    def check_price_for_limit_orders(cls, values):
        if isinstance(values, dict):
            order_kind = values.get("order_kind")
            price = values.get("price")
            if order_kind == OrderKind.limit and (price is None or price <= 0):
                raise ValueError("Price must be provided and > 0 for limit orders")
        return values


# ---- Create order ----
class OrderCreate(OrderBase):
    user_id: str


# ---- Update order ----
class OrderUpdate(BaseModel):
    price: Optional[float] = None
    quantity: Optional[float] = Field(None, gt=0)
    status: Optional[StatusType] = None

    @model_validator(mode="before")
    def validate_update(cls, values):
        price = values.get("price")
        quantity = values.get("quantity")
        if price is not None and price <= 0:
            raise ValueError("Price must be > 0")
        if quantity is not None and quantity <= 0:
            raise ValueError("Quantity must be > 0")
        return values


# ---- Response schema ----
class OrderResponse(OrderBase):
    id: str
    user_id: str
    status: StatusType
    remaining_quantity: float
    created_at: datetime
    updated_at: datetime

    # Nested user info
    user: UserResponse

    model_config = {"from_attributes": True}
