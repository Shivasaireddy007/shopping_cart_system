"""Rebuild the product search index without downtime.

uv run python -m app.jobs.reindex
"""

import asyncio
import time

from app.db import SessionLocal
from app.services.search import index
from app.services.search.client import get_search_client


async def main() -> None:
    started = time.perf_counter()
    async with SessionLocal() as session:
        count = await index.rebuild(get_search_client(), session)
    print(f'Indexed {count} products into "{index.alias()}" in {time.perf_counter() - started:.1f}s.')


if __name__ == "__main__":
    asyncio.run(main())
