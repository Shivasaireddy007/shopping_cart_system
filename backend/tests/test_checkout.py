from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CartItem, Order, OrderStatus, Product
from tests.conftest import ADDRESS, Factory, FakeRazorpay, auth_header


async def test_checkout_reserves_stock_and_returns_razorpay_details(
    client: AsyncClient, factory: Factory, razorpay: FakeRazorpay, session: AsyncSession
) -> None:
    user = await factory.user()
    product = await factory.product(price=60000, stock=5)
    await factory.cart_with(user, (product, 2))

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["order"]["status"] == "pending_payment"
    assert body["order"]["total"] == 120000
    assert body["razorpay"]["amount"] == 120000
    assert body["razorpay"]["key_id"] == "rzp_test_key"
    assert body["razorpay"]["order_id"].startswith("order_")
    assert razorpay.created[0]["receipt"] == body["order"]["number"]

    assert (await session.get(Product, product.id, populate_existing=True)).stock == 3  # type: ignore[union-attr]
    assert await session.scalar(select(func.count(CartItem.id))) == 0


async def test_order_keeps_the_price_paid(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    user = await factory.user()
    product = await factory.product(price=50000)
    await factory.cart_with(user, (product, 1))
    number = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user))
    ).json()["order"]["number"]

    product.price, product.mrp = 99900, None
    await session.commit()

    order = (await client.get(f"/api/v1/orders/{number}", headers=auth_header(user))).json()
    assert order["items"][0]["unit_price"] == 50000


async def test_empty_cart_cannot_check_out(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )

    assert response.status_code == 422


async def test_stock_that_ran_out_blocks_checkout_and_changes_nothing(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    user = await factory.user()
    plenty = await factory.product(stock=10)
    scarce = await factory.product(stock=1)
    await factory.cart_with(user, (plenty, 2), (scarce, 3))

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )

    assert response.status_code == 409
    assert response.json()["available"] == 1
    await session.refresh(plenty)
    assert plenty.stock == 10, "the whole reservation rolls back"
    assert await session.scalar(select(func.count(Order.id))) == 0


async def test_gateway_failure_cancels_the_order_and_keeps_the_cart(
    client: AsyncClient, factory: Factory, razorpay: FakeRazorpay, session: AsyncSession
) -> None:
    razorpay.fail = True
    user = await factory.user()
    product = await factory.product(stock=4)
    await factory.cart_with(user, (product, 2))

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )

    assert response.status_code == 502
    await session.refresh(product)
    assert product.stock == 4
    assert await session.scalar(select(Order.status)) == OrderStatus.cancelled
    assert await session.scalar(select(func.count(CartItem.id))) == 1


async def test_validates_indian_phone_pincode_and_state(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    address = {**ADDRESS, "phone": "12345", "pincode": "0560", "state": "Atlantis"}

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": address}, headers=auth_header(user)
    )

    assert response.status_code == 422
    assert {e["loc"][-1] for e in response.json()["detail"]} == {"phone", "pincode", "state"}


async def test_users_only_see_their_own_orders(client: AsyncClient, factory: Factory) -> None:
    owner, other = await factory.user(), await factory.user()
    await factory.cart_with(owner, (await factory.product(), 1))
    number = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(owner))
    ).json()["order"]["number"]

    assert (await client.get("/api/v1/orders", headers=auth_header(owner))).json()["total"] == 1
    assert (await client.get("/api/v1/orders", headers=auth_header(other))).json()["total"] == 0
    assert (await client.get(f"/api/v1/orders/{number}", headers=auth_header(other))).status_code == 404
