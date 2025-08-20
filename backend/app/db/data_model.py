# app/db/data_model.py
from sqlalchemy import (
    Column,
    Float,
    String,
    Enum,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()


# ---- ENUMS ----
class OrderType(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class StatusType(str, enum.Enum):
    pending = "pending"
    executed = "executed"
    canceled = "canceled"


# ---- USER ----
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # One-to-one wallet
    wallet = relationship(
        "Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-many orders
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")


# ---- WALLET ----
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    balance = Column(Float, default=0.0)  # fiat balance
    reserved_balance = Column(Float, default=0.0)  # locked for pending buy orders
    holdings = Column(Float, default=0.0)  # asset balance
    reserved_holdings = Column(Float, default=0.0)  # locked for pending sell orders

    currency = Column(String, default="USD")
    asset_symbol = Column(String, default="BTC")

    user = relationship("User", back_populates="wallet")


# ---- ORDER ----
class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    type = Column(Enum(OrderType), nullable=False)  # buy / sell
    order_kind = Column(String, default="limit")  # "limit" or "market"
    price = Column(Float, nullable=True)  # nullable for market orders
    quantity = Column(Float, nullable=False)
    remaining_quantity = Column(Float, nullable=False)  # tracks partial fills
    status = Column(Enum(StatusType), default=StatusType.pending)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")

    # trades referencing this order
    buy_trades = relationship(
        "Trade", foreign_keys="[Trade.buy_order_id]", back_populates="buy_order"
    )
    sell_trades = relationship(
        "Trade", foreign_keys="[Trade.sell_order_id]", back_populates="sell_order"
    )


# ---- TRADE ----
class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    buy_order_id = Column(
        String, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    sell_order_id = Column(
        String, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )

    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    buy_order = relationship(
        "Order", foreign_keys=[buy_order_id], back_populates="buy_trades"
    )
    sell_order = relationship(
        "Order", foreign_keys=[sell_order_id], back_populates="sell_trades"
    )
