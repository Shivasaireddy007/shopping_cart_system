"""Publishes outbox events to Kafka.

    uv run python -m app.events.relay

Rows are claimed with FOR UPDATE SKIP LOCKED, so several relays can run side by side
without publishing the same event twice in the normal case. A crash between publishing
and committing can re-send a batch; consumers de-duplicate by event id.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.events.publisher import KafkaPublisher, Publisher
from app.models import OutboxEvent

log = logging.getLogger(__name__)


async def relay_once(session: AsyncSession, publisher: Publisher, batch: int = 100) -> int:
    """Publishes one batch of unsent events in id order and marks them sent."""
    events = (
        await session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id)
            .limit(batch)
            .with_for_update(skip_locked=True)
        )
    ).all()

    for event in events:
        await publisher.publish(
            event.topic,
            event.key,
            {"event_id": str(event.event_id), "type": event.event_type, "data": event.payload},
            {"event_id": str(event.event_id), "event_type": event.event_type},
        )
        event.published_at = datetime.now(UTC)

    await session.commit()
    return len(events)


async def main(poll_seconds: float = 0.5) -> None:
    logging.basicConfig(level=logging.INFO)
    publisher = KafkaPublisher()
    await publisher.start()
    try:
        while True:
            try:
                async with SessionLocal() as session:
                    sent = await relay_once(session, publisher)
                if sent:
                    log.info("Published %d event(s)", sent)
                    continue  # more may be waiting
            except Exception:
                log.exception("Relay batch failed; retrying")
            await asyncio.sleep(poll_seconds)
    finally:
        await publisher.stop()


if __name__ == "__main__":
    asyncio.run(main())
