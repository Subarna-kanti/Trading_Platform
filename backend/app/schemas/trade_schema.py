from pydantic import BaseModel
from datetime import datetime


# ---- Base ----
class TradeBase(BaseModel):
    buy_order_id: int
    sell_order_id: int
    price: float
    quantity: float


# ---- Create ----
class TradeCreate(TradeBase):
    pass


# ---- Response ----
class TradeResponse(TradeBase):
    id: int
    executed_at: datetime

    class Config:
        orm_mode = True
