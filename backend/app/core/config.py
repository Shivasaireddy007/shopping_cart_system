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


@lru_cache
def get_settings() -> Settings:
    return Settings()
