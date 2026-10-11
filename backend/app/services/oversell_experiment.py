"""The live "try to oversell" experiment on the demo's How it's built page.

Ten buyers check out the last three units at the same moment, each on its own database
connection, like separate requests. With the real checkout, which locks the product row,
exactly three sell. The naive version reads the stock and writes it back without a lock, so
every buyer "succeeds" and the stock count ends up wrong: the lost-update race the lock prevents.
Everything the experiment creates is deleted afterwards.
"""

import asyncio
import secrets
import time
from dataclasses import dataclass

from sqlalchemy import delete, select, update

from app.core.errors import InsufficientStock
from app.core.redis import get_redis
from app.db import SessionLocal
from app.models import Cart, CartItem, Category, Order, OutboxEvent, Product, User
from app.services import orders
from app.services.cache import CatalogCache
from app.services.razorpay import RazorpayClient

BUYERS = 10
UNITS = 3
ADDRESS = {
    "name": "Experiment Buyer",
    "phone": "9876543210",
    "line1": "1 Test Street",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
}
# Time the naive code spends between reading the stock and writing it (validation, pricing,
# a network call). Real code always has some; it only widens a race that exists regardless.
NAIVE_WORK_SECONDS = 0.02

_running = asyncio.Lock()


class ExperimentBusy(Exception):
    pass


@dataclass
class Attempt:
    buyer: int
    sold: bool
    ms: float


@dataclass
class Outcome:
    locked: bool
    units: int
    attempts: list[Attempt]
    final_stock: int
    ms: float


@dataclass
class _Fixture:
    category_id: int
    product_id: int
    slug: str
    user_ids: list[int]


async def run(razorpay: RazorpayClient, *, locked: bool) -> Outcome:
    """Runs one experiment. Only one runs at a time; raises ExperimentBusy otherwise."""
    if _running.locked():
        raise ExperimentBusy
    async with _running:
        fixture = await _create_fixture()
        try:
            started = time.perf_counter()
            attempts = await asyncio.gather(
                *(
                    _checkout(razorpay, buyer, user_id) if locked else _naive_buy(buyer, fixture.product_id)
                    for buyer, user_id in enumerate(fixture.user_ids, start=1)
                )
            )
            elapsed = (time.perf_counter() - started) * 1000
            async with SessionLocal() as session:
                stock = await session.scalar(select(Product.stock).where(Product.id == fixture.product_id))
        finally:
            await _delete_fixture(fixture)
    return Outcome(locked=locked, units=UNITS, attempts=list(attempts), final_stock=stock or 0, ms=elapsed)


async def _checkout(razorpay: RazorpayClient, buyer: int, user_id: int) -> Attempt:
    started = time.perf_counter()
    async with SessionLocal() as session:
        try:
            await orders.checkout(session, razorpay, user_id, ADDRESS)
            sold = True
        except InsufficientStock:
            sold = False
    return Attempt(buyer, sold, (time.perf_counter() - started) * 1000)


async def _naive_buy(buyer: int, product_id: int) -> Attempt:
    """Check-then-write without a lock: the bug the real checkout avoids."""
    started = time.perf_counter()
    async with SessionLocal() as session:
        stock = await session.scalar(select(Product.stock).where(Product.id == product_id))
        await asyncio.sleep(NAIVE_WORK_SECONDS)
        sold = stock is not None and stock >= 1
        if sold:
            assert stock is not None
            await session.execute(update(Product).where(Product.id == product_id).values(stock=stock - 1))
            await session.commit()
    return Attempt(buyer, sold, (time.perf_counter() - started) * 1000)


async def _create_fixture() -> _Fixture:
    tag = secrets.token_hex(4)
    async with SessionLocal() as session:
        category = Category(name=f"Experiment {tag}", slug=f"experiment-{tag}")
        session.add(category)
        await session.flush()
        product = Product(
            category_id=category.id, sku=f"EXP-{tag}", name="Last three pairs", slug=f"experiment-{tag}",
            brand="Experiment", price=49900, stock=UNITS, attributes={},
        )  # fmt: skip
        # "!" is not a valid password hash, so nobody can sign in as these buyers.
        users = [
            User(email=f"buyer{i}-{tag}@example.com", name=f"Buyer {i}", password_hash="!")
            for i in range(1, BUYERS + 1)
        ]
        session.add_all([product, *users])
        await session.flush()
        for user in users:
            cart = Cart(user_id=user.id)
            session.add(cart)
            await session.flush()
            session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=1))
        await session.commit()
        return _Fixture(category.id, product.id, product.slug, [user.id for user in users])


async def _delete_fixture(fixture: _Fixture) -> None:
    async with SessionLocal() as session:
        numbers = (
            await session.scalars(select(Order.number).where(Order.user_id.in_(fixture.user_ids)))
        ).all()
        await session.execute(
            delete(OutboxEvent).where(OutboxEvent.key.in_([*numbers, str(fixture.product_id)]))
        )
        await session.execute(delete(Order).where(Order.user_id.in_(fixture.user_ids)))
        await session.execute(delete(User).where(User.id.in_(fixture.user_ids)))
        await session.execute(delete(Product).where(Product.id == fixture.product_id))
        await session.execute(delete(Category).where(Category.id == fixture.category_id))
        await session.commit()
    await CatalogCache(get_redis()).invalidate([fixture.slug])
