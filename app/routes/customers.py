"""
app.routes.customers
-------------------
Read endpoints for customers.

* GET /customers/top — customers ranked by total payout.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.customer import TopCustomer
from app.services import customers_service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "/top",
    response_model=list[TopCustomer],
    summary="Top customers ranked by total payout",
)
def top_customers(
    db: Session = Depends(get_db),
    n: int = Query(10, ge=1, le=100, description="Number of customers to return (default 10)"),
):
    """Return the `n` customers with the highest total payout, including their
    total number of claims and whether any of their claims is fraud-flagged."""
    return customers_service.get_top_customers(db, limit=n)
