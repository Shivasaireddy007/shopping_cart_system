import httpx
import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import app
from app.services.razorpay import DEMO_KEY_ID, RazorpayClient, get_razorpay
from tests.conftest import ADDRESS, Factory, auth_header


def unreachable(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"demo mode called Razorpay: {request.url}")


@pytest.fixture
def demo_gateway(client: AsyncClient) -> RazorpayClient:
    settings = get_settings().model_copy(update={"demo_payments": True, "razorpay_key_id": ""})
    gateway = RazorpayClient(settings, transport=httpx.MockTransport(unreachable))
    app.dependency_overrides[get_razorpay] = lambda: gateway
    return gateway


async def test_demo_purchase_goes_through_the_signature_check(
    client: AsyncClient, factory: Factory, demo_gateway: RazorpayClient
) -> None:
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(price=50000, stock=3), 1))
    headers = auth_header(user)

    checkout = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=headers)
    ).json()
    number = checkout["order"]["number"]
    assert checkout["razorpay"]["key_id"] == DEMO_KEY_ID

    signed = (await client.post(f"/api/v1/orders/{number}/demo-payment", headers=headers)).json()
    forged = {**signed, "razorpay_signature": "0" * 64}
    rejected = await client.post(f"/api/v1/orders/{number}/verify-payment", json=forged, headers=headers)
    paid = await client.post(f"/api/v1/orders/{number}/verify-payment", json=signed, headers=headers)

    assert rejected.status_code == 422
    assert paid.json()["status"] == "paid"
    again = await client.post(f"/api/v1/orders/{number}/demo-payment", headers=headers)
    assert again.status_code == 409


async def test_demo_payment_does_not_exist_with_real_razorpay(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(stock=3), 1))
    headers = auth_header(user)
    checkout = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=headers)
    ).json()

    response = await client.post(
        f"/api/v1/orders/{checkout['order']['number']}/demo-payment", headers=headers
    )

    assert response.status_code == 404


def test_demo_payments_refuse_real_keys() -> None:
    with pytest.raises(ValidationError, match="DEMO_PAYMENTS"):
        Settings(demo_payments=True, razorpay_key_id="rzp_live_abc")


@pytest.mark.parametrize("url", ["postgres://u:p@db:5432/shop", "postgresql://u:p@db:5432/shop"])
def test_platform_database_urls_get_the_async_driver(url: str) -> None:
    assert Settings(database_url=url).database_url == "postgresql+asyncpg://u:p@db:5432/shop"
