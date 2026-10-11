from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus
from app.services import dashboard
from app.services.cache import CatalogCache
from tests.conftest import ADDRESS, Factory, auth_header


async def place(client: AsyncClient, factory: Factory, price: int) -> str:
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(price=price, mrp=None, stock=20), 1))
    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )
    return str(response.json()["order"]["number"])


async def test_dashboard_counts_today_and_buckets_revenue_by_india_day(
    client: AsyncClient, factory: Factory, session: AsyncSession, cache: CatalogCache
) -> None:
    now = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)  # 17:30 IST
    today_paid = await place(client, factory, 100000)
    late_night = await place(client, factory, 200000)
    await place(client, factory, 300000)  # unpaid

    await session.execute(
        update(Order)
        .where(Order.number == today_paid)
        .values(status=OrderStatus.paid, paid_at=now, created_at=now)
    )
    # 20:00 UTC on the 10th is 01:30 IST on the 11th: India's "today", though UTC's yesterday.
    utc_yesterday = now - timedelta(hours=16)
    await session.execute(
        update(Order)
        .where(Order.number == late_night)
        .values(status=OrderStatus.shipped, paid_at=utc_yesterday, created_at=utc_yesterday)
    )
    await session.commit()

    result = await dashboard.build(session, cache, now=now)

    assert (
        result.revenue_today == 100000 + 200000 + 4900 * 0
    )  # both paid on 11 Oct IST; free shipping above ₹999
    assert result.to_ship == 1, "only the paid, unshipped order"
    assert [d.date for d in result.revenue_by_day][-1] == "2026-10-11"
    assert len(result.revenue_by_day) == 7
    assert result.revenue_by_day[-1].orders == 2


async def test_dashboard_lists_low_stock_and_hot_products(
    client: AsyncClient, factory: Factory, cache: CatalogCache
) -> None:
    admin = await factory.user(is_admin=True)
    low = await factory.product(stock=2)
    popular = await factory.product(stock=50)
    for _ in range(3):
        await cache.record_view(popular.id)

    body = (await client.get("/api/v1/admin/dashboard", headers=auth_header(admin))).json()

    assert [p["id"] for p in body["low_stock"]] == [low.id]
    assert body["hot_products"][0] == {"id": popular.id, "name": popular.name, "views": 3}


async def test_dashboard_is_admin_only(client: AsyncClient, factory: Factory) -> None:
    customer = await factory.user()

    assert (await client.get("/api/v1/admin/dashboard", headers=auth_header(customer))).status_code == 403
