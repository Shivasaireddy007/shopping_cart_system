import json
from typing import Any, Protocol

from aiokafka import AIOKafkaProducer

from app.core.config import get_settings


class Publisher(Protocol):
    async def publish(self, topic: str, key: str, value: dict[str, Any], headers: dict[str, str]) -> None: ...


class KafkaPublisher:
    """Idempotent Kafka producer: acks from all replicas, no duplicates from producer retries."""

    def __init__(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=get_settings().kafka_bootstrap_servers,
            enable_idempotence=True,
            acks="all",
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=str.encode,
        )

    async def start(self) -> None:
        await self._producer.start()

    async def stop(self) -> None:
        await self._producer.stop()

    async def publish(self, topic: str, key: str, value: dict[str, Any], headers: dict[str, str]) -> None:
        await self._producer.send_and_wait(
            topic, value=value, key=key, headers=[(k, v.encode()) for k, v in headers.items()]
        )
