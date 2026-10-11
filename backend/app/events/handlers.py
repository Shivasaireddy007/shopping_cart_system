"""Kafka consumers.

uv run python -m app.events.handlers shipping   # order.paid -> Shiprocket shipment
uv run python -m app.events.handlers search     # product.changed -> OpenSearch
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.consumer import Event, run
from app.events.outbox import ORDERS_TOPIC, PRODUCTS_TOPIC
from app.services import shipments
from app.services.search import index
from app.services.search.client import get_search_client
from app.services.shiprocket import get_shiprocket


async def create_shipment(session: AsyncSession, event: Event) -> None:
    await shipments.create_for_order(session, get_shiprocket(), event["data"]["order_id"])


async def index_product(session: AsyncSession, event: Event) -> None:
    await index.sync(get_search_client(), session, [event["data"]["product_id"]])


WORKERS = {
    "shipping": ("shipping", ORDERS_TOPIC, {"order.paid": create_shipment}),
    "search": ("search-indexer", PRODUCTS_TOPIC, {"product.changed": index_product}),
}

if __name__ == "__main__":
    name, topic, handlers = WORKERS[sys.argv[1]]
    asyncio.run(run(name, topic, handlers))
