"""
app.routes.health
-----------------
Health-check endpoint.

Exposes `GET /health`, used by load balancers, container orchestrators
(Kubernetes liveness/readiness probes) and monitoring to confirm that the
service — and its database connection — are up.

It verifies real database connectivity by issuing a trivial `SELECT 1`
against PostgreSQL through a SQLAlchemy session.
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)

# Router for health-related endpoints. The `tags` value groups this route
# nicely in the Swagger UI.
router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service and database health check")
def health_check(db: Session = Depends(get_db)):
    """Return the service status and database connectivity.

    On success responds with HTTP 200:
        {"status": "healthy", "database": "connected"}

    If the database cannot be reached, responds with HTTP 503:
        {"status": "unhealthy", "database": "disconnected"}
    """
    try:
        # A minimal round-trip proves the connection pool can reach the DB.
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:  # noqa: BLE001 - we want to report any DB failure.
        logger.error("Health check failed: database unreachable: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"},
        )
