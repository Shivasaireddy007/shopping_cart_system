import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import Factory, auth_header


async def test_cart_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/cart")).status_code == 401


async def test_adding_the_same_product_twice_increments_quantity(
    client: AsyncClient, factory: Factory
) -> None:
    user = await factory.user()
    product = await factory.product(price=50000, stock=10)
    headers = auth_header(user)

    await client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)
    body = (
        await client.post(
            "/api/v1/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers
        )
    ).json()

    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["subtotal"] == 150000


async def test_shipping_is_free_above_threshold(
    client: AsyncClient, factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "shipping_free_above", 100000)
    monkeypatch.setattr(get_settings(), "shipping_flat_fee", 4900)
    user = await factory.user()
    cheap = await factory.product(price=50000, mrp=None)
    expensive = await factory.product(price=150000, mrp=None)
    headers = auth_header(user)

    first = (
        await client.post("/api/v1/cart/items", json={"product_id": cheap.id, "quantity": 1}, headers=headers)
    ).json()
    assert (first["shipping_fee"], first["total"]) == (4900, 54900)

    second = (
        await client.post(
            "/api/v1/cart/items", json={"product_id": expensive.id, "quantity": 1}, headers=headers
        )
    ).json()
    assert (second["shipping_fee"], second["total"]) == (0, 200000)


async def test_cannot_add_more_than_available_stock(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    product = await factory.product(stock=2)

    response = await client.post(
        "/api/v1/cart/items", json={"product_id": product.id, "quantity": 3}, headers=auth_header(user)
    )

    assert response.status_code == 409
    assert response.json()["available"] == 2


async def test_cannot_add_inactive_product(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    product = await factory.product(is_active=False)

    response = await client.post(
        "/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=auth_header(user)
    )

    assert response.status_code == 404


async def test_quantity_is_capped_per_item(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    product = await factory.product(stock=100)

    body = (
        await client.post(
            "/api/v1/cart/items", json={"product_id": product.id, "quantity": 50}, headers=auth_header(user)
        )
    ).json()

    assert body["items"][0]["quantity"] == get_settings().max_quantity_per_item


async def test_update_and_remove_item(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    product = await factory.product(stock=10)
    headers = auth_header(user)
    item_id = (
        await client.post(
            "/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers
        )
    ).json()["items"][0]["id"]

    updated = (
        await client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 4}, headers=headers)
    ).json()
    assert updated["items"][0]["quantity"] == 4

    removed = (await client.delete(f"/api/v1/cart/items/{item_id}", headers=headers)).json()
    assert removed["items"] == []


async def test_cannot_change_another_users_cart_item(client: AsyncClient, factory: Factory) -> None:
    owner, other = await factory.user(), await factory.user()
    product = await factory.product()
    item_id = (
        await client.post(
            "/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=auth_header(owner)
        )
    ).json()["items"][0]["id"]

    response = await client.patch(
        f"/api/v1/cart/items/{item_id}", json={"quantity": 2}, headers=auth_header(other)
    )

    assert response.status_code == 404


async def test_cart_shows_current_price(client: AsyncClient, factory: Factory, session) -> None:  # type: ignore[no-untyped-def]
    user = await factory.user()
    product = await factory.product(price=10000, mrp=None)
    headers = auth_header(user)
    await client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)

    product.price = 12000
    await session.commit()

    assert (await client.get("/api/v1/cart", headers=headers)).json()["subtotal"] == 12000


async def test_clear_cart(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    product = await factory.product()
    headers = auth_header(user)
    await client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)

    assert (await client.delete("/api/v1/cart", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/cart", headers=headers)).json()["items"] == []
