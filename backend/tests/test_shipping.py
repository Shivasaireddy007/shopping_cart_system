import uuid
from datetime import UTC, datetime

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.consumer import handle_once
from app.models import Order, OrderStatus, Shipment, User
from app.services import shipments
from tests.conftest import ADDRESS, Factory, FakeShiprocket, auth_header


async def paid_order(client: AsyncClient, factory: Factory, session: AsyncSession) -> tuple[User, Order]:
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(price=150000, weight_grams=750, stock=10), 2))
    number = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user))
    ).json()["order"]["number"]
    await session.execute(update(Order).values(status=OrderStatus.paid, paid_at=datetime.now(UTC)))
    await session.commit()
    order = await session.scalar(
        select(Order).where(Order.number == number).execution_options(populate_existing=True)
    )
    assert order is not None
    return user, order


async def test_shipment_is_created_and_a_courier_assigned(
    client: AsyncClient, factory: Factory, session: AsyncSession, shiprocket: FakeShiprocket
) -> None:
    _, order = await paid_order(client, factory, session)

    shipment = await shipments.create_for_order(session, shiprocket.client, order.id)

    assert shipment is not None and (shipment.awb_code, shipment.courier_name) == ("AWB123", "Delhivery")
    _, _, body = next(c for c in shiprocket.calls if c[1] == "/orders/create/adhoc")
    assert (body["order_id"], body["payment_method"], body["weight"]) == (order.number, "Prepaid", 1.5)


async def test_retry_after_courier_failure_does_not_create_a_second_shiprocket_order(
    client: AsyncClient, factory: Factory, session: AsyncSession, shiprocket: FakeShiprocket
) -> None:
    _, order = await paid_order(client, factory, session)
    shiprocket.awb_failures = 1

    with pytest.raises(httpx.HTTPStatusError):
        await shipments.create_for_order(session, shiprocket.client, order.id)
    await session.rollback()
    shipment = await shipments.create_for_order(session, shiprocket.client, order.id)

    assert shiprocket.paths().count("/orders/create/adhoc") == 1
    assert shipment is not None and shipment.awb_code == "AWB123"


async def test_unconfigured_shiprocket_skips_shipping(
    client: AsyncClient, factory: Factory, session: AsyncSession
) -> None:
    _, order = await paid_order(client, factory, session)

    assert (
        await shipments.create_for_order(session, FakeShiprocket(configured=False).client, order.id) is None
    )


async def test_consumer_handles_each_event_once(factory: Factory, session: AsyncSession) -> None:
    calls: list[str] = []

    async def handler(_: AsyncSession, event: dict) -> None:  # type: ignore[type-arg]
        calls.append(event["event_id"])

    event = {"event_id": str(uuid.uuid4()), "type": "order.paid", "data": {}}

    assert await handle_once(session, "shipping", event, handler) is True
    assert await handle_once(session, "shipping", event, handler) is False
    assert await handle_once(session, "search-indexer", event, handler) is True, (
        "each consumer tracks its own"
    )
    assert len(calls) == 2


async def shiprocket_webhook(client: AsyncClient, awb: str, status: str, token: str = "ship-token"):  # type: ignore[no-untyped-def]
    from app.core.config import get_settings

    get_settings().shiprocket_webhook_token = "ship-token"
    return await client.post(
        "/api/webhooks/shiprocket", json={"awb": awb, "current_status": status}, headers={"x-api-key": token}
    )


async def test_webhook_moves_the_order_forward_only(
    client: AsyncClient, factory: Factory, session: AsyncSession, shiprocket: FakeShiprocket
) -> None:
    _, order = await paid_order(client, factory, session)
    await shipments.create_for_order(session, shiprocket.client, order.id)

    assert (await shiprocket_webhook(client, "AWB123", "IN TRANSIT")).json() == {"status": "ok"}
    await shiprocket_webhook(client, "AWB123", "DELIVERED")
    await shiprocket_webhook(client, "AWB123", "OUT FOR DELIVERY")  # arrives late

    status = await session.scalar(
        select(Order.status).where(Order.id == order.id).execution_options(populate_existing=True)
    )
    assert status == OrderStatus.delivered


async def test_webhook_rejects_a_bad_token_and_ignores_repeats(
    client: AsyncClient, factory: Factory, session: AsyncSession, shiprocket: FakeShiprocket
) -> None:
    _, order = await paid_order(client, factory, session)
    await shipments.create_for_order(session, shiprocket.client, order.id)

    assert (await shiprocket_webhook(client, "AWB123", "IN TRANSIT", token="wrong")).status_code == 401
    assert (await shiprocket_webhook(client, "AWB123", "IN TRANSIT")).json() == {"status": "ok"}
    assert (await shiprocket_webhook(client, "AWB123", "IN TRANSIT")).json() == {"status": "duplicate"}


async def test_tracking_shows_the_courier_timeline(
    client: AsyncClient, factory: Factory, session: AsyncSession, shiprocket: FakeShiprocket
) -> None:
    user, order = await paid_order(client, factory, session)
    before = (await client.get(f"/api/v1/orders/{order.number}/tracking", headers=auth_header(user))).json()
    assert before["awb_code"] is None

    await shipments.create_for_order(session, shiprocket.client, order.id)
    body = (await client.get(f"/api/v1/orders/{order.number}/tracking", headers=auth_header(user))).json()

    assert (body["awb_code"], body["courier_name"]) == ("AWB123", "Delhivery")
    assert body["events"][0]["activity"] == "In transit"


async def test_admin_lists_orders_and_shipments(
    client: AsyncClient, factory: Factory, session: AsyncSession, shiprocket: FakeShiprocket
) -> None:
    admin = await factory.user(is_admin=True)
    user, order = await paid_order(client, factory, session)
    await shipments.create_for_order(session, shiprocket.client, order.id)

    orders = (await client.get("/api/v1/admin/orders", headers=auth_header(admin))).json()
    ships = (await client.get("/api/v1/admin/shipments", headers=auth_header(admin))).json()
    customer = await client.get("/api/v1/admin/orders", headers=auth_header(user))

    assert orders["items"][0]["number"] == order.number
    assert (orders["items"][0]["shipment_status"], orders["items"][0]["awb_code"]) == (
        "awb_assigned",
        "AWB123",
    )
    assert ships["items"][0]["order_number"] == order.number
    assert customer.status_code == 403
    assert await session.scalar(select(Shipment.status)) == "awb_assigned"
