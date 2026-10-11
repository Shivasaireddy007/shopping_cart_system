"""The outbox relay publishing through a real Kafka broker.

Runs when KAFKA_TEST_BOOTSTRAP points at a reachable broker (CI starts one as a service).
"""

import asyncio
import json
import os
import socket
import uuid

import pytest
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.events.publisher import KafkaPublisher
from app.events.relay import relay_once
from app.models import OutboxEvent

BOOTSTRAP = os.environ.get("KAFKA_TEST_BOOTSTRAP", "")


def _reachable() -> bool:
    if not BOOTSTRAP:
        return False
    host, _, port = BOOTSTRAP.partition(":")
    try:
        socket.create_connection((host, int(port)), timeout=2).close()
        return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="set KAFKA_TEST_BOOTSTRAP to a running Kafka")


async def test_relay_delivers_outbox_events_in_order_with_keys_and_headers(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "kafka_bootstrap_servers", BOOTSTRAP)
    topic = f"test-orders-{uuid.uuid4().hex[:8]}"
    for i in range(3):
        session.add(OutboxEvent(topic=topic, key="ORD-1", event_type="order.paid", payload={"seq": i}))
    await session.flush()

    publisher = KafkaPublisher()
    await publisher.start()
    try:
        assert await relay_once(session, publisher) >= 3
    finally:
        await publisher.stop()

    consumer = AIOKafkaConsumer(
        topic, bootstrap_servers=BOOTSTRAP, auto_offset_reset="earliest", group_id=topic
    )
    await consumer.start()
    try:
        messages = [await asyncio.wait_for(consumer.getone(), 20) for _ in range(3)]
    finally:
        await consumer.stop()

    assert [json.loads(m.value)["data"]["seq"] for m in messages] == [0, 1, 2], "same key keeps order"
    assert {m.key for m in messages} == {b"ORD-1"}
    headers = dict(messages[0].headers)
    assert headers["event_type"] == b"order.paid"
    assert json.loads(messages[0].value)["event_id"] == headers["event_id"].decode()
