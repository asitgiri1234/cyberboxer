"""
app.core.exception_handlers
--------------------------
Centralised exception handling.

Every error leaving the API is converted to a single, consistent JSON shape::

    {"success": false, "error": "<ErrorType>", "message": "<human message>"}

(optionally with an extra `details`/`errors` field). This makes client-side
error handling predictable and prevents leaking stack traces or ORM internals.

Handlers are registered in one place via `register_exception_handlers(app)`.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.upload_service import CSVReadError, StructureValidationError

logger = logging.getLogger(__name__)


def _payload(error: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build the standard error response body."""
    body: dict[str, Any] = {"success": False, "error": error, "message": message}
    body.update(extra)
    return body


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalise HTTPExceptions (including those raised in routes).

    Supports both string details and the structured `{"error", "message"}`
    dicts used by the route handlers, preserving any extra keys (e.g. `errors`).
    """
    detail = exc.detail
    if isinstance(detail, dict):
        error = detail.get("error") or HTTPStatus(exc.status_code).phrase
        message = detail.get("message") or detail.get("detail") or error
        extra = {k: v for k, v in detail.items() if k not in {"error", "message"}}
    else:
        try:
            error = HTTPStatus(exc.status_code).phrase
        except ValueError:
            error = "HTTPException"
        message = detail if isinstance(detail, str) else str(detail)
        extra = {}

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(_payload(error, message, **extra)),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors (bad query/path/body) -> 422."""
    logger.warning("Validation failed: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            _payload("ValidationError", "Request validation failed", details=exc.errors())
        ),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity violations (unique/FK) -> 409."""
    logger.warning("Integrity error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=_payload("IntegrityError", "Database integrity constraint violated"),
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle any other database error -> 500 (full detail logged, not exposed)."""
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_payload("DatabaseError", "A database error occurred"),
    )


async def csv_read_error_handler(request: Request, exc: CSVReadError) -> JSONResponse:
    """Handle unparseable uploaded CSV files -> 400."""
    logger.warning("CSV read error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_payload("CSVReadError", str(exc)),
    )


async def structure_validation_error_handler(
    request: Request, exc: StructureValidationError
) -> JSONResponse:
    """Handle CSVs failing structural validation -> 400 (with per-file errors)."""
    logger.warning("Structure validation failed with %d issue(s)", len(exc.errors))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_payload("ValidationError", "CSV structure validation failed", errors=exc.errors),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler for unexpected errors -> 500 (details logged only)."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_payload("InternalServerError", "An unexpected error occurred"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # IntegrityError is a subclass of SQLAlchemyError; register both so the
    # more specific one wins for integrity violations.
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(CSVReadError, csv_read_error_handler)
    app.add_exception_handler(StructureValidationError, structure_validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
