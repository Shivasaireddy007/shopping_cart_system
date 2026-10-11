"""Concurrent checkouts against real, separate database connections.

The other tests share one connection inside a rolled-back transaction, which can't show
locking behaviour. These run several checkouts at the same moment, each on its own
connection, like simultaneous requests in production.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import InsufficientStock
from app.core.security import hash_password
from app.models import Cart, CartItem, Category, Order, Product, User
from app.services.orders import checkout
from tests.conftest import ADDRESS, FakeRazorpay

pytestmark = pytest.mark.concurrency


@pytest.fixture
async def engine(connection: AsyncConnection) -> AsyncIterator[AsyncEngine]:
    """A separate engine with committed data; tables are emptied afterwards."""
    eng = create_async_engine(get_settings().database_url, pool_size=12)
    yield eng
    async with eng.begin() as conn:
        tables = "outbox_events, processed_events, order_items, orders, cart_items, carts, " + (
            "products, categories, users"
        )
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await eng.dispose()


async def test_ten_buyers_for_three_units_sell_exactly_three(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    password = hash_password("password123")

    async with sessions() as setup:
        category = Category(name="Shoes", slug="shoes")
        setup.add(category)
        await setup.flush()
        product = Product(
            category_id=category.id, sku="LAST-3", name="Last pair", slug="last-pair", brand="Nike",
            price=50000, stock=3, attributes={},
        )  # fmt: skip
        users = [
            User(email=f"buyer{i}@example.com", name=f"Buyer {i}", password_hash=password) for i in range(10)
        ]
        setup.add_all([product, *users])
        await setup.flush()
        for user in users:
            cart = Cart(user_id=user.id)
            setup.add(cart)
            await setup.flush()
            setup.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=1))
        await setup.commit()
        user_ids, product_id = [u.id for u in users], product.id

    razorpay = FakeRazorpay().client

    async def buy(user_id: int) -> str:
        async with sessions() as session:
            try:
                await checkout(session, razorpay, user_id, ADDRESS)
                return "sold"
            except InsufficientStock:
                return "out of stock"

    results = await asyncio.gather(*(buy(uid) for uid in user_ids))

    assert results.count("sold") == 3
    assert results.count("out of stock") == 7
    async with sessions() as check:
        assert await check.scalar(select(Product.stock).where(Product.id == product_id)) == 0
        assert len((await check.scalars(select(Order.id))).all()) == 3
