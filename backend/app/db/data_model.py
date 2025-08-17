from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Enum,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


# --- Enum for order type ---
class OrderType(enum.Enum):
    buy = "buy"
    sell = "sell"


class StatusType(enum.Enum):
    pending = "pending"
    executed = "executed"
    cancelled = "cancelled"


# --- Users Table ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="trader", nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    orders = relationship("Order", back_populates="user")


# --- Orders Table ---
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(Enum(OrderType, native_enum=False), nullable=False)
    order_type = Column(String(20), default="limit")  # 'limit' or 'market'
    price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    status = Column(Enum(StatusType, native_enum=False), default=StatusType.pending)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    buy_trades = relationship(
        "Trade", back_populates="buy_order", foreign_keys="Trade.buy_order_id"
    )
    sell_trades = relationship(
        "Trade", back_populates="sell_order", foreign_keys="Trade.sell_order_id"
    )

    def __repr__(self):
        return f"<Order(id={self.id}, type={self.type}, status={self.status})>"


# --- Trades Table ---
class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    buy_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sell_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    executed_at = Column(DateTime, server_default=func.now())

    buy_order = relationship(
        "Order", foreign_keys=[buy_order_id], back_populates="buy_trades"
    )
    sell_order = relationship(
        "Order", foreign_keys=[sell_order_id], back_populates="sell_trades"
    )


# --- Connect to PostgreSQL ---
engine = create_engine(
    "postgresql+psycopg2://trading_user:trade@localhost/trading_platform"
)

# --- Create all tables if they do not exist ---
Base.metadata.create_all(engine)

print("Tables created successfully (if they did not exist).")
