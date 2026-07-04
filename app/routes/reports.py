"""
app.routes.reports
-----------------
Aggregate reporting endpoints.

* GET /reports/state             — ORM aggregate grouped by state
* GET /reports/top-cities        — RAW SQL: cities by total payout
* GET /reports/average-by-cause  — RAW SQL: average payout by claim cause
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import CausePayout, CityPayout, StateReport
from app.services import reports_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/state",
    response_model=list[StateReport],
    summary="Claim metrics grouped by state",
)
def state_report(db: Session = Depends(get_db)):
    """Return per-state totals (claims, average/maximum/total payout), sorted
    by total payout descending."""
    return reports_service.get_state_report(db)


@router.get(
    "/top-cities",
    response_model=list[CityPayout],
    summary="Top cities by total payout (raw SQL)",
)
def top_cities(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of cities to return (default 10)"),
):
    """RAW SQL report: cities ranked by total payout descending."""
    return reports_service.get_top_cities_by_payout(db, limit=limit)


@router.get(
    "/average-by-cause",
    response_model=list[CausePayout],
    summary="Average payout grouped by claim cause (raw SQL)",
)
def average_by_cause(db: Session = Depends(get_db)):
    """RAW SQL report: average payout per claim cause, sorted descending."""
    return reports_service.get_average_payout_by_cause(db)
