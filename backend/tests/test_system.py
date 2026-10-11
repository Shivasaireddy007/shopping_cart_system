import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import verify_password
from app.db import SessionLocal
from app.main import app
from app.models import Category, Product, User
from app.services.razorpay import RazorpayClient, get_razorpay
from tests.conftest import Factory


@pytest.fixture
def demo_server(client: AsyncClient) -> None:
    settings = get_settings().model_copy(update={"demo_payments": True, "razorpay_key_id": ""})
    gateway = RazorpayClient(settings, transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    app.dependency_overrides[get_razorpay] = lambda: gateway


async def test_stats_report_live_numbers(client: AsyncClient, factory: Factory) -> None:
    product = await factory.product()
    for _ in range(3):
        await client.get(f"/api/v1/products/{product.slug}")

    stats = (await client.get("/api/v1/system/stats")).json()

    assert stats["products"] == 1
    assert stats["latency"]["requests"] >= 3
    assert stats["latency"]["p95_ms"] is not None
    assert stats["cache"]["hits"] >= 2
    assert stats["postgres"][0].isdigit()
    assert stats["recent_events"][0]["event_type"] == "product.changed"


async def test_experiment_is_only_on_demo_servers(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/system/oversell-experiment")).status_code == 404


@pytest.mark.concurrency
@pytest.mark.usefixtures("demo_server")
async def test_locked_checkout_sells_exactly_the_stock(client: AsyncClient) -> None:
    result = (await client.post("/api/v1/system/oversell-experiment?locked=true")).json()

    assert (result["sold"], result["final_stock"]) == (3, 0)
    assert len(result["attempts"]) == 10
    await assert_cleaned_up()


@pytest.mark.concurrency
@pytest.mark.usefixtures("demo_server")
async def test_naive_checkout_oversells(client: AsyncClient) -> None:
    result = (await client.post("/api/v1/system/oversell-experiment?locked=false")).json()

    assert result["sold"] > result["units"]
    assert result["final_stock"] > result["units"] - result["sold"], "stock no longer matches sales"
    await assert_cleaned_up()


async def assert_cleaned_up() -> None:
    async with SessionLocal() as session:
        for model, column in ((Category, Category.slug), (Product, Product.slug), (User, User.email)):
            leftover = select(func.count()).select_from(model).where(column.like("%experiment-%"))
            assert await session.scalar(leftover) == 0
        buyers = select(func.count()).select_from(User).where(User.email.like("buyer%"))
        assert await session.scalar(buyers) == 0


def test_accounts_without_a_valid_hash_cannot_sign_in() -> None:
    assert verify_password("!", "anything") is False
