import json
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus, Payment, User
from tests.conftest import ADDRESS, Factory, FakeRazorpay, auth_header


@pytest.fixture
async def placed(client: AsyncClient, factory: Factory) -> tuple[User, dict[str, Any]]:
    """A customer with an unpaid ₹1,200 order."""
    user = await factory.user()
    await factory.cart_with(user, (await factory.product(price=120000, stock=5), 1))
    body = (
        await client.post("/api/v1/checkout", json={"shipping_address": ADDRESS}, headers=auth_header(user))
    ).json()
    return user, body


def webhook_body(
    event: str, razorpay_order_id: str, payment_id: str, amount: int, error: str | None = None
) -> bytes:
    entity = {"id": payment_id, "order_id": razorpay_order_id, "amount": amount, "method": "upi"}
    if error:
        entity["error_description"] = error
    return json.dumps({"event": event, "payload": {"payment": {"entity": entity}}}).encode()


async def send_webhook(client: AsyncClient, razorpay: FakeRazorpay, event_id: str, body: bytes) -> Response:
    return await client.post(
        "/api/webhooks/razorpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Event-Id": event_id,
            "X-Razorpay-Signature": razorpay.webhook_signature(body),
        },
    )


async def order_status(session: AsyncSession) -> str:
    return str(await session.scalar(select(Order.status).execution_options(populate_existing=True)))


async def test_valid_checkout_signature_marks_order_paid(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    user, body = placed
    rzp_order = body["razorpay"]["order_id"]

    response = await client.post(
        f"/api/v1/orders/{body['order']['number']}/verify-payment",
        json={
            "razorpay_payment_id": "pay_1",
            "razorpay_signature": razorpay.payment_signature(rzp_order, "pay_1"),
        },
        headers=auth_header(user),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    payment = await session.scalar(select(Payment))
    assert payment is not None and (payment.status, payment.amount) == ("captured", 120000)


async def test_forged_signature_is_rejected(
    client: AsyncClient, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    user, body = placed

    response = await client.post(
        f"/api/v1/orders/{body['order']['number']}/verify-payment",
        json={"razorpay_payment_id": "pay_1", "razorpay_signature": "forged"},
        headers=auth_header(user),
    )

    assert response.status_code == 422
    assert await order_status(session) == OrderStatus.pending_payment


async def test_webhook_marks_order_paid(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    _, body = placed
    event = webhook_body("payment.captured", body["razorpay"]["order_id"], "pay_2", 120000)

    response = await send_webhook(client, razorpay, "evt_1", event)

    assert response.json() == {"status": "ok"}
    assert await order_status(session) == OrderStatus.paid


async def test_repeated_delivery_is_processed_once(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    _, body = placed
    event = webhook_body("payment.captured", body["razorpay"]["order_id"], "pay_2", 120000)

    assert (await send_webhook(client, razorpay, "evt_1", event)).json() == {"status": "ok"}
    assert (await send_webhook(client, razorpay, "evt_1", event)).json() == {"status": "duplicate"}
    assert await session.scalar(select(func.count(Payment.id))) == 1


async def test_callback_and_webhook_for_the_same_payment_record_it_once(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    user, body = placed
    rzp_order = body["razorpay"]["order_id"]

    await client.post(
        f"/api/v1/orders/{body['order']['number']}/verify-payment",
        json={
            "razorpay_payment_id": "pay_3",
            "razorpay_signature": razorpay.payment_signature(rzp_order, "pay_3"),
        },
        headers=auth_header(user),
    )
    await send_webhook(
        client, razorpay, "evt_9", webhook_body("payment.captured", rzp_order, "pay_3", 120000)
    )

    assert await session.scalar(select(func.count(Payment.id))) == 1
    assert await order_status(session) == OrderStatus.paid


async def test_webhook_with_bad_signature_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/webhooks/razorpay", content=b"{}", headers={"X-Razorpay-Signature": "nope"}
    )

    assert response.status_code == 400


async def test_amount_mismatch_does_not_mark_paid(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    _, body = placed

    await send_webhook(
        client,
        razorpay,
        "evt_2",
        webhook_body("payment.captured", body["razorpay"]["order_id"], "pay_4", 100),
    )

    assert await order_status(session) == OrderStatus.pending_payment


async def test_failed_payment_is_recorded_and_order_stays_payable(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    _, body = placed

    await send_webhook(
        client,
        razorpay,
        "evt_3",
        webhook_body("payment.failed", body["razorpay"]["order_id"], "pay_5", 120000, "Card declined"),
    )

    payment = await session.scalar(select(Payment))
    assert payment is not None and (payment.status, payment.error_description) == ("failed", "Card declined")
    assert await order_status(session) == OrderStatus.pending_payment


async def test_late_failure_does_not_downgrade_a_captured_payment(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    _, body = placed
    rzp_order = body["razorpay"]["order_id"]

    await send_webhook(
        client, razorpay, "evt_4", webhook_body("payment.captured", rzp_order, "pay_6", 120000)
    )
    await send_webhook(
        client, razorpay, "evt_5", webhook_body("payment.failed", rzp_order, "pay_6", 120000, "late")
    )

    payment = await session.scalar(select(Payment).execution_options(populate_existing=True))
    assert payment is not None and payment.status == "captured"


async def test_payment_for_a_cancelled_order_does_not_revive_it(
    client: AsyncClient, razorpay: FakeRazorpay, placed: tuple[User, dict[str, Any]], session: AsyncSession
) -> None:
    user, body = placed
    await client.post(f"/api/v1/orders/{body['order']['number']}/cancel", headers=auth_header(user))

    await send_webhook(
        client,
        razorpay,
        "evt_6",
        webhook_body("payment.captured", body["razorpay"]["order_id"], "pay_7", 120000),
    )

    assert await order_status(session) == OrderStatus.cancelled
