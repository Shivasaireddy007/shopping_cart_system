"""Pre-cache the most viewed products so they are always served from Redis.

    uv run python -m app.jobs.warm_hot_products

Run it every few minutes from a scheduler.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db import SessionLocal
from app.models import Product
from app.schemas.catalog import ProductOut
from app.services.cache import CatalogCache


async def warm(session: AsyncSession, cache: CatalogCache) -> int:
    """Caches the top viewed products with the long TTL and marks them as hot."""
    ids = await cache.top_products(get_settings().hot_product_count)
    products = (
        await session.scalars(
            select(Product)
            .where(Product.id.in_(ids), Product.is_active.is_(True))
            .options(selectinload(Product.category))
        )
    ).all()
    for product in products:
        await cache.put_product(product.slug, ProductOut.model_validate(product).model_dump_json())
    await cache.set_hot(p.slug for p in products)
    return len(products)


async def main() -> None:
    async with SessionLocal() as session:
        print(f"Warmed {await warm(session, CatalogCache(get_redis()))} hot product(s).")


if __name__ == "__main__":
    asyncio.run(main())
