"""
app.routes.health
-----------------
Health-check endpoint.

Exposes `GET /health`, used by load balancers, container orchestrators
(Kubernetes liveness/readiness probes) and monitoring to confirm that the
service — and its database connection — are up.

It verifies real database connectivity by issuing a trivial `SELECT 1`
against PostgreSQL through a SQLAlchemy session, and reports process uptime.
"""

import logging
import time

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)

# Router for health-related endpoints. The `tags` value groups this route
# nicely in the Swagger UI.
router = APIRouter(tags=["Health"])


def _format_uptime(seconds: float) -> str:
    """Render an elapsed number of seconds as a compact string, e.g. '2h 13m'."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


@router.get("/health", summary="Service and database health check")
def health_check(request: Request, db: Session = Depends(get_db)):
    """Return the service status, database connectivity and uptime.

    On success responds with HTTP 200:
        {"status": "healthy", "database": "connected", "uptime": "2h 13m"}

    If the database cannot be reached, responds with HTTP 503:
        {"status": "unhealthy", "database": "disconnected", "uptime": "..."}
    """
    # `started_at` is set on the app in main.py at startup.
    started_at = getattr(request.app.state, "started_at", time.time())
    uptime = _format_uptime(time.time() - started_at)

    try:
        # A minimal round-trip proves the connection pool can reach the DB.
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "uptime": uptime}
    except Exception as exc:  # noqa: BLE001 - we want to report any DB failure.
        logger.error("Health check failed: database unreachable: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "uptime": uptime},
        )
