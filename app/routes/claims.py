"""
app.routes.claims
----------------
Read endpoints for claims:

* GET /claims/{claim_id} — full claim detail (policy + customer + payout + fraud)
* GET /claims           — filtered, sorted, paginated list

Handlers stay thin: they validate inputs, delegate to `claims_service`, and
map "not found" to HTTP 404. All query construction lives in the service.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.claim import (
    ClaimDetail,
    ClaimListResponse,
    ClaimSortField,
    SortOrder,
)
from app.schemas.common import ErrorResponse
from app.services import claims_service

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.get(
    "/{claim_id}",
    response_model=ClaimDetail,
    summary="Get a single claim with its policy and customer",
    responses={404: {"model": ErrorResponse, "description": "Claim not found"}},
)
def get_claim(
    claim_id: str = Path(..., description="Business identifier of the claim, e.g. 'CL001'"),
    db: Session = Depends(get_db),
):
    """Return one claim including its owning policy, customer, calculated
    payout and fraud flag. Responds 404 if the claim does not exist."""
    claim = claims_service.get_claim_detail(db, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Not found", "message": f"Claim '{claim_id}' does not exist"},
        )
    return claim


@router.get(
    "",
    response_model=ClaimListResponse,
    summary="List claims with filtering, sorting and pagination",
    responses={400: {"model": ErrorResponse, "description": "Invalid filter range"}},
)
def list_claims(
    db: Session = Depends(get_db),
    city: str | None = Query(None, description="Filter by customer city (case-insensitive)"),
    state: str | None = Query(None, description="Filter by customer state (case-insensitive)"),
    cause: str | None = Query(None, description="Filter by claim cause, e.g. 'Flood' (case-insensitive)"),
    start_date: date | None = Query(None, description="Only claims with loss_date >= this ISO date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Only claims with loss_date <= this ISO date (YYYY-MM-DD)"),
    min_payout: Decimal | None = Query(None, description="Minimum payout_amount (inclusive)"),
    max_payout: Decimal | None = Query(None, description="Maximum payout_amount (inclusive)"),
    sort_by: ClaimSortField = Query(ClaimSortField.claim_date, description="Field to sort by"),
    order: SortOrder = Query(SortOrder.desc, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=200, description="Rows per page (1-200)"),
):
    """Return a paginated list of claims. All filters are optional and applied
    dynamically; results include the customer city/state for context."""
    # Cross-field validation (single-field bounds are enforced by Query()).
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid range", "message": "start_date cannot be after end_date"},
        )
    if min_payout is not None and max_payout is not None and min_payout > max_payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid range", "message": "min_payout cannot be greater than max_payout"},
        )

    return claims_service.list_claims(
        db,
        city=city, state=state, cause=cause,
        start_date=start_date, end_date=end_date,
        min_payout=min_payout, max_payout=max_payout,
        sort_by=sort_by, order=order,
        page=page, page_size=page_size,
    )
