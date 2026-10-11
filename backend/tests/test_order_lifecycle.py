from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus, Product
from app.services.orders import expire_unpaid
from tests.conftest import ADDRESS, Factory, auth_header


async def place(client: AsyncClient, factory: Factory, user_product_qty: tuple) -> str:  # type: ignore[type-arg]
    user, product, quantity = user_product_qty
    await factory.cart_with(user, (product, quantity))
    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )
    assert response.status_code == 201
    return str(response.json()["order"]["number"])


async def test_customer_cancels_unpaid_order_and_stock_returns(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    user = await factory.user()
    product = await factory.product(stock=5)
    number = await place(client, factory, (user, product, 2))

    response = await client.post(f"/api/v1/orders/{number}/cancel", headers=auth_header(user))

    assert response.json()["status"] == "cancelled"
    await session.refresh(product)
    assert product.stock == 5


async def test_paid_order_cannot_be_cancelled(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    user = await factory.user()
    number = await place(client, factory, (user, await factory.product(), 1))
    await session.execute(update(Order).values(status=OrderStatus.paid, paid_at=datetime.now(UTC)))
    await session.commit()

    assert (
        await client.post(f"/api/v1/orders/{number}/cancel", headers=auth_header(user))
    ).status_code == 409


async def test_expiry_cancels_only_stale_unpaid_orders(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    product = await factory.product(stock=10)
    stale = await place(client, factory, (await factory.user(), product, 2))
    fresh = await place(client, factory, (await factory.user(), product, 3))
    await session.execute(
        update(Order).where(Order.number == stale).values(created_at=datetime.now(UTC) - timedelta(hours=1))
    )
    await session.commit()

    assert await expire_unpaid(session, older_than_minutes=30) == 1

    statuses = dict((await session.execute(select(Order.number, Order.status))).all())
    assert statuses == {stale: OrderStatus.cancelled, fresh: OrderStatus.pending_payment}
    assert (await session.get(Product, product.id, populate_existing=True)).stock == 7  # type: ignore[union-attr]
