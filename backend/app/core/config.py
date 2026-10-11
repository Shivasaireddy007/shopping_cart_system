from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Shopping Cart API"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://postgres@127.0.0.1:5432/shop"
    cors_origins: list[str] = ["http://localhost:5173"]
    web_dir: str | None = None  # serve the built web app from here (the single-container demo)

    jwt_secret: str = "change-me-in-production-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14

    # Amounts are in paise (₹1 = 100 paise).
    shipping_flat_fee: int = 4900
    shipping_free_above: int = 99900
    max_quantity_per_item: int = 10

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_base_url: str = "https://api.razorpay.com/v1"
    # Plays Razorpay's part for the public demo, which has no Razorpay account: no money moves,
    # but payments still pass the usual signature check. Refused alongside real keys.
    demo_payments: bool = False
    unpaid_order_minutes: int = 30

    redis_url: str = "redis://127.0.0.1:6379/0"
    catalog_cache_enabled: bool = True
    listing_cache_seconds: int = 300
    product_cache_seconds: int = 600
    hot_product_cache_seconds: int = 3600
    hot_product_count: int = 100

    search_enabled: bool = True
    search_url: str = "http://127.0.0.1:9200"
    search_index: str = "products"

    kafka_bootstrap_servers: str = "127.0.0.1:9092"

    shiprocket_email: str = ""
    shiprocket_password: str = ""
    shiprocket_pickup_location: str = "Primary"
    shiprocket_webhook_token: str = ""
    shiprocket_base_url: str = "https://apiv2.shiprocket.in/v1/external"

    @field_validator("database_url")
    @classmethod
    def _name_the_async_driver(cls, url: str) -> str:
        """Hosting platforms hand out postgres:// URLs; SQLAlchemy needs the asyncpg driver named."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url.removeprefix(prefix)
        return url

    @model_validator(mode="after")
    def _demo_payments_only_without_real_keys(self) -> Self:
        if self.demo_payments and self.razorpay_key_id:
            raise ValueError("DEMO_PAYMENTS can't be combined with Razorpay keys")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
