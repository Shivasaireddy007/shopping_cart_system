"""Creating shipments for paid orders, and applying courier status updates."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order, OrderStatus, Shipment, User
from app.services.shiprocket import ShiprocketClient

log = logging.getLogger(__name__)

SHIPPED = {"PICKED UP", "SHIPPED", "IN TRANSIT", "OUT FOR DELIVERY", "REACHED AT DESTINATION HUB"}
DELIVERED = {"DELIVERED"}
RANK = {OrderStatus.paid: 1, OrderStatus.shipped: 2, OrderStatus.delivered: 3}


async def create_for_order(
    session: AsyncSession, shiprocket: ShiprocketClient, order_id: int
) -> Shipment | None:
    """Creates the Shiprocket order and assigns a courier.

    Each step is committed as soon as it succeeds, so if assigning the courier fails, the
    retry continues from there instead of creating a second Shiprocket order.
    """
    if not shiprocket.configured:
        log.info("Shiprocket not configured; order %s will not ship", order_id)
        return None

    order = await session.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    if order is None or order.status != OrderStatus.paid:
        return None
    customer = await session.get(User, order.user_id)
    assert customer is not None

    shipment = await session.scalar(select(Shipment).where(Shipment.order_id == order_id))
    if shipment is None:
        shipment = Shipment(order_id=order_id)
        session.add(shipment)
    if shipment.awb_code:
        return shipment

    if shipment.shiprocket_shipment_id is None:
        shipment.shiprocket_order_id, shipment.shiprocket_shipment_id = await shiprocket.create_order(
            order, customer
        )
        shipment.status = "created"
        await session.commit()

    assert shipment.shiprocket_shipment_id is not None
    shipment.awb_code, shipment.courier_name = await shiprocket.assign_awb(shipment.shiprocket_shipment_id)
    shipment.status = "awb_assigned"
    shipment.status_updated_at = datetime.now(UTC)
    await session.commit()
    return shipment


async def apply_status(session: AsyncSession, awb: str, courier_status: str) -> Shipment | None:
    """Applies a courier update. Updates can arrive late or twice, so the order only moves forward."""
    shipment = await session.scalar(select(Shipment).where(Shipment.awb_code == awb).with_for_update())
    if shipment is None:
        return None
    order = await session.get(Order, shipment.order_id, with_for_update=True)
    assert order is not None

    status = courier_status.strip().upper()
    target = (
        OrderStatus.delivered if status in DELIVERED else OrderStatus.shipped if status in SHIPPED else None
    )
    if target is None or RANK[target] > RANK.get(OrderStatus(order.status), 0):
        shipment.status = status.lower()
        shipment.status_updated_at = datetime.now(UTC)
        if target is not None:
            order.status = target
    return shipment
