import hashlib
import hmac
import json
import os
import secrets
from collections.abc import AsyncIterator
from typing import Any

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:5432/shop_test")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

import app.models
from app.api.routes.catalog import get_catalog_cache
from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import create_token, hash_password
from app.db import Base, get_session
from app.main import app
from app.models import Cart, CartItem, Category, Product, User
from app.services import product_changes
from app.services.cache import CatalogCache
from app.services.razorpay import RazorpayClient, get_razorpay
from app.services.search.client import SearchClient, get_search_client
from app.services.shiprocket import ShiprocketClient, get_shiprocket

_PASSWORD_HASH = hash_password("password123")


@pytest.fixture(scope="session")
async def connection() -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        yield conn
    await engine.dispose()


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """A session inside a transaction that is rolled back after the test.

    The app's own commits become savepoints, so each test starts from an empty database.
    """
    transaction = await connection.begin()
    db = AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield db
    finally:
        await db.close()
        await transaction.rollback()


class FakeRazorpay:
    """Razorpay's Orders API on an in-memory transport, with test credentials."""

    key_secret = "test-key-secret"
    webhook_secret = "test-webhook-secret"

    def __init__(self) -> None:
        self.fail = False
        self.created: list[dict[str, Any]] = []
        settings = get_settings().model_copy(
            update={
                "razorpay_key_id": "rzp_test_key",
                "razorpay_key_secret": self.key_secret,
                "razorpay_webhook_secret": self.webhook_secret,
            }
        )
        self.client = RazorpayClient(settings, transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.fail:
            return httpx.Response(500, json={"error": {"description": "unavailable"}})
        body = json.loads(request.content)
        self.created.append(body)
        return httpx.Response(200, json={"id": f"order_{secrets.token_hex(7)}", **body})

    def payment_signature(self, razorpay_order_id: str, payment_id: str) -> str:
        message = f"{razorpay_order_id}|{payment_id}".encode()
        return hmac.new(self.key_secret.encode(), message, hashlib.sha256).hexdigest()

    def webhook_signature(self, body: bytes) -> str:
        return hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def razorpay() -> FakeRazorpay:
    return FakeRazorpay()


class FakeSearch:
    """OpenSearch on an in-memory transport. Records requests; replies with `next_search`."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str, Any]] = []
        self.down = False
        self.next_search: dict[str, Any] = {"hits": {"total": {"value": 0}, "hits": []}, "aggregations": {}}
        self.client = SearchClient("http://search.test", transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("Connection refused")
        body: Any = None
        if request.content:
            text = request.content.decode()
            body = (
                [json.loads(line) for line in text.splitlines()]
                if request.url.path == "/_bulk"
                else json.loads(text)
            )
        self.requests.append((request.method, request.url.path, body))
        if request.url.path.endswith("/_search"):
            return httpx.Response(200, json=self.next_search)
        if request.url.path == "/_bulk":
            return httpx.Response(200, json={"errors": False, "items": []})
        return httpx.Response(200, json={"acknowledged": True})

    def bulk_bodies(self) -> list[Any]:
        return [body for method, path, body in self.requests if path == "/_bulk"]


class FakeShiprocket:
    """Shiprocket's API on an in-memory transport. `awb_failures` makes the next AWB calls fail."""

    def __init__(self, configured: bool = True) -> None:
        self.calls: list[tuple[str, str, Any]] = []
        self.awb_failures = 0
        settings = get_settings().model_copy(
            update={
                "shiprocket_email": "ops@example.com" if configured else "",
                "shiprocket_password": "secret" if configured else "",
                "shiprocket_webhook_token": "ship-token",
            }
        )
        self.client = ShiprocketClient(settings, get_redis(), transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        path = request.url.path.removeprefix("/v1/external")
        self.calls.append((request.method, path, body))
        if path == "/auth/login":
            return httpx.Response(200, json={"token": "sr-token"})
        if path == "/orders/create/adhoc":
            return httpx.Response(200, json={"order_id": 5001, "shipment_id": 9001, "status": "NEW"})
        if path == "/courier/assign/awb":
            if self.awb_failures:
                self.awb_failures -= 1
                return httpx.Response(500, json={"message": "Courier unavailable"})
            return httpx.Response(
                200, json={"response": {"data": {"awb_code": "AWB123", "courier_name": "Delhivery"}}}
            )
        if path.startswith("/courier/track/awb/"):
            return httpx.Response(200, json={"tracking_data": {
                "track_url": "https://shiprocket.co/tracking/AWB123",
                "shipment_track_activities": [
                    {"date": "2026-10-11 09:40:00", "activity": "In transit", "location": "Bengaluru hub"},
                ],
            }})  # fmt: skip
        return httpx.Response(404)

    def paths(self) -> list[str]:
        return [path for _, path, _ in self.calls]


@pytest.fixture
def shiprocket() -> FakeShiprocket:
    return FakeShiprocket()


@pytest.fixture
def search() -> FakeSearch:
    return FakeSearch()


@pytest.fixture
async def cache() -> AsyncIterator[CatalogCache]:
    """The catalog cache on Redis database 15, emptied before each test."""
    redis = get_redis()
    await redis.flushdb()
    yield CatalogCache(redis)


@pytest.fixture
async def client(
    session: AsyncSession,
    razorpay: FakeRazorpay,
    search: FakeSearch,
    cache: CatalogCache,
    shiprocket: FakeShiprocket,
) -> AsyncIterator[AsyncClient]:
    async def override() -> AsyncIterator[AsyncSession]:
        yield session
        await product_changes.publish(session, cache)

    app.dependency_overrides[get_session] = override
    app.dependency_overrides[get_razorpay] = lambda: razorpay.client
    app.dependency_overrides[get_search_client] = lambda: search.client
    app.dependency_overrides[get_catalog_cache] = lambda: cache
    app.dependency_overrides[get_shiprocket] = lambda: shiprocket.client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


class Factory:
    """Creates test data with sensible defaults."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.counter = 0

    def _next(self) -> int:
        self.counter += 1
        return self.counter

    async def user(self, *, is_admin: bool = False, email: str | None = None) -> User:
        n = self._next()
        user = User(
            email=email or f"user{n}@example.com",
            name=f"User {n}",
            password_hash=_PASSWORD_HASH,
            is_admin=is_admin,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def category(self, slug: str | None = None) -> Category:
        n = self._next()
        category = Category(name=f"Category {n}", slug=slug or f"category-{n}")
        self.session.add(category)
        await self.session.flush()
        return category

    async def product(self, category: Category | None = None, **overrides: Any) -> Product:
        n = self._next()
        category = category or await self.category()
        values: dict[str, Any] = {
            "sku": f"SKU-{n}",
            "name": f"Product {n}",
            "slug": f"product-{n}",
            "brand": "Nike",
            "price": 50000,
            "stock": 10,
            "attributes": {"color": "black", "size": "M"},
        }
        values.update(overrides)
        values.setdefault("mrp", values["price"] * 6 // 5)
        product = Product(category_id=category.id, **values)
        self.session.add(product)
        await self.session.flush()
        return product

    async def cart_with(self, user: User, *lines: tuple[Product, int]) -> Cart:
        cart = Cart(user_id=user.id)
        self.session.add(cart)
        await self.session.flush()
        for product, quantity in lines:
            self.session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity))
        await self.session.flush()
        return cart


@pytest.fixture
def factory(session: AsyncSession) -> Factory:
    return Factory(session)


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user.id, 'access')}"}


ADDRESS = {
    "name": "Asha Rao",
    "phone": "9876543210",
    "line1": "12 MG Road",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
}
