"""Prometheus metrics and OpenTelemetry tracing.

Metrics are always on and served at /metrics. Tracing is on when OTEL_EXPORTER_OTLP_ENDPOINT
is set (e.g. http://jaeger:4318), and covers requests, SQL, Redis and outgoing HTTP calls.
"""

import os
import time
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_SECONDS = Histogram(
    "http_request_duration_seconds",
    "API request latency",
    ["method", "route", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
CHECKOUTS = Counter("checkouts_total", "Checkout attempts by outcome", ["outcome"])
ORDERS_PAID = Counter("orders_paid_total", "Orders marked paid")
PAID_AMOUNT = Counter("orders_paid_paise_total", "Revenue from paid orders, in paise")
CACHE_LOOKUPS = Counter("catalog_cache_lookups_total", "Catalog cache lookups", ["kind", "result"])

STARTED_AT = time.time()
# Latencies of the most recent API requests, for exact percentiles on the system stats page
# (Prometheus histograms only give bucket bounds).
RECENT_API_SECONDS: deque[float] = deque(maxlen=2000)


def _route_template(request: Request) -> str:
    """The matched route's template, e.g. "/api/v1/products/{slug}", so label values stay bounded.

    A route inside an included router only knows its own part ("/products/{slug}"), so the
    router prefix is recovered from the real path.
    """
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if template is None:
        return "unmatched"
    try:
        concrete = template.format(**request.path_params)
    except (KeyError, IndexError, ValueError):
        return str(template)
    path: str = request.scope["path"]
    prefix = path[: -len(concrete)] if concrete and path.endswith(concrete) else ""
    return prefix + str(template)


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def record_latency(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        route = _route_template(request)
        if route != "/metrics":
            REQUEST_SECONDS.labels(request.method, route, str(response.status_code)).observe(elapsed)
        if route.startswith("/api/v1/") and not route.startswith("/api/v1/system/"):
            RECENT_API_SECONDS.append(elapsed)
        # Shown in the browser's network panel and the demo's request inspector.
        response.headers["Server-Timing"] = f"app;dur={elapsed * 1000:.1f}"
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        _install_tracing(app)


def _install_tracing(app: FastAPI) -> None:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    from app.db import engine

    provider = TracerProvider(
        resource=Resource.create({"service.name": os.environ.get("OTEL_SERVICE_NAME", "shopping-cart-api")})
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
