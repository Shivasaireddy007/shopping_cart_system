import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OutboxEvent(Base):
    """An event written in the same transaction as the change it describes.

    A relay publishes unsent rows to Kafka, so an event is never lost if the app crashes
    after committing, and never sent for a change that rolled back.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        # Only unsent rows are indexed, so the relay's query stays fast however big the table grows.
        Index("ix_outbox_events_unsent", "id", postgresql_where=text("published_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    topic: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(
        String(128), comment="Kafka message key; events with one key stay in order"
    )
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessedEvent(Base):
    """Events a consumer has handled. Kafka delivers at least once; this makes handling once."""

    __tablename__ = "processed_events"

    consumer: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
