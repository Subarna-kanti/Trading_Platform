from pydantic import BaseModel
from datetime import datetime
from app.schemas.user_schema import UserBasic


# ---- Base ----
class TradeBase(BaseModel):
    price: float
    quantity: float


# ---- Create ----
class TradeCreate(TradeBase):
    buy_order_id: str
    sell_order_id: str


# ---- Full Response (with nested buyer/seller) ----
class TradeResponse(TradeBase):
    id: str
    buy_order_id: str
    sell_order_id: str
    created_at: datetime

    # Nested buyer/seller (lightweight, avoids full order nesting)
    buyer: UserBasic
    seller: UserBasic

    model_config = {"from_attributes": True}

