from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Shared Redis client; responses are decoded to str."""
    global _redis
    _redis = _redis or Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis
