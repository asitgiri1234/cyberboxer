"""
app.routes.upload
----------------
CSV upload endpoint.

Thin HTTP layer: it validates that the three required files are present,
delegates ALL processing to `upload_service`, and maps service outcomes to
proper HTTP status codes with a consistent JSON shape.

    POST /upload            (multipart/form-data)  synchronous import
    POST /upload/async      same files, processed as a background job
    GET  /upload/jobs/{id}  poll a background job's outcome

        customer -> customer.csv
        policy   -> policy.csv
        claims   -> claims.csv
"""

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core import jobs
from app.database import get_db
from app.schemas.job import JobStatus, JobSubmitted
from app.services import upload_jobs, upload_service
from app.services.upload_service import CSVReadError, StructureValidationError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    summary="Upload customer, policy and claim CSV files",
    description=(
        "Accepts three `multipart/form-data` CSV files and loads them into the "
        "database. Files are cleaned, validated (structure and relationships) "
        "and inserted in dependency order: customers → policies → claims. "
        "Individual bad rows are rejected and reported; they do not abort the "
        "whole upload. Returns a per-entity summary plus a list of row errors."
    ),
)
def upload_csv_files(
    customer: UploadFile = File(..., description="customer.csv — customer master data"),
    policy: UploadFile = File(..., description="policy.csv — policies referencing customers"),
    claims: UploadFile = File(..., description="claims.csv — claims referencing policies"),
    db: Session = Depends(get_db),
):
    """Handle the upload request and return the processing summary.

    Status codes:
      * 200 — processed (summary may still contain rejected rows/errors)
      * 400 — a file is unreadable or fails structural validation
      * 422 — a required file is missing (enforced by FastAPI)
      * 500 — unexpected server/database error
    """
    try:
        summary = upload_service.process_upload(customer, policy, claims, db)
        return summary

    except CSVReadError as exc:
        # Unparseable CSV -> client error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "CSV parse error", "message": str(exc)},
        )

    except StructureValidationError as exc:
        # Missing required columns / duplicate headers -> client error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Structure validation failed", "errors": exc.errors},
        )

    except Exception:  # noqa: BLE001 - last-resort guard; details are logged.
        logger.exception("Unexpected error while processing upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error while processing upload"},
        )


@router.post(
    "/upload/async",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobSubmitted,
    summary="Upload the three CSV files as a background job",
    description=(
        "Accepts the same three `multipart/form-data` CSV files as `POST /upload` "
        "but processes them **in the background**: the request returns immediately "
        "with HTTP 202 and a `job_id`. Poll `GET /upload/jobs/{job_id}` for the "
        "outcome. Useful for large files where a synchronous import would block."
    ),
)
async def upload_csv_files_async(
    background_tasks: BackgroundTasks,
    customer: UploadFile = File(..., description="customer.csv — customer master data"),
    policy: UploadFile = File(..., description="policy.csv — policies referencing customers"),
    claims: UploadFile = File(..., description="claims.csv — claims referencing policies"),
):
    """Accept the upload, register a job and schedule background processing.

    The file contents are read NOW because the temporary upload objects are
    closed once this response is sent; the background job then runs the exact
    same pipeline as the synchronous endpoint with its own DB session.
    """
    customer_bytes = await customer.read()
    policy_bytes = await policy.read()
    claims_bytes = await claims.read()

    job_id = jobs.create()
    background_tasks.add_task(
        upload_jobs.run_upload_job, job_id, customer_bytes, policy_bytes, claims_bytes
    )
    logger.info("Accepted async upload as job %s", job_id)
    return {
        "job_id": job_id,
        "status": "pending",
        "status_url": f"/upload/jobs/{job_id}",
    }


@router.get(
    "/upload/jobs/{job_id}",
    response_model=JobStatus,
    summary="Get the status of a background upload job",
)
def get_upload_job(job_id: str):
    """Return the job's state: pending, completed (with summary) or failed.

    Responds 404 if the job id is unknown.
    """
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Not found", "message": f"Upload job '{job_id}' does not exist"},
        )
    return job
