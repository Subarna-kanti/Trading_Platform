# app/db/data_model.py
from sqlalchemy import Column, Integer, Float, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class OrderType(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class StatusType(str, enum.Enum):
    pending = "pending"
    executed = "executed"
    canceled = "canceled"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    wallets = relationship("Wallet", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user")


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Float, default=0.0)
    reserved_balance = Column(
        Float, default=0.0
    )  # Funds reserved for pending buy orders
    user = relationship("User", back_populates="wallets")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(Enum(OrderType), nullable=False)
    order_type = Column(String, default="limit")  # "limit" or "market"
    price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    remaining_quantity = Column(Float, nullable=False)  # Tracks partial fills
    status = Column(Enum(StatusType), default=StatusType.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="orders")


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    buy_order_id = Column(Integer, ForeignKey("orders.id"))
    sell_order_id = Column(Integer, ForeignKey("orders.id"))
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
