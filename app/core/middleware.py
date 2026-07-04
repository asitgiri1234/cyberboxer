"""
app.core.middleware
------------------
Request-logging middleware.

Logs one line per request with the HTTP method, path, response status and
wall-clock duration, and adds an `X-Process-Time-ms` response header. It never
reads or logs request/response bodies, so uploaded file contents and sensitive
customer data are never written to the logs.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status and duration for every HTTP request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        method, path = request.method, request.url.path

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            # Body is never touched; only metadata is logged.
            logger.exception("%s %s failed after %.2f ms", method, path, elapsed_ms)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %d (%.2f ms)", method, path, response.status_code, elapsed_ms)
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
        return response
