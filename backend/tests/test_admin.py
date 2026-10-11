from httpx import AsyncClient

from tests.conftest import Factory, auth_header


def payload(category_id: int, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "category_id": category_id,
        "sku": "NIKE-PEG41-BLK-8",
        "name": "Air Zoom Pegasus 41",
        "brand": "Nike",
        "price": 899900,
        "mrp": 1099900,
        "stock": 25,
        "attributes": {"color": "black", "size": "8"},
    }
    data.update(overrides)
    return data


async def test_customers_get_403_and_guests_401(client: AsyncClient, factory: Factory) -> None:
    category = await factory.category()
    customer = await factory.user()

    assert (await client.post("/api/v1/admin/products", json=payload(category.id))).status_code == 401
    forbidden = await client.post(
        "/api/v1/admin/products", json=payload(category.id), headers=auth_header(customer)
    )
    assert forbidden.status_code == 403


async def test_admin_creates_product_with_generated_slug(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    category = await factory.category()

    response = await client.post(
        "/api/v1/admin/products", json=payload(category.id), headers=auth_header(admin)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["slug"].startswith("air-zoom-pegasus-41-")
    assert (await client.get(f"/api/v1/products/{body['slug']}")).status_code == 200


async def test_validates_product_fields(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    category = await factory.category()

    response = await client.post(
        "/api/v1/admin/products",
        json=payload(category.id, price=50, stock=-1, sku="has spaces"),
        headers=auth_header(admin),
    )

    assert response.status_code == 422
    fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert {"price", "stock", "sku"} <= fields


async def test_mrp_below_price_is_rejected(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    category = await factory.category()

    response = await client.post(
        "/api/v1/admin/products", json=payload(category.id, mrp=1000), headers=auth_header(admin)
    )

    assert response.status_code == 422


async def test_duplicate_sku_is_a_conflict(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    existing = await factory.product()

    response = await client.post(
        "/api/v1/admin/products",
        json=payload(existing.category_id, sku=existing.sku),
        headers=auth_header(admin),
    )

    assert response.status_code == 409


async def test_admin_updates_price_and_stock(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product(price=10000, mrp=None, stock=1)

    body = (
        await client.patch(
            f"/api/v1/admin/products/{product.id}",
            json={"price": 12000, "stock": 40},
            headers=auth_header(admin),
        )
    ).json()

    assert (body["price"], body["stock"]) == (12000, 40)


async def test_update_cannot_put_price_above_mrp(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product(price=10000, mrp=12000)

    response = await client.patch(
        f"/api/v1/admin/products/{product.id}", json={"price": 15000}, headers=auth_header(admin)
    )

    assert response.status_code == 422


async def test_delete_archives_the_product(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product()

    body = (await client.delete(f"/api/v1/admin/products/{product.id}", headers=auth_header(admin))).json()

    assert body["is_active"] is False
    assert (await client.get(f"/api/v1/products/{product.slug}")).status_code == 404


async def test_admin_listing_includes_archived_and_searches(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    category = await factory.category()
    await factory.product(category, sku="OLD-1", is_active=False)
    await factory.product(category)

    everything = (await client.get("/api/v1/admin/products", headers=auth_header(admin))).json()
    found = (
        await client.get("/api/v1/admin/products", params={"search": "OLD-1"}, headers=auth_header(admin))
    ).json()

    assert everything["total"] == 2
    assert [p["sku"] for p in found["items"]] == ["OLD-1"]


async def test_category_with_products_cannot_be_deleted(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product()
    empty = await factory.category()

    assert (
        await client.delete(f"/api/v1/admin/categories/{product.category_id}", headers=auth_header(admin))
    ).status_code == 409
    assert (
        await client.delete(f"/api/v1/admin/categories/{empty.id}", headers=auth_header(admin))
    ).status_code == 204


async def test_admin_creates_category_with_slug(client: AsyncClient, factory: Factory) -> None:
    admin = await factory.user(is_admin=True)

    response = await client.post(
        "/api/v1/admin/categories", json={"name": "Running Shoes"}, headers=auth_header(admin)
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "running-shoes"
