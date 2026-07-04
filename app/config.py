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

    # --- Development conveniences ---
    # When True, tables are auto-created on startup (handy in development).
    # In production this should be False and schema managed via migrations.
    AUTO_CREATE_TABLES: bool = True

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
