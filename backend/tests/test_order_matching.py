# tests/test_order_matching.py
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import data_model as models
from app.core import order_matching


# -----------------------------
# Setup in-memory DB
# -----------------------------
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# -----------------------------
# Factory functions
# -----------------------------
def create_order(
    session,
    user_id,
    type_,
    price,
    quantity,
    status=models.StatusType.pending,
    order_kind="limit",
):
    order = models.Order(
        user_id=user_id,
        type=type_,
        price=price,
        quantity=quantity,
        remaining_quantity=quantity,
        status=status,
        order_kind=order_kind,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def create_wallet(session, user_id, balance=1000, holdings=100):
    wallet = models.Wallet(
        user_id=user_id,
        balance=float(balance),
        reserved_balance=float(balance),
        holdings=float(holdings),
        reserved_holdings=float(holdings),
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


# -----------------------------
# Tests for _compatible_prices
# -----------------------------
def test_compatible_prices_limit_cross(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 100, 10)
    sell = create_order(db_session, 2, models.OrderType.sell, 90, 10)
    assert order_matching._compatible_prices(buy, sell) is True


def test_compatible_prices_limit_no_cross(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 80, 10)
    sell = create_order(db_session, 2, models.OrderType.sell, 90, 10)
    assert order_matching._compatible_prices(buy, sell) is False


def test_compatible_prices_market_order(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 0, 10, order_kind="market")
    sell = create_order(db_session, 2, models.OrderType.sell, 90, 10)
    assert order_matching._compatible_prices(buy, sell) is True


def test_compatible_prices_both_market(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 0, 10, order_kind="market")
    sell = create_order(
        db_session, 2, models.OrderType.sell, 0, 10, order_kind="market"
    )
    assert order_matching._compatible_prices(buy, sell) is False


# -----------------------------
# Tests for _execution_price
# -----------------------------
def test_execution_price_opposite_limit(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 100, 10)
    sell = create_order(db_session, 2, models.OrderType.sell, 90, 10)
    price = order_matching._execution_price(buy, sell)
    assert price == Decimal("90")


def test_execution_price_new_limit_opposite_market(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 100, 10)
    sell = create_order(
        db_session, 2, models.OrderType.sell, 0, 10, order_kind="market"
    )
    price = order_matching._execution_price(buy, sell)
    assert price == Decimal("100")


def test_execution_price_both_market_raises(db_session):
    buy = create_order(db_session, 1, models.OrderType.buy, 0, 10, order_kind="market")
    sell = create_order(
        db_session, 2, models.OrderType.sell, 0, 10, order_kind="market"
    )
    import pytest

    with pytest.raises(ValueError):
        order_matching._execution_price(buy, sell)


# -----------------------------
# Tests for match_orders
# -----------------------------
def test_match_orders_basic(db_session):
    # Create wallets
    create_wallet(db_session, 1, balance=1000, holdings=0)
    create_wallet(db_session, 2, balance=0, holdings=10)

    # Orders
    buy_order = create_order(db_session, 1, models.OrderType.buy, 100, 5)
    sell_order = create_order(db_session, 2, models.OrderType.sell, 90, 5)

    executed_trades = order_matching.match_orders(db_session, buy_order)

    assert len(executed_trades) == 1
    trade = executed_trades[0]
    assert trade.price == 90
    assert trade.quantity == 5

    # Wallet updates
    buyer_wallet = db_session.query(models.Wallet).filter_by(user_id=1).one()
    seller_wallet = db_session.query(models.Wallet).filter_by(user_id=2).one()

    # Buyer spent 90*5 = 450
    assert buyer_wallet.reserved_balance == float(1000 - 450)
    assert buyer_wallet.holdings == float(5)

    # Seller sold 5 units
    assert seller_wallet.reserved_holdings == float(10 - 5)
    assert seller_wallet.balance == float(0 + 450)


def test_match_orders_partial_fill(db_session):
    # Wallets
    create_wallet(db_session, 1, balance=1000, holdings=0)
    create_wallet(db_session, 2, balance=0, holdings=2)

    # Orders
    buy_order = create_order(db_session, 1, models.OrderType.buy, 100, 5)
    sell_order = create_order(db_session, 2, models.OrderType.sell, 90, 2)

    executed_trades = order_matching.match_orders(db_session, buy_order)
    assert len(executed_trades) == 1
    trade = executed_trades[0]
    assert trade.quantity == 2
    assert buy_order.remaining_quantity == 3
    assert sell_order.remaining_quantity == 0
    assert sell_order.status == models.StatusType.executed


def test_match_orders_self_trade_skipped(db_session):
    create_wallet(db_session, 1, balance=1000, holdings=10)
    # Order from same user
    buy_order = create_order(db_session, 1, models.OrderType.buy, 100, 5)
    sell_order = create_order(db_session, 1, models.OrderType.sell, 90, 5)

    executed_trades = order_matching.match_orders(db_session, buy_order)
    assert len(executed_trades) == 0


def test_match_orders_insufficient_funds(db_session):
    create_wallet(db_session, 1, balance=10, holdings=0)
    create_wallet(db_session, 2, balance=0, holdings=10)
    buy_order = create_order(db_session, 1, models.OrderType.buy, 100, 5)
    sell_order = create_order(db_session, 2, models.OrderType.sell, 90, 5)
    executed_trades = order_matching.match_orders(db_session, buy_order)
    assert len(executed_trades) == 0
