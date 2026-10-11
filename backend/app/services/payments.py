"""Records Razorpay payments.

The checkout callback and the webhook can both report the same payment, and webhooks
can repeat or arrive out of order, so every function here is idempotent. Callers commit.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.outbox import ORDERS_TOPIC, add_event
from app.models import Order, OrderStatus, Payment

log = logging.getLogger(__name__)


async def record_captured(
    session: AsyncSession, razorpay_order_id: str, payment_id: str, amount: int, method: str | None = None
) -> Order | None:
    order = await session.scalar(
        select(Order).where(Order.razorpay_order_id == razorpay_order_id).with_for_update()
    )
    if order is None:
        log.warning("Payment %s for unknown Razorpay order %s", payment_id, razorpay_order_id)
        return None

    await _upsert_payment(session, order, payment_id, amount, "captured", method)

    if order.paid_at is not None:
        return order
    if amount != order.total:
        log.critical("Order %s: captured %s but total is %s", order.number, amount, order.total)
        return order
    if order.status == OrderStatus.cancelled:
        log.critical(
            "Order %s was cancelled but payment %s was captured; refund it", order.number, payment_id
        )
        return order

    order.status = OrderStatus.paid
    order.paid_at = datetime.now(UTC)
    add_event(
        session, ORDERS_TOPIC, order.number, "order.paid", {"order_id": order.id, "number": order.number}
    )
    return order


async def record_failed(
    session: AsyncSession, razorpay_order_id: str, payment_id: str, amount: int, error: str | None
) -> None:
    order = await session.scalar(select(Order).where(Order.razorpay_order_id == razorpay_order_id))
    if order is not None:
        await _upsert_payment(session, order, payment_id, amount, "failed", None, error)


async def _upsert_payment(
    session: AsyncSession,
    order: Order,
    payment_id: str,
    amount: int,
    status: str,
    method: str | None,
    error: str | None = None,
) -> None:
    payment = await session.scalar(
        select(Payment).where(Payment.razorpay_payment_id == payment_id).with_for_update()
    )
    if payment is None:
        session.add(
            Payment(
                order_id=order.id,
                razorpay_payment_id=payment_id,
                amount=amount,
                status=status,
                method=method,
                error_description=error,
            )
        )
        return

    # A late "failed" event must never downgrade a captured payment.
    if payment.status == "captured":
        return
    payment.status = status
    payment.amount = amount
    payment.method = method or payment.method
    payment.error_description = error
