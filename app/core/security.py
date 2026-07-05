"""
app.core.security
----------------
Optional API-key authentication.

When `settings.AUTH_ENABLED` is True, protected endpoints require a valid
`X-API-Key` request header matching `settings.API_KEY`. When it is False (the
default), the dependency is a no-op, so the API is trivial to evaluate and no
existing behaviour changes.

Using `APIKeyHeader` also registers the scheme in the OpenAPI spec, so Swagger
shows an "Authorize" button for the protected routes.
"""

from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

# `auto_error=False` lets us return our own consistent error envelope instead
# of FastAPI's default, and lets the header be optional when auth is disabled.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency enforcing the API key when authentication is enabled.

    * Auth disabled  -> always allowed.
    * Header missing  -> 401 Unauthorized.
    * Header wrong    -> 403 Forbidden.
    """
    if not settings.AUTH_ENABLED:
        return

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Unauthorized", "message": "Missing X-API-Key header"},
        )
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "message": "Invalid API key"},
        )
