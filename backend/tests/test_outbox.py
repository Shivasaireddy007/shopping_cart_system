from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.relay import relay_once
from app.models import OutboxEvent
from tests.conftest import ADDRESS, Factory, FakeRazorpay, auth_header


class FakePublisher:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, dict[str, Any]]] = []

    async def publish(self, topic: str, key: str, value: dict[str, Any], headers: dict[str, str]) -> None:
        assert headers["event_id"] == value["event_id"]
        self.sent.append((topic, key, value))


async def events(session: AsyncSession) -> list[tuple[str, str, str]]:
    rows = await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id))
    return [(e.topic, e.event_type, e.key) for e in rows]


async def test_admin_product_change_writes_an_event(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    admin = await factory.user(is_admin=True)
    product = await factory.product()
    await session.commit()
    before = len(await events(session))

    response = await client.patch(
        f"/api/v1/admin/products/{product.id}", json={"name": "Renamed"}, headers=auth_header(admin)
    )
    assert response.status_code == 200

    assert (await events(session))[before:] == [("products", "product.changed", str(product.id))]


async def test_rolled_back_checkout_writes_no_events(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(stock=1), 5))
    await session.commit()
    before = await events(session)

    response = await client.post(
        "/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user)
    )

    assert response.status_code == 409
    assert await events(session) == before


async def test_payment_writes_order_paid_event(
    client: AsyncClient, factory: Factory, razorpay: FakeRazorpay, session: AsyncSession
) -> None:
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(stock=3), 1))
    body = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user))
    ).json()
    number, rzp_order = body["order"]["number"], body["razorpay"]["order_id"]

    await client.post(
        f"/api/v1/orders/{number}/verify-payment",
        json={
            "razorpay_payment_id": "pay_1",
            "razorpay_signature": razorpay.payment_signature(rzp_order, "pay_1"),
        },
        headers=auth_header(user),
    )

    assert ("orders", "order.paid", number) in await events(session)


async def test_relay_publishes_in_order_and_marks_sent(factory: Factory, session: AsyncSession) -> None:
    await factory.product()
    await factory.product()
    await session.commit()
    publisher = FakePublisher()
    expected = [str(e) for e in await session.scalars(select(OutboxEvent.event_id).order_by(OutboxEvent.id))]

    sent = await relay_once(session, publisher)

    assert sent == len(expected) >= 2
    assert [value["event_id"] for _, _, value in publisher.sent] == expected, "published in commit order"
    assert await relay_once(session, publisher) == 0, "nothing left to send"
