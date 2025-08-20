from pydantic import BaseModel
from decimal import Decimal
from typing import Optional


# ---- Base ----
class WalletBase(BaseModel):
    balance: Decimal = Decimal(0)
    reserved_balance: Decimal = Decimal(0)
    holdings: Decimal = Decimal(0)
    reserved_holdings: Decimal = Decimal(0)
    currency: str = "USD"
    asset_symbol: str = "BTC"


# ---- Create ----
class WalletCreate(WalletBase):
    user_id: str


# ---- Update ----
class WalletUpdate(BaseModel):
    balance: Optional[Decimal] = None
    reserved_balance: Optional[Decimal] = None
    holdings: Optional[Decimal] = None
    currency: Optional[str] = None
    asset_symbol: Optional[str] = None


# ---- Response ----
class WalletResponse(WalletBase):
    id: str
    user_id: str

    model_config = {"from_attributes": True}
