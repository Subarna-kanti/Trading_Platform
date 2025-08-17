# test_order_matching.py

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from main import Base, match_orders, get_password_hash  # Import your models & match_orders
from models import User, Wallet, Order  # Adjust based on your project structure

DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # In-memory test DB

# --- Async DB Setup Fixture ---
@pytest.fixture(scope="module")
async def engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")
async def test_db(engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
        await session.rollback()

# --- Helper function ---
async def create_user_with_wallet(session, username, balance=0.0):
    user = User(username=username, password=get_password_hash("pass"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    wallet = Wallet(user_id=user.id, balance=balance, reserved_balance=0.0)
    session.add(wallet)
    await session.commit()
    await session.refresh(wallet)
    return user, wallet

# --- 1. User & Wallet Tests ---
@pytest.mark.asyncio
async def test_user_creation_duplicate_username(test_db):
    user1 = User(username="dupuser", password=get_password_hash("pass"))
    user2 = User(username="dupuser", password=get_password_hash("pass2"))
    test_db.add(user1)
    await test_db.commit()
    test_db.add(user2)
    with pytest.raises(Exception):
        await test_db.commit()

@pytest.mark.asyncio
async def test_wallet_negative_balance_prevention(test_db):
    user = User(username="wallet_user", password=get_password_hash("pass"))
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    wallet = Wallet(user_id=user.id, balance=-100.0, reserved_balance=0.0)
    test_db.add(wallet)
    with pytest.raises(Exception):
        await test_db.commit()

# --- 2. Limit Orders ---
@pytest.mark.asyncio
async def test_limit_order_zero_quantity(test_db):
    user, _ = await create_user_with_wallet(test_db, "zero_qty")
    order = Order(user_id=user.id, order_type="limit", side="buy", quantity=0, price=100.0, remaining_quantity=0)
    test_db.add(order)
    with pytest.raises(Exception):
        await test_db.commit()

@pytest.mark.asyncio
async def test_limit_order_negative_price(test_db):
    user, _ = await create_user_with_wallet(test_db, "neg_price")
    order = Order(user_id=user.id, order_type="limit", side="sell", quantity=5, price=-10, remaining_quantity=5)
    test_db.add(order)
    with pytest.raises(Exception):
        await test_db.commit()

# --- 3. Market Orders ---
@pytest.mark.asyncio
async def test_market_order_no_available_sell(test_db):
    buyer, _ = await create_user_with_wallet(test_db, "market_no_sell", balance=500.0)
    buy_order = Order(user_id=buyer.id, order_type="market", side="buy", quantity=10, price=None, remaining_quantity=10)
    test_db.add(buy_order)
    await test_db.commit()
    await test_db.refresh(buy_order)
    await match_orders(buy_order, test_db)
    await test_db.refresh(buy_order)
    assert buy_order.remaining_quantity == 10

# --- 4. Partial Fills ---
@pytest.mark.asyncio
async def test_partial_fill_multiple_orders(test_db):
    seller1, _ = await create_user_with_wallet(test_db, "partial_seller1")
    seller2, _ = await create_user_with_wallet(test_db, "partial_seller2")
    order1 = Order(user_id=seller1.id, order_type="limit", side="sell", quantity=3, price=50, remaining_quantity=3)
    order2 = Order(user_id=seller2.id, order_type="limit", side="sell", quantity=4, price=50, remaining_quantity=4)
    test_db.add_all([order1, order2])
    await test_db.commit()
    await test_db.refresh(order1)
    await test_db.refresh(order2)

    buyer, buyer_wallet = await create_user_with_wallet(test_db, "partial_buyer", balance=1000.0)
    buy_order = Order(user_id=buyer.id, order_type="market", side="buy", quantity=5, price=None, remaining_quantity=5)
    test_db.add(buy_order)
    await test_db.commit()
    await test_db.refresh(buy_order)
    await match_orders(buy_order, test_db)
    await test_db.refresh(order1)
    await test_db.refresh(order2)
    await test_db.refresh(buy_order)
    await test_db.refresh(buyer_wallet)

    assert buy_order.remaining_quantity == 0
    assert order1.remaining_quantity == 0
    assert order2.remaining_quantity == 2
    assert buyer_wallet.balance == 1000 - 5*50

# --- 5. Concurrency / Race Conditions ---
@pytest.mark.asyncio
async def test_concurrent_orders(test_db):
    seller, _ = await create_user_with_wallet(test_db, "concurrent_seller")
    sell_order = Order(user_id=seller.id, order_type="limit", side="sell", quantity=10, price=20, remaining_quantity=10)
    test_db.add(sell_order)
    await test_db.commit()
    await test_db.refresh(sell_order)

    async def place_buy(user_name, qty):
        buyer, buyer_wallet = await create_user_with_wallet(test_db, user_name, balance=200.0)
        buy_order = Order(user_id=buyer.id, order_type="market", side="buy", quantity=qty, price=None, remaining_quantity=qty)
        test_db.add(buy_order)
        await test_db.commit()
        await test_db.refresh(buy_order)
        await match_orders(buy_order, test_db)
        await test_db.refresh(buyer_wallet)
        return buy_order, buyer_wallet

    results = await asyncio.gather(
        place_buy("buyer1", 6),
        place_buy("buyer2", 6)
    )
    total_bought = sum(10 - r[0].remaining_quantity for r in results)
    assert total_bought == 10

# --- 6. Edge Cases ---
@pytest.mark.asyncio
async def test_overdraw_buy(test_db):
    buyer, wallet = await create_user_with_wallet(test_db, "overdraw_buyer", balance=50.0)
    seller, _ = await create_user_with_wallet(test_db, "overdraw_seller")
    sell_order = Order(user_id=seller.id, order_type="limit", side="sell", quantity=2, price=100, remaining_quantity=2)
    test_db.add(sell_order)
    await test_db.commit()
    await test_db.refresh(sell_order)

    buy_order = Order(user_id=buyer.id, order_type="market", side="buy", quantity=2, price=None, remaining_quantity=2)
    test_db.add(buy_order)
    await test_db.commit()
    await test_db.refresh(buy_order)

    await match_orders(buy_order, test_db)
    await test_db.refresh(wallet)
    assert wallet.balance == 50
