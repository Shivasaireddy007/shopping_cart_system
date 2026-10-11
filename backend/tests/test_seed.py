from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Product, User
from app.schemas.auth import LoginIn
from app.seed import DEMO_PASSWORD, DEMO_USERS, reset
from tests.conftest import ADDRESS, Factory, auth_header


def test_demo_logins_pass_login_validation() -> None:
    """Reserved domains like .test fail email validation, which would lock out the demo accounts."""
    for email, _, _ in DEMO_USERS:
        LoginIn(email=email, password=DEMO_PASSWORD)


async def test_reset_empties_every_table(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    user = await factory.user()
    product = await factory.product(stock=5)
    await factory.cart_with(user, (product, 1))
    await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user))

    await reset(session)

    for model in (User, Product, Order):
        assert await session.scalar(select(func.count()).select_from(model)) == 0
