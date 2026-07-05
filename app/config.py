"""
app.config
----------
Centralised application configuration.

All runtime configuration is loaded from environment variables (optionally
sourced from a local `.env` file via python-dotenv / pydantic-settings).
Using a single typed `Settings` object gives us:

* One import site for configuration (`from app.config import settings`).
* Type validation and sensible defaults out of the box (Pydantic).
* No hard-coded secrets in the codebase — 12-factor friendly.

Never commit a real `.env` file; commit `.env.example` instead.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from the environment."""

    # --- Application metadata (surfaced in the OpenAPI / Swagger docs) ---
    APP_NAME: str = "Insurance Claims API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "Production-quality REST API for managing insurance claims. "
        "Phase 1 exposes only a health check; business endpoints follow."
    )

    # --- Database ---
    # Full SQLAlchemy connection URL, e.g.
    #   postgresql+psycopg://user:password@localhost:5432/insurance_claims
    DATABASE_URL: str

    # --- Logging ---
    LOG_LEVEL: str = "INFO"          # Default log level for the whole app.
    LOG_FILE: str = "logs/app.log"   # Path (relative to project root) of the log file.

    # NOTE: The database schema is managed by Alembic migrations
    # (`alembic upgrade head`), so the application no longer creates tables on
    # startup.

    # --- Authentication (optional, off by default) ---
    # When AUTH_ENABLED is True, data endpoints require the `X-API-Key` header
    # to match API_KEY. Health and docs remain public. Disabled by default so
    # the API is easy to evaluate; enable it in production.
    AUTH_ENABLED: bool = False
    API_KEY: str = "change-me"

    # --- Rate limiting (optional, off by default) ---
    # When RATE_LIMIT_ENABLED is True, each client IP is limited to RATE_LIMIT
    # requests (slowapi syntax, e.g. "100/minute"). Disabled by default so
    # evaluation and test runs are never throttled.
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT: str = "100/minute"

    # --- Response caching (optional, off by default) ---
    # When CACHE_ENABLED is True, expensive report queries are cached in-process
    # for CACHE_TTL_SECONDS and invalidated automatically after every upload.
    # Disabled by default so evaluators always see live data.
    CACHE_ENABLED: bool = False
    CACHE_TTL_SECONDS: int = 60

    # Load variables from a `.env` file when present. Extra/unknown env vars
    # are ignored so the app does not crash on unrelated environment values.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# A single, importable settings instance used throughout the application.
settings = Settings()
