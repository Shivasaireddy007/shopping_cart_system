import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import AppError, BadGateway, InsufficientStock, NotFound
from app.events.outbox import ORDERS_TOPIC, add_event
from app.models import Cart, CartItem, Order, OrderItem, OrderStatus, Product
from app.services.razorpay import RazorpayClient, RazorpayError
from app.services.shipping import shipping_fee

log = logging.getLogger(__name__)


class EmptyCart(AppError):
    status_code = 422


def new_order_number() -> str:
    return f"ORD-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"


async def load_order(session: AsyncSession, order_id: int) -> Order:
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    assert order is not None
    return order


async def checkout(
    session: AsyncSession, razorpay: RazorpayClient, user_id: int, address: dict[str, Any]
) -> Order:
    """Turns the user's cart into an order and opens a Razorpay order for it.

    Stock is reserved in one transaction with the product rows locked in id order, so
    concurrent checkouts can neither oversell nor deadlock. That transaction commits
    before Razorpay is called, so no locks are held during the network call. If Razorpay
    fails, the order is cancelled, which releases the stock, and the cart is kept.
    """
    cart = await session.scalar(select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items)))
    if cart is None or not cart.items:
        raise EmptyCart("Your cart is empty.")

    order = await _reserve(session, user_id, cart.items, address)
    await session.commit()

    try:
        razorpay_order_id = await razorpay.create_order(order.total, order.number)
    except RazorpayError:
        log.exception("Razorpay order creation failed for %s", order.number)
        await cancel(session, order.id)
        raise BadGateway("Payment provider is unavailable, please try again.") from None

    order.razorpay_order_id = razorpay_order_id
    for item in cart.items:
        await session.delete(item)
    await session.commit()
    return await load_order(session, order.id)


async def _reserve(
    session: AsyncSession, user_id: int, cart_items: list[CartItem], address: dict[str, Any]
) -> Order:
    quantities = {item.product_id: item.quantity for item in cart_items}
    products = (
        await session.scalars(
            select(Product).where(Product.id.in_(quantities)).order_by(Product.id).with_for_update()
        )
    ).all()

    lines = []
    for product in products:
        quantity = quantities[product.id]
        if not product.is_in_stock(quantity):
            raise InsufficientStock(product.sku, product.stock if product.is_active else 0, quantity)
        product.stock -= quantity
        lines.append(
            OrderItem(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                unit_price=product.price,
                quantity=quantity,
                line_total=product.price * quantity,
                weight_grams=product.weight_grams,
            )
        )

    if len(products) != len(quantities):
        raise NotFound("A product in your cart no longer exists.")

    subtotal = sum(line.line_total for line in lines)
    fee = shipping_fee(subtotal)
    order = Order(
        number=new_order_number(),
        user_id=user_id,
        status=OrderStatus.pending_payment,
        subtotal=subtotal,
        shipping_fee=fee,
        total=subtotal + fee,
        shipping_address=address,
        items=lines,
    )
    session.add(order)
    await session.flush()
    return order


async def cancel(session: AsyncSession, order_id: int) -> bool:
    """Cancels an unpaid order and puts its stock back.

    Returns False if the order is no longer awaiting payment, e.g. it was paid meanwhile.
    """
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None or order.status != OrderStatus.pending_payment:
        await session.rollback()
        return False

    quantities = {item.product_id: item.quantity for item in order.items if item.product_id is not None}
    products = await session.scalars(
        select(Product).where(Product.id.in_(quantities)).order_by(Product.id).with_for_update()
    )
    for product in products:
        product.stock += quantities[product.id]

    order.status = OrderStatus.cancelled
    order.cancelled_at = datetime.now(UTC)
    add_event(
        session, ORDERS_TOPIC, order.number, "order.cancelled", {"order_id": order.id, "number": order.number}
    )
    await session.commit()
    return True


async def expire_unpaid(session: AsyncSession, older_than_minutes: int | None = None) -> int:
    """Cancels orders left unpaid for too long and returns how many were cancelled."""
    minutes = older_than_minutes if older_than_minutes is not None else get_settings().unpaid_order_minutes
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    ids = (
        await session.scalars(
            select(Order.id).where(Order.status == OrderStatus.pending_payment, Order.created_at < cutoff)
        )
    ).all()
    await session.commit()

    cancelled = 0
    for order_id in ids:
        cancelled += await cancel(session, order_id)
    return cancelled
