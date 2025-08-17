# tests/test_app.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db.session import async_session
from app.db.data_model import User, Wallet, Order, Trade
from app.core.security import get_password_hash
from app.core.order_matching import match_orders
from decimal import Decimal

@pytest.fixture
async def test_db():
    async with async_session() as session:
        async with session.begin():
            # Clean slate
            await session.execute("DELETE FROM trades")
            await session.execute("DELETE FROM orders")
            await session.execute("DELETE FROM wallets")
            await session.execute("DELETE FROM users")
        yield session
        # teardown
        await session.rollback()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user_and_wallet(test_db: AsyncSession):
    # Create user
    user = User(username="testuser", password=get_password_hash("password"))
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    # Check wallet created
    wallet = Wallet(user_id=user.id, balance=1000.0, reserved_balance=0.0)
    test_db.add(wallet)
    await test_db.commit()
    await test_db.refresh(wallet)

    assert wallet.user_id == user.id
    assert wallet.balance == 1000.0
    assert wallet.reserved_balance == 0.0

@pytest.mark.asyncio
async def test_create_limit_order_and_match(test_db: AsyncSession):
    # Create buyer
    buyer = User(username="buyer", password=get_password_hash("pass"))
    test_db.add(buyer)
    await test_db.commit()
    await test_db.refresh(buyer)

    buyer_wallet = Wallet(user_id=buyer.id, balance=1000.0, reserved_balance=0.0)
    test_db.add(buyer_wallet)
    await test_db.commit()
    await test_db.refresh(buyer_wallet)

    # Create seller
    seller = User(username="seller", password=get_password_hash("pass"))
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    seller_wallet = Wallet(user_id=seller.id, balance=0.0, reserved_balance=0.0)
    test_db.add(seller_wallet)
    await test_db.commit()
    await test_db.refresh(seller_wallet)

    # Seller places limit sell order
    sell_order = Order(
        user_id=seller.id,
        order_type="limit",
        side="sell",
        quantity=5.0,
        price=100.0,
        remaining_quantity=5.0
    )
    test_db.add(sell_order)
    await test_db.commit()
    await test_db.refresh(sell_order)

    # Buyer places limit buy order
    buy_order = Order(
        user_id=buyer.id,
        order_type="limit",
        side="buy",
        quantity=5.0,
        price=100.0,
        remaining_quantity=5.0
    )
    test_db.add(buy_order)
    await test_db.commit()
    await test_db.refresh(buy_order)

    # Match orders
    await match_orders(buy_order, test_db)

    # Check wallet balances
    await test_db.refresh(buyer_wallet)
    await test_db.refresh(seller_wallet)
    await test_db.refresh(buy_order)
    await test_db.refresh(sell_order)

    assert buyer_wallet.balance == 500.0  # 1000 - (5*100)
    assert seller_wallet.balance == 500.0  # Received 5*100
    assert buy_order.remaining_quantity == 0.0
    assert sell_order.remaining_quantity == 0.0

@pytest.mark.asyncio
async def test_partial_fill(test_db: AsyncSession):
    # Buyer wallet
    buyer = User(username="partial_buyer", password=get_password_hash("pass"))
    test_db.add(buyer)
    await test_db.commit()
    await test_db.refresh(buyer)
    buyer_wallet = Wallet(user_id=buyer.id, balance=1000.0, reserved_balance=0.0)
    test_db.add(buyer_wallet)
    await test_db.commit()
    await test_db.refresh(buyer_wallet)

    # Seller wallet
    seller = User(username="partial_seller", password=get_password_hash("pass"))
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)
    seller_wallet = Wallet(user_id=seller.id, balance=0.0, reserved_balance=0.0)
    test_db.add(seller_wallet)
    await test_db.commit()
    await test_db.refresh(seller_wallet)

    # Seller places smaller sell order
    sell_order = Order(
        user_id=seller.id,
        order_type="limit",
        side="sell",
        quantity=3.0,
        price=100.0,
        remaining_quantity=3.0
    )
    test_db.add(sell_order)
    await test_db.commit()
    await test_db.refresh(sell_order)

    # Buyer places larger buy order
    buy_order = Order(
        user_id=buyer.id,
        order_type="limit",
        side="buy",
        quantity=5.0,
        price=100.0,
        remaining_quantity=5.0
    )
    test_db.add(buy_order)
    await test_db.commit()
    await test_db.refresh(buy_order)

    await match_orders(buy_order, test_db)

    # Refresh wallets and orders
    await test_db.refresh(buyer_wallet)
    await test_db.refresh(seller_wallet)
    await test_db.refresh(buy_order)
    await test_db.refresh(sell_order)

    assert buyer_wallet.balance == 700.0  # Paid 3*100
    assert seller_wallet.balance == 300.0
    assert buy_order.remaining_quantity == 2.0  # Partially filled
    assert sell_order.remaining_quantity == 0.0

@pytest.mark.asyncio
async def test_market_order_matching(test_db: AsyncSession):
    # Seller
    seller = User(username="market_seller", password=get_password_hash("pass"))
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)
    seller_wallet = Wallet(user_id=seller.id, balance=0.0, reserved_balance=0.0)
    test_db.add(seller_wallet)
    await test_db.commit()
    await test_db.refresh(seller_wallet)

    # Seller places limit sell order
    sell_order = Order(
        user_id=seller.id,
        order_type="limit",
        side="sell",
        quantity=2.0,
        price=50.0,
        remaining_quantity=2.0
    )
    test_db.add(sell_order)
    await test_db.commit()
    await test_db.refresh(sell_order)

    # Buyer market order
    buyer = User(username="market_buyer", password=get_password_hash("pass"))
    test_db.add(buyer)
    await test_db.commit()
    await test_db.refresh(buyer)
    buyer_wallet = Wallet(user_id=buyer.id, balance=500.0, reserved_balance=0.0)
    test_db.add(buyer_wallet)
    await test_db.commit()
    await test_db.refresh(buyer_wallet)

    buy_order = Order(
        user_id=buyer.id,
        order_type="market",
        side="buy",
        quantity=2.0,
        price=None,
        remaining_quantity=2.0
    )
    test_db.add(buy_order)
    await test_db.commit()
    await test_db.refresh(buy_order)

    await match_orders(buy_order, test_db)

    # Check balances
    await test_db.refresh(buyer_wallet)
    await test_db.refresh(seller_wallet)
    assert buyer_wallet.balance == 400.0  # Paid 2*50
    assert seller_wallet.balance == 100.0
    assert buy_order.remaining_quantity == 0.0
    assert sell_order.remaining_quantity == 0.0
