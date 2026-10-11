import os
import platform
import statistics
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from prometheus_client import Counter
from redis.exceptions import RedisError
from sqlalchemy import func, select, text

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.observability import CACHE_LOOKUPS, CHECKOUTS, RECENT_API_SECONDS, STARTED_AT
from app.core.redis import get_redis
from app.models import Order, OutboxEvent, Product
from app.schemas.system import (
    CacheStats,
    ExperimentAttempt,
    ExperimentOut,
    LatencyStats,
    RecentEvent,
    SystemStats,
)
from app.services import oversell_experiment
from app.services.razorpay import RazorpayClient, get_razorpay

router = APIRouter(prefix="/system", tags=["System"])


def _counter_totals(counter: Counter, label: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                key = sample.labels[label]
                totals[key] = totals.get(key, 0) + int(sample.value)
    return totals


def _latency() -> LatencyStats:
    recent = list(RECENT_API_SECONDS)
    if len(recent) < 2:
        return LatencyStats(requests=len(recent))
    cuts = statistics.quantiles(recent, n=100, method="inclusive")
    return LatencyStats(
        requests=len(recent), p50_ms=round(cuts[49] * 1000, 1), p95_ms=round(cuts[94] * 1000, 1)
    )


async def _redis_version() -> str | None:
    try:
        info = await get_redis().info("server")
    except RedisError:
        return None
    version = info.get("valkey_version") or info.get("redis_version")
    return str(version) if version else None


@router.get("/stats")
async def stats(session: SessionDep) -> SystemStats:
    """Live numbers from this server: latency of recent API reads, cache hit rate, checkout
    outcomes and the latest events written to the outbox."""
    cache = _counter_totals(CACHE_LOOKUPS, "result")
    hits, misses = cache.get("hit", 0), cache.get("miss", 0)
    events = await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id.desc()).limit(8))
    commit = os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_COMMIT")
    return SystemStats(
        uptime_seconds=int(time.time() - STARTED_AT),
        commit=commit[:7] if commit else None,
        python=platform.python_version(),
        postgres=str(await session.scalar(text("SHOW server_version"))).split(" ")[0],
        redis=await _redis_version(),
        demo=get_settings().demo_payments,
        latency=_latency(),
        cache=CacheStats(
            hits=hits, misses=misses, hit_rate=hits / (hits + misses) if hits + misses else None
        ),
        checkouts=_counter_totals(CHECKOUTS, "outcome"),
        products=await session.scalar(select(func.count()).where(Product.is_active)) or 0,
        orders=await session.scalar(select(func.count(Order.id))) or 0,
        outbox_events=await session.scalar(select(func.count(OutboxEvent.id))) or 0,
        recent_events=[RecentEvent.model_validate(e, from_attributes=True) for e in events],
    )


@router.post(
    "/oversell-experiment",
    responses={404: {"description": "Not a demo server"}, 429: {"description": "One is already running"}},
)
async def oversell_experiment_run(
    razorpay: Annotated[RazorpayClient, Depends(get_razorpay)],
    locked: Annotated[bool, Query(description="Use the real, row-locking checkout")] = True,
) -> ExperimentOut:
    """Public demo only: ten buyers check out the last three units at the same moment, on
    separate database connections. With `locked=true` the real checkout runs; with `false`, a
    naive read-then-write version shows the race the lock prevents."""
    if not razorpay.demo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    try:
        outcome = await oversell_experiment.run(razorpay, locked=locked)
    except oversell_experiment.ExperimentBusy:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "An experiment is running, try again."
        ) from None
    return ExperimentOut(
        locked=outcome.locked,
        units=outcome.units,
        attempts=[ExperimentAttempt(buyer=a.buyer, sold=a.sold, ms=round(a.ms, 1)) for a in outcome.attempts],
        sold=sum(a.sold for a in outcome.attempts),
        final_stock=outcome.final_stock,
        ms=round(outcome.ms, 1),
    )
