from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, cart, catalog
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler

DESCRIPTION = """
REST API for the shopping cart: catalog, cart, checkout with Razorpay, Shiprocket shipping,
search and admin catalog management.

**Authentication.** Get tokens from `POST /api/v1/auth/login` and send the access token as
`Authorization: Bearer <token>`. Access tokens last 15 minutes; use `POST /api/v1/auth/refresh`
with the refresh token to get a new pair.

**Money.** All amounts are integers in paise (₹1 = 100 paise), currency INR.

**Errors.** Validation errors return `422`. Stock conflicts return `409` with the available quantity.
"""


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

    for module in (auth, catalog, cart, admin):
        app.include_router(module.router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
