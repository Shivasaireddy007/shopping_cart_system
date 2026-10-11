from httpx import AsyncClient

from tests.conftest import Factory


async def test_lists_only_active_products(client: AsyncClient, factory: Factory) -> None:
    category = await factory.category()
    for _ in range(3):
        await factory.product(category)
    await factory.product(category, is_active=False)

    body = (await client.get("/api/v1/products")).json()

    assert body["total"] == 3
    assert len(body["items"]) == 3


async def test_filters_by_category_brand_and_price(client: AsyncClient, factory: Factory) -> None:
    shoes = await factory.category("shoes")
    await factory.product(shoes, brand="Nike", price=250000)
    await factory.product(shoes, brand="Nike", price=900000, mrp=None)
    await factory.product(shoes, brand="Puma", price=250000)
    await factory.product(brand="Nike", price=250000)

    body = (
        await client.get(
            "/api/v1/products", params={"category": "shoes", "brand": "Nike", "max_price": 500000}
        )
    ).json()

    assert body["total"] == 1
    assert body["items"][0]["price"] == 250000


async def test_sorts_by_price(client: AsyncClient, factory: Factory) -> None:
    category = await factory.category()
    for price in (30000, 10000, 20000):
        await factory.product(category, price=price, mrp=None)

    body = (await client.get("/api/v1/products", params={"sort": "price_asc"})).json()

    assert [p["price"] for p in body["items"]] == [10000, 20000, 30000]


async def test_in_stock_filter(client: AsyncClient, factory: Factory) -> None:
    category = await factory.category()
    await factory.product(category, stock=0)
    await factory.product(category, stock=5)

    body = (await client.get("/api/v1/products", params={"in_stock": True})).json()

    assert body["total"] == 1
    assert body["items"][0]["in_stock"] is True


async def test_rejects_invalid_filters(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products", params={"sort": "random", "per_page": 500})

    assert response.status_code == 422


async def test_rejects_inverted_price_range(client: AsyncClient) -> None:
    response = await client.get("/api/v1/products", params={"min_price": 5000, "max_price": 100})

    assert response.status_code == 422


async def test_max_price_alone_is_allowed(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/products", params={"max_price": 100})).status_code == 200


async def test_paginates(client: AsyncClient, factory: Factory) -> None:
    category = await factory.category()
    for _ in range(5):
        await factory.product(category)

    body = (await client.get("/api/v1/products", params={"per_page": 2, "page": 3})).json()

    assert body["total"] == 5
    assert len(body["items"]) == 1


async def test_shows_product_by_slug(client: AsyncClient, factory: Factory) -> None:
    product = await factory.product()

    body = (await client.get(f"/api/v1/products/{product.slug}")).json()

    assert body["sku"] == product.sku
    assert body["category"]["id"] == product.category_id


async def test_inactive_product_is_not_found(client: AsyncClient, factory: Factory) -> None:
    product = await factory.product(is_active=False)

    assert (await client.get(f"/api/v1/products/{product.slug}")).status_code == 404


async def test_lists_categories(client: AsyncClient, factory: Factory) -> None:
    await factory.category()
    await factory.category()

    assert len((await client.get("/api/v1/categories")).json()) == 2
