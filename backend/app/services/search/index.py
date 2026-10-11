"""The products search index.

The configured index name is an alias pointing at a versioned index, so a full rebuild
fills a new index in the background and then swaps the alias in one atomic step.
"""

import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import Product
from app.services.search.client import SearchClient

MAPPING: dict[str, Any] = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "id": {"type": "long"},
            "sku": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "english", "fields": {"raw": {"type": "keyword"}}},
            "description": {"type": "text", "analyzer": "english"},
            "brand": {"type": "keyword"},
            "category": {"type": "keyword"},
            "color": {"type": "keyword"},
            "size": {"type": "keyword"},
            "price": {"type": "long"},
            "in_stock": {"type": "boolean"},
            "created_at": {"type": "date"},
        },
    },
}


def alias() -> str:
    return get_settings().search_index


def document(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "brand": product.brand,
        "category": product.category.slug,
        "color": product.attributes.get("color"),
        "size": product.attributes.get("size"),
        "price": product.price,
        "in_stock": product.stock > 0,
        "created_at": product.created_at.isoformat(),
    }


async def sync(client: SearchClient, session: AsyncSession, product_ids: list[int]) -> None:
    """Indexes the given products, removing inactive or deleted ones, in one bulk request."""
    if not product_ids:
        return
    products = {
        p.id: p
        for p in await session.scalars(
            select(Product).where(Product.id.in_(product_ids)).options(selectinload(Product.category))
        )
    }
    actions: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for product_id in product_ids:
        product = products.get(product_id)
        if product is not None and product.is_active:
            actions.append(({"index": {"_index": alias(), "_id": str(product_id)}}, document(product)))
        else:
            actions.append(({"delete": {"_index": alias(), "_id": str(product_id)}}, None))

    result = await client.bulk(actions)
    del result  # errors other than "not found" on delete would have raised


async def rebuild(client: SearchClient, session: AsyncSession, batch: int = 1000) -> int:
    """Fills a new versioned index with every active product and points the alias at it."""
    # Millisecond timestamp plus a random suffix, so back-to-back or overlapping rebuilds never collide.
    name = f"{alias()}_{datetime.now(UTC):%Y%m%d%H%M%S%f}"[:-3] + f"_{secrets.token_hex(2)}"
    (await client.request("PUT", f"/{name}", MAPPING)).raise_for_status()

    try:
        count, last_id = 0, 0
        while True:
            rows = (
                await session.scalars(
                    select(Product)
                    .where(Product.is_active.is_(True), Product.id > last_id)
                    .options(selectinload(Product.category))
                    .order_by(Product.id)
                    .limit(batch)
                )
            ).all()
            if not rows:
                break
            await client.bulk([({"index": {"_index": name, "_id": str(p.id)}}, document(p)) for p in rows])
            count, last_id = count + len(rows), rows[-1].id

        (await client.request("POST", f"/{name}/_refresh")).raise_for_status()
        await _point_alias(client, name)
    except Exception:
        # Leave the alias on the old index and don't keep a half-built one.
        await client.request("DELETE", f"/{name}")
        raise
    return count


async def _point_alias(client: SearchClient, index: str) -> None:
    current = await client.request("GET", f"/_alias/{alias()}")
    old = list(current.json()) if current.status_code == 200 else []

    # A plain index named like the alias (e.g. auto-created by an early write) must go first.
    if current.status_code == 404 and (await client.request("HEAD", f"/{alias()}")).status_code == 200:
        (await client.request("DELETE", f"/{alias()}")).raise_for_status()

    actions = [{"add": {"index": index, "alias": alias()}}] + [{"remove_index": {"index": o}} for o in old]
    (await client.request("POST", "/_aliases", {"actions": actions})).raise_for_status()
