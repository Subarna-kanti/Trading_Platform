from pydantic import BaseModel
from typing import Optional


# ---- Base ----
class WalletBase(BaseModel):
    user_id: int
    balance: float = 0.0


# ---- Create ----
class WalletCreate(WalletBase):
    pass


# ---- Update ----
class WalletUpdate(BaseModel):
    balance: Optional[float] = None


# ---- Response ----
class WalletResponse(WalletBase):
    id: int

    class Config:
        from_attributes = True
