"""
app.schemas.common
-----------------
Shared response schemas.

`ErrorResponse` documents the consistent error envelope produced by the
centralised exception handlers, so it shows up in the Swagger docs for
error status codes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Machine-readable error type")
    message: str = Field(..., description="Human-readable error message")
    details: Any | None = Field(None, description="Optional structured error details")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error": "Not found",
                "message": "Claim 'CL999' does not exist",
            }
        }
    }
