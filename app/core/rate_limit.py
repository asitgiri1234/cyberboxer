"""
app.core.rate_limit
------------------
Optional per-client rate limiting (via slowapi).

A single `Limiter` keyed on the client IP applies `settings.RATE_LIMIT` as a
global default limit. It is enabled only when `settings.RATE_LIMIT_ENABLED` is
True (the default is False), so evaluation and test runs are never throttled.

When a client exceeds the limit, `rate_limit_exceeded_handler` returns the same
consistent error envelope used everywhere else, with HTTP 429.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings

# Global limiter. `enabled` gates enforcement; `default_limits` applies the
# configured limit to every route.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
    enabled=settings.RATE_LIMIT_ENABLED,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a consistent 429 response when the rate limit is exceeded.

    Deliberately synchronous: `SlowAPIMiddleware` runs handlers synchronously
    and falls back to its own default response for `async def` handlers.
    """
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "RateLimitExceeded",
            "message": "Rate limit exceeded. Please slow down and retry.",
        },
    )
