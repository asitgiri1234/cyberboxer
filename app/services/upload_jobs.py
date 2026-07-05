"""
app.services.upload_jobs
-----------------------
Background execution of the CSV upload pipeline.

The async upload route reads the uploaded files into memory (the temporary
`UploadFile` objects are closed once the HTTP response is sent), registers a
job, and schedules `run_upload_job`. The job opens its OWN database session
(request-scoped sessions die with the request) and reuses the exact same
`process_upload` pipeline as the synchronous endpoint — no logic is duplicated.
"""

from __future__ import annotations

import io
import logging

from app.core import jobs
from app.database import SessionLocal
from app.services import upload_service

logger = logging.getLogger(__name__)


class MemoryUpload:
    """Tiny in-memory stand-in for FastAPI's UploadFile.

    `process_upload` only touches `.file` (seek + read), so wrapping the raw
    bytes in a BytesIO is all the pipeline needs.
    """

    def __init__(self, data: bytes) -> None:
        self.file = io.BytesIO(data)


def run_upload_job(
    job_id: str,
    customer_bytes: bytes,
    policy_bytes: bytes,
    claims_bytes: bytes,
) -> None:
    """Execute the full upload pipeline for a background job.

    Runs after the HTTP response has been sent; outcome (summary or error) is
    recorded on the job so clients can poll `GET /upload/jobs/{job_id}`.
    """
    logger.info("Background upload job %s started", job_id)
    db = SessionLocal()
    try:
        summary = upload_service.process_upload(
            MemoryUpload(customer_bytes),  # type: ignore[arg-type]
            MemoryUpload(policy_bytes),    # type: ignore[arg-type]
            MemoryUpload(claims_bytes),    # type: ignore[arg-type]
            db,
        )
        jobs.complete(job_id, summary)
        logger.info("Background upload job %s completed", job_id)
    except Exception as exc:  # noqa: BLE001 - job must record any failure.
        db.rollback()
        jobs.fail(job_id, f"{type(exc).__name__}: {exc}")
        logger.exception("Background upload job %s failed", job_id)
    finally:
        db.close()
