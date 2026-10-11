"""Runs a Kafka consumer group with once-only handling, retries and a dead-letter topic."""

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from aiokafka import AIOKafkaConsumer
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import SessionLocal
from app.events.publisher import KafkaPublisher, Publisher
from app.models import ProcessedEvent
from app.services import product_changes

log = logging.getLogger(__name__)

Event = dict[str, Any]
Handler = Callable[[AsyncSession, Event], Awaitable[None]]

MAX_ATTEMPTS = 5


async def handle_once(session: AsyncSession, consumer: str, event: Event, handler: Handler) -> bool:
    """Runs the handler unless this consumer already handled the event.

    The "processed" marker is inserted in the handler's transaction, so they commit
    together: a crash before commit means the redelivered event is handled again.
    Returns False for a duplicate.
    """
    claimed = await session.scalar(
        insert(ProcessedEvent)
        .values(consumer=consumer, event_id=uuid.UUID(event["event_id"]))
        .on_conflict_do_nothing()
        .returning(ProcessedEvent.event_id)
    )
    if claimed is None:
        await session.rollback()
        return False

    await handler(session, event)
    await session.commit()
    await product_changes.publish(session)
    return True


async def process_with_retries(
    consumer: str, topic: str, event: Event, handler: Handler, dead_letters: Publisher, delay: float = 1.0
) -> None:
    """Retries with exponential backoff, then parks the event on `<topic>.dlq` for a person to look at."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with SessionLocal() as session:
                await handle_once(session, consumer, event, handler)
            return
        except Exception:
            log.exception(
                "%s failed on %s (attempt %d/%d)", consumer, event.get("event_id"), attempt, MAX_ATTEMPTS
            )
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(delay * 2 ** (attempt - 1))

    await dead_letters.publish(
        f"{topic}.dlq", str(event.get("event_id")), event, {"consumer": consumer, "error": "max attempts"}
    )


async def run(consumer: str, topic: str, handlers: Mapping[str, Handler]) -> None:
    """Consumes `topic`, dispatching on event type, committing offsets only after handling."""
    logging.basicConfig(level=logging.INFO)
    kafka = AIOKafkaConsumer(
        topic,
        bootstrap_servers=get_settings().kafka_bootstrap_servers,
        group_id=consumer,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=json.loads,
    )
    dead_letters = KafkaPublisher()
    await kafka.start()
    await dead_letters.start()
    log.info("%s consuming %s", consumer, topic)
    try:
        async for message in kafka:
            event: Event = message.value
            handler = handlers.get(event.get("type", ""))
            if handler is not None:
                await process_with_retries(consumer, topic, event, handler, dead_letters)
            await kafka.commit()
    finally:
        await kafka.stop()
        await dead_letters.stop()
