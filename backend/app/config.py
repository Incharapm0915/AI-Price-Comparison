"""Application configuration.

All runtime settings come from environment variables (see root
`.env.example`). Never hard-code secrets or connection strings here.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    secret_key: str = "dev-only-not-secure"
    api_v1_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+psycopg://price_app:price_app_pw@localhost:5433/price_comparison"

    # Redis / Celery
    redis_url: str = "redis://localhost:6380/0"
    celery_broker_url: str = "redis://localhost:6380/1"
    celery_result_backend: str = "redis://localhost:6380/2"

    # Data collection
    mock_mode: bool = True
    collector_max_results_per_retailer: int = 5
    collector_request_timeout_ms: int = 15000
    collector_max_retries: int = 2
    collector_min_delay_seconds: float = 2.0
    max_reviews_per_product: int = 100
    playwright_headless: bool = True

    # Matching thresholds
    match_threshold_match: float = 0.90
    match_threshold_possible: float = 0.75
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # Optional LLM
    llm_api_key: str = ""
    llm_api_base: str = ""
    llm_model: str = ""

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_from_email: str = "alerts@example.com"

    # Search cache
    search_cache_ttl_seconds: int = 600

    # Celery schedules (Phase 12) — configurable, kept deliberately
    # infrequent so background jobs never hammer retailers.
    price_alert_check_interval_minutes: int = 30
    price_refresh_interval_hours: int = 6
    stale_listing_refresh_days: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
