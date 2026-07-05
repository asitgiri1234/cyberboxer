"""
app.main
--------
Application entry point.

Creates and configures the FastAPI application:
* sets up logging before anything else runs,
* configures OpenAPI metadata (title, version, description, tags) which powers
  the automatic Swagger UI at `/docs` and ReDoc at `/redoc`,
* installs middleware (request logging + gzip compression),
* registers centralised exception handlers,
* mounts the feature routers.

Run with:  uvicorn app.main:app --reload
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import RequestLoggingMiddleware
from app.routes import claims, customers, health, reports, upload
from app.utils.logger import setup_logging

# Configure logging once, at import time, so every module that grabs a logger
# afterwards inherits the console + file handlers.
logger = setup_logging()

# OpenAPI tag descriptions — these group and document endpoints in Swagger.
TAGS_METADATA = [
    {"name": "Health", "description": "Liveness/readiness and database connectivity checks."},
    {"name": "Upload", "description": "Bulk CSV ingestion of customers, policies and claims."},
    {"name": "Claims", "description": "Retrieve and search claims with filtering, sorting and pagination."},
    {"name": "Customers", "description": "Customer rankings and aggregates."},
    {"name": "Reports", "description": "Aggregate and raw-SQL reporting."},
]

DESCRIPTION = """
Production-quality REST API for managing insurance **claims**.

**Pipeline:** upload CSVs → clean (Pandas) → validate → apply business rules
(payout + fraud) → persist (PostgreSQL) → query via read APIs and reports.

* Interactive docs: `/docs` (Swagger) and `/redoc`.
* All errors share one JSON envelope: `{"success": false, "error": ..., "message": ...}`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Code before `yield` runs on start-up; code after runs on shutdown. This
    is the modern replacement for the deprecated `@app.on_event` hooks and is
    the natural place to add resource setup/teardown later.
    """
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    # The schema is managed by Alembic (`alembic upgrade head`); the app does
    # not create tables on startup. This keeps development and production
    # behaviour identical and safe.
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


# Instantiate the FastAPI app with rich OpenAPI metadata. FastAPI serves the
# interactive Swagger docs automatically at /docs and ReDoc at /redoc.
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Insurance Claims API"},
    license_info={"name": "MIT"},
)

# Record process start time so /health can report uptime.
app.state.started_at = time.time()

# --- Middleware (outermost is added last) --------------------------------- #
# GZip compresses larger responses; request logging times & logs every call.
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)

# --- Centralised exception handling --------------------------------------- #
register_exception_handlers(app)

# --- Routers -------------------------------------------------------------- #
# Register routers. Each domain gets mounted here; keeping this list short and
# explicit makes it obvious what the API exposes.
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(claims.router)
app.include_router(customers.router)
app.include_router(reports.router)
