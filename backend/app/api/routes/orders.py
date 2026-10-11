import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.core.redis import get_redis
from app.models import Order, OrderStatus, Shipment
from app.schemas.common import Page
from app.schemas.orders import (
    CheckoutIn,
    CheckoutOut,
    OrderOut,
    RazorpayCheckout,
    TrackingEvent,
    TrackingOut,
    VerifyPaymentIn,
)
from app.services import orders, payments
from app.services.razorpay import RazorpayClient, get_razorpay
from app.services.shiprocket import ShiprocketClient, get_shiprocket

router = APIRouter(tags=["Checkout and orders"])

RazorpayDep = Annotated[RazorpayClient, Depends(get_razorpay)]


async def _own_order(session: SessionDep, user_id: int, number: str) -> Order:
    order = await session.scalar(
        select(Order)
        .where(Order.number == number, Order.user_id == user_id)
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found.")
    return order


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(
    data: CheckoutIn, user: CurrentUser, session: SessionDep, razorpay: RazorpayDep
) -> CheckoutOut:
    """Place an order from the cart and get the details to open Razorpay Checkout.

    Returns `409` if stock ran out and `502` if Razorpay is unavailable (the order is
    cancelled and the cart kept).
    """
    order = await orders.checkout(session, razorpay, user.id, data.shipping_address.model_dump())
    assert order.razorpay_order_id is not None
    return CheckoutOut(
        order=OrderOut.model_validate(order),
        razorpay=RazorpayCheckout(
            key_id=razorpay.key_id,
            order_id=order.razorpay_order_id,
            amount=order.total,
            currency=order.currency,
        ),
    )


@router.get("/orders")
async def list_orders(
    user: CurrentUser, session: SessionDep, page: Annotated[int, Query(ge=1)] = 1
) -> Page[OrderOut]:
    """List your orders, newest first."""
    per_page = 10
    total = await session.scalar(select(func.count(Order.id)).where(Order.user_id == user.id)) or 0
    rows = await session.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    return Page(items=[OrderOut.model_validate(o) for o in rows], total=total, page=page, per_page=per_page)


@router.get("/orders/{number}")
async def get_order(number: str, user: CurrentUser, session: SessionDep) -> OrderOut:
    """Get one of your orders."""
    return OrderOut.model_validate(await _own_order(session, user.id, number))


@router.post("/orders/{number}/payment")
async def retry_payment(
    number: str, user: CurrentUser, session: SessionDep, razorpay: RazorpayDep
) -> RazorpayCheckout:
    """Get the Razorpay details again to pay an unpaid order, e.g. after closing the payment window."""
    order = await _own_order(session, user.id, number)
    if order.status != OrderStatus.pending_payment or order.razorpay_order_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This order can't be paid.")
    return RazorpayCheckout(
        key_id=razorpay.key_id, order_id=order.razorpay_order_id, amount=order.total, currency=order.currency
    )


@router.post("/orders/{number}/verify-payment")
async def verify_payment(
    number: str, data: VerifyPaymentIn, user: CurrentUser, session: SessionDep, razorpay: RazorpayDep
) -> OrderOut:
    """Confirm a payment with the signature Razorpay Checkout returned. `422` if the signature is wrong."""
    order = await _own_order(session, user.id, number)
    if order.razorpay_order_id is None or not razorpay.is_valid_payment_signature(
        order.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid payment signature.")

    await payments.record_captured(session, order.razorpay_order_id, data.razorpay_payment_id, order.total)
    await session.commit()
    return OrderOut.model_validate(await _own_order(session, user.id, number))


@router.post("/orders/{number}/cancel")
async def cancel_order(number: str, user: CurrentUser, session: SessionDep) -> OrderOut:
    """Cancel an unpaid order and release its stock. `409` once it is paid."""
    order = await _own_order(session, user.id, number)
    if not await orders.cancel(session, order.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "This order can no longer be cancelled.")
    return OrderOut.model_validate(await _own_order(session, user.id, number))


log = logging.getLogger(__name__)


@router.get("/orders/{number}/tracking")
async def tracking(
    number: str,
    user: CurrentUser,
    session: SessionDep,
    shiprocket: Annotated[ShiprocketClient, Depends(get_shiprocket)],
) -> TrackingOut:
    """Courier, AWB and tracking timeline for an order. The timeline is cached for 10 minutes."""
    order = await _own_order(session, user.id, number)
    shipment = await session.scalar(select(Shipment).where(Shipment.order_id == order.id))
    if shipment is None or shipment.awb_code is None:
        return TrackingOut(status=order.status, courier_name=None, awb_code=None, track_url=None, events=[])

    key = f"tracking:{shipment.awb_code}"
    redis = get_redis()
    if cached := await redis.get(key):
        data = json.loads(cached)
    else:
        try:
            data = await shiprocket.track(shipment.awb_code)
            await redis.set(key, json.dumps(data), ex=600)
        except httpx.HTTPError:
            log.warning("Could not fetch tracking for %s", shipment.awb_code, exc_info=True)
            data = {}

    return TrackingOut(
        status=order.status,
        courier_name=shipment.courier_name,
        awb_code=shipment.awb_code,
        track_url=data.get("track_url"),
        events=[
            TrackingEvent(date=a.get("date", ""), activity=a.get("activity", ""), location=a.get("location"))
            for a in data.get("shipment_track_activities") or []
        ],
    )
