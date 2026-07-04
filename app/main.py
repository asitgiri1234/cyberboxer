"""
app.main
--------
Application entry point.

Creates and configures the FastAPI application:
* sets up logging before anything else runs,
* configures OpenAPI metadata (title, version, description) which powers the
  automatic Swagger UI at `/docs` and ReDoc at `/redoc`,
* mounts the feature routers (currently only `health`).

Run with:  uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import create_tables
from app.routes import health
from app.utils.logger import setup_logging

# Configure logging once, at import time, so every module that grabs a logger
# afterwards inherits the console + file handlers.
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Code before `yield` runs on start-up; code after runs on shutdown. This
    is the modern replacement for the deprecated `@app.on_event` hooks and is
    the natural place to add resource setup/teardown later.
    """
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # In development, ensure all tables exist. `create_tables` is idempotent
    # and never drops data. Disable via AUTO_CREATE_TABLES=false in production.
    if settings.AUTO_CREATE_TABLES:
        create_tables()
        logger.info("Database tables ensured (create_all).")

    yield
    logger.info("Shutting down %s", settings.APP_NAME)


# Instantiate the FastAPI app with rich OpenAPI metadata. FastAPI serves the
# interactive Swagger docs automatically at /docs and ReDoc at /redoc.
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register routers. Each domain gets mounted here; keeping this list short and
# explicit makes it obvious what the API exposes.
app.include_router(health.router)
