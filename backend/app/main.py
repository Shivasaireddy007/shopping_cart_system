from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from app.api.routes import admin, auth, cart, catalog, orders, system, webhooks
from app.core import observability
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.redis import get_redis
from app.db import engine

DESCRIPTION = """
REST API for the shopping cart: catalog, cart, checkout with Razorpay, Shiprocket shipping,
search and admin catalog management.

**Authentication.** Get tokens from `POST /api/v1/auth/login` and send the access token as
`Authorization: Bearer <token>`. Access tokens last 15 minutes; use `POST /api/v1/auth/refresh`
with the refresh token to get a new pair.

**Money.** All amounts are integers in paise (₹1 = 100 paise), currency INR.

**Errors.** Validation errors return `422`. Stock conflicts return `409` with the available quantity.
"""


class SinglePageApp(StaticFiles):
    """The built web app. Unknown paths load index.html so client-side routes survive a reload;
    unknown API paths still get a 404."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", description=DESCRIPTION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    observability.install(app)

    for module in (auth, catalog, cart, orders, admin, system):
        app.include_router(module.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api")

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        """Liveness: the process is up."""
        return {"status": "ok"}

    @app.get("/ready", tags=["Health"], responses={503: {"description": "A dependency is down"}})
    async def ready() -> JSONResponse:
        """Readiness: PostgreSQL and Redis answer, so this instance can take traffic."""
        checks: dict[str, str] = {}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "down"
        try:
            await get_redis().ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "down"
        healthy = all(v == "ok" for v in checks.values())
        return JSONResponse(
            {"status": "ok" if healthy else "unavailable", **checks}, status_code=200 if healthy else 503
        )

    if settings.web_dir:
        # Mounted last, so the API routes above take precedence.
        app.mount("/", SinglePageApp(directory=settings.web_dir, html=True), name="web")

    return app


app = create_app()
