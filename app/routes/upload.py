"""
app.routes.upload
----------------
CSV upload endpoint.

Thin HTTP layer: it validates that the three required files are present,
delegates ALL processing to `upload_service`, and maps service outcomes to
proper HTTP status codes with a consistent JSON shape.

    POST /upload  (multipart/form-data)
        customer -> customer.csv
        policy   -> policy.csv
        claims   -> claims.csv
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import upload_service
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
