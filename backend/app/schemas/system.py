from datetime import datetime

from pydantic import BaseModel


class LatencyStats(BaseModel):
    requests: int = 0
    p50_ms: float | None = None
    p95_ms: float | None = None


class CacheStats(BaseModel):
    hits: int = 0
    misses: int = 0
    hit_rate: float | None = None


class RecentEvent(BaseModel):
    topic: str
    event_type: str
    created_at: datetime


class SystemStats(BaseModel):
    """Live numbers from this server, for the How it's built page."""

    uptime_seconds: int
    commit: str | None
    python: str
    postgres: str
    redis: str | None
    demo: bool
    latency: LatencyStats
    cache: CacheStats
    checkouts: dict[str, int]
    products: int
    orders: int
    outbox_events: int
    recent_events: list[RecentEvent]


class ExperimentAttempt(BaseModel):
    buyer: int
    sold: bool
    ms: float


class ExperimentOut(BaseModel):
    locked: bool
    units: int
    attempts: list[ExperimentAttempt]
    sold: int
    final_stock: int
    ms: float
