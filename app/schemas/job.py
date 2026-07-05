"""
app.schemas.job
--------------
Response models for background upload jobs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobSubmitted(BaseModel):
    """Returned immediately (HTTP 202) when an async upload is accepted."""

    job_id: str
    status: str = Field(..., description='Initial job state, always "pending"')
    status_url: str = Field(..., description="Poll this URL for the job outcome")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "1f2a3b4c5d6e7f8091a2b3c4d5e6f708",
                "status": "pending",
                "status_url": "/upload/jobs/1f2a3b4c5d6e7f8091a2b3c4d5e6f708",
            }
        }
    }


class JobStatus(BaseModel):
    """Current state of a background upload job."""

    job_id: str
    status: str = Field(..., description='"pending" | "completed" | "failed"')
    submitted_at: str
    finished_at: str | None = None
    summary: dict[str, Any] | None = Field(
        None, description="Upload summary once the job completes"
    )
    error: str | None = Field(None, description="Failure reason if the job failed")
