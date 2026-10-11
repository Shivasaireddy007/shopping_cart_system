from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models import OutboxEvent

ORDERS_TOPIC = "orders"
PRODUCTS_TOPIC = "products"


def add_event(
    session: AsyncSession | Session, topic: str, key: str, event_type: str, payload: dict[str, Any]
) -> None:
    """Records an event in the caller's transaction; the relay publishes it after commit."""
    session.add(OutboxEvent(topic=topic, key=key, event_type=event_type, payload=payload))
