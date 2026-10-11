from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Shopping Cart API"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://postgres@127.0.0.1:5432/shop"
    cors_origins: list[str] = ["http://localhost:5173"]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
