import os
from collections.abc import AsyncIterator
from typing import Any

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:5432/shop_test")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

import app.models
from app.core.config import get_settings
from app.core.security import create_token, hash_password
from app.db import Base, get_session
from app.main import app
from app.models import Category, Product, User

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


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override
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


@pytest.fixture
def factory(session: AsyncSession) -> Factory:
    return Factory(session)


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user.id, 'access')}"}
