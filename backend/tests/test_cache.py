from httpx import AsyncClient
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.jobs.warm_hot_products import warm
from app.services.cache import CatalogCache
from tests.conftest import ADDRESS, Factory, auth_header


async def test_listing_is_cached_until_a_product_changes(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product()
    assert (await client.get("/api/v1/products")).json()["total"] == 1

    # A raw insert bypasses change tracking, so the cached listing is still served.
    await session.execute(
        text(
            "INSERT INTO products (category_id, sku, name, slug, brand, price, stock, weight_grams, "
            "attributes) VALUES (:c, 'RAW-1', 'Raw', 'raw-1', 'Puma', 1000, 1, 100, '{}')"
        ),
        {"c": product.category_id},
    )
    assert (await client.get("/api/v1/products")).json()["total"] == 1

    # An admin edit is tracked, retires every cached listing, and the new row appears.
    await client.patch(
        f"/api/v1/admin/products/{product.id}", json={"name": "Renamed"}, headers=auth_header(admin)
    )
    assert (await client.get("/api/v1/products")).json()["total"] == 2


async def test_product_page_is_invalidated_on_price_change(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product(price=10000, mrp=None)
    assert (await client.get(f"/api/v1/products/{product.slug}")).json()["price"] == 10000

    await client.patch(
        f"/api/v1/admin/products/{product.id}", json={"price": 12000}, headers=auth_header(admin)
    )

    assert (await client.get(f"/api/v1/products/{product.slug}")).json()["price"] == 12000


async def test_checkout_updates_the_cached_stock(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    product = await factory.product(stock=2)
    assert (await client.get(f"/api/v1/products/{product.slug}")).json()["stock"] == 2

    await factory.cart_with(user, (product, 2))
    await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user))

    body = (await client.get(f"/api/v1/products/{product.slug}")).json()
    assert (body["stock"], body["in_stock"]) == (0, False)


async def test_failed_checkout_leaves_the_cache_alone(
    client: AsyncClient, factory: Factory, cache: CatalogCache
) -> None:
    user = await factory.user()
    product = await factory.product(stock=1)
    await client.get(f"/api/v1/products/{product.slug}")
    await factory.cart_with(user, (product, 5))

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )

    assert response.status_code == 409
    assert await cache.redis.exists(f"catalog:product:{product.slug}") == 1, (
        "nothing committed, nothing evicted"
    )


async def test_cache_can_be_turned_off(
    client: AsyncClient, factory: Factory, session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "catalog_cache_enabled", False)
    product = await factory.product(price=10000, mrp=None)
    slug, product_id = product.slug, product.id
    await client.get(f"/api/v1/products/{slug}")

    await session.execute(text("UPDATE products SET price = 15000 WHERE id = :id"), {"id": product_id})
    session.expire_all()  # tests share the app's session; a real request would start fresh

    assert (await client.get(f"/api/v1/products/{slug}")).json()["price"] == 15000


async def test_pages_still_load_when_redis_is_down(factory: Factory, client: AsyncClient) -> None:
    from app.api.routes.catalog import get_catalog_cache
    from app.main import app

    down = Redis(port=1, socket_connect_timeout=0.1, retry=Retry(NoBackoff(), 0))
    app.dependency_overrides[get_catalog_cache] = lambda: CatalogCache(down)
    product = await factory.product()

    assert (await client.get("/api/v1/products")).json()["total"] == 1
    assert (await client.get(f"/api/v1/products/{product.slug}")).status_code == 200


async def test_views_rank_hot_products_and_warming_caches_them(
    client: AsyncClient, factory: Factory, cache: CatalogCache, session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "hot_product_count", 2)
    category = await factory.category()
    a, b, c = [await factory.product(category) for _ in range(3)]
    for product in (b, b, b, a, a, c):
        await cache.redis.delete(f"catalog:product:{product.slug}")
        await client.get(f"/api/v1/products/{product.slug}")

    assert await cache.top_products(2) == [b.id, a.id]

    assert await warm(session, cache) == 2
    assert await cache.redis.sismember("catalog:hot", b.slug)
    assert not await cache.redis.sismember("catalog:hot", c.slug)
    ttl = await cache.redis.ttl(f"catalog:product:{b.slug}")
    assert ttl > get_settings().product_cache_seconds


async def test_responses_say_how_they_were_served(client: AsyncClient, factory: Factory) -> None:
    product = await factory.product()

    first = await client.get(f"/api/v1/products/{product.slug}")
    second = await client.get(f"/api/v1/products/{product.slug}")

    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("MISS", "HIT")
    assert second.headers["Server-Timing"].startswith("app;dur=")
