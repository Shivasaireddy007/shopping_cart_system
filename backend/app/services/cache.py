"""Read-through Redis cache for catalog pages.

Listing keys embed a catalog version. Any product change increments the version, which
retires every cached listing at once without scanning or deleting keys; old entries just
expire. Product pages are cached per slug and deleted when that product changes.
"""

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.observability import CACHE_LOOKUPS

log = logging.getLogger(__name__)

VERSION_KEY = "catalog:version"
HOT_KEY = "catalog:hot"
VIEWS_PREFIX = "catalog:views:"


def _product_key(slug: str) -> str:
    return f"catalog:product:{slug}"


class CatalogCache:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.settings = get_settings()

    async def listing(self, filters: dict[str, Any], build: Callable[[], Awaitable[str]]) -> str:
        """Returns the cached JSON for a listing, building and storing it on a miss."""
        if not self.settings.catalog_cache_enabled:
            return await build()
        try:
            version = str(await self.redis.get(VERSION_KEY) or "0")
            digest = hashlib.md5(json.dumps(filters, sort_keys=True, default=str).encode()).hexdigest()
            key = f"catalog:list:v{version}:{digest}"
            if (cached := await self.redis.get(key)) is not None:
                CACHE_LOOKUPS.labels("listing", "hit").inc()
                return str(cached)
            CACHE_LOOKUPS.labels("listing", "miss").inc()
        except RedisError:
            log.warning("Redis unavailable, serving listing uncached", exc_info=True)
            return await build()

        payload = await build()
        await self._set(key, payload, self.settings.listing_cache_seconds)
        return payload

    async def product(self, slug: str, build: Callable[[], Awaitable[str | None]]) -> str | None:
        """Returns the cached JSON for a product page. Hot products are kept longer."""
        if not self.settings.catalog_cache_enabled:
            return await build()
        try:
            if (cached := await self.redis.get(_product_key(slug))) is not None:
                CACHE_LOOKUPS.labels("product", "hit").inc()
                return str(cached)
            CACHE_LOOKUPS.labels("product", "miss").inc()
            hot = await self.redis.sismember(HOT_KEY, slug)
        except RedisError:
            log.warning("Redis unavailable, serving product uncached", exc_info=True)
            return await build()

        payload = await build()
        if payload is not None:
            ttl = self.settings.hot_product_cache_seconds if hot else self.settings.product_cache_seconds
            await self._set(_product_key(slug), payload, ttl)
        return payload

    async def put_product(self, slug: str, payload: str) -> None:
        await self._set(_product_key(slug), payload, self.settings.hot_product_cache_seconds)

    async def set_hot(self, slugs: Iterable[str]) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(HOT_KEY)
            if slugs := list(slugs):
                pipe.sadd(HOT_KEY, *slugs)
            await pipe.execute()

    async def invalidate(self, slugs: Iterable[str]) -> None:
        """Called after products change: drops their pages and retires all cached listings."""
        try:
            async with self.redis.pipeline(transaction=False) as pipe:
                pipe.incr(VERSION_KEY)
                if keys := [_product_key(slug) for slug in slugs]:
                    pipe.delete(*keys)
                await pipe.execute()
        except RedisError:
            log.exception("Could not invalidate catalog cache")

    async def record_view(self, product_id: int) -> None:
        """Counts a product view in this hour's sorted set (kept for 26 hours)."""
        key = VIEWS_PREFIX + datetime.now(UTC).strftime("%Y%m%d%H")
        try:
            async with self.redis.pipeline(transaction=False) as pipe:
                pipe.zincrby(key, 1, str(product_id))
                pipe.expire(key, 26 * 3600)
                await pipe.execute()
        except RedisError:
            log.warning("Could not record product view", exc_info=True)

    async def top_products(self, limit: int, hours: int = 24) -> list[int]:
        """Most viewed product ids over the last `hours` hours."""
        now = datetime.now(UTC)
        keys = [VIEWS_PREFIX + (now - timedelta(hours=h)).strftime("%Y%m%d%H") for h in range(hours)]
        destination = f"{VIEWS_PREFIX}window:{now:%Y%m%d%H%M%S%f}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zunionstore(destination, keys)
            pipe.zrevrange(destination, 0, limit - 1)
            pipe.delete(destination)
            _, ids, _ = await pipe.execute()
        return [int(i) for i in ids]

    async def _set(self, key: str, value: str, ttl: int) -> None:
        try:
            await self.redis.set(key, value, ex=ttl)
        except RedisError:
            log.warning("Could not write %s to cache", key, exc_info=True)
