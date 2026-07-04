"""
app.schemas.claim
----------------
Response models and query enums for the claims endpoints.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ClaimSortField(str, Enum):
    """Columns that `GET /claims` may be sorted by."""

    claim_date = "claim_date"
    loss_date = "loss_date"
    payout_amount = "payout_amount"
    loss_amount = "loss_amount"
    city = "city"
    state = "state"


class SortOrder(str, Enum):
    """Sort direction."""

    asc = "asc"
    desc = "desc"


class PolicyNested(BaseModel):
    """Policy fields embedded in a claim detail response."""

    policy_id: str
    policy_type: str | None = None
    coverage_limit: Decimal | None = None
    premium_amount: Decimal | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    status: str | None = None


class CustomerNested(BaseModel):
    """Customer fields embedded in a claim detail response."""

    customer_id: str
    customer_name: str
    city: str | None = None
    state: str | None = None
    email: str | None = None


class ClaimDetail(BaseModel):
    """Full claim detail with its owning policy and customer."""

    claim_id: str
    cause: str | None = None
    loss_date: date | None = None
    claim_date: date | None = None
    loss_amount: Decimal | None = None
    payout_amount: Decimal | None = None
    fraud_flag: bool
    status: str | None = None
    policy: PolicyNested
    customer: CustomerNested


class ClaimSummary(BaseModel):
    """Compact claim row returned by the paginated list endpoint."""

    claim_id: str
    cause: str | None = None
    loss_date: date | None = None
    claim_date: date | None = None
    loss_amount: Decimal | None = None
    payout_amount: Decimal | None = None
    fraud_flag: bool
    policy_id: str
    customer_id: str
    customer_name: str
    city: str | None = None
    state: str | None = None


class ClaimListResponse(BaseModel):
    """Paginated envelope for `GET /claims`."""

    total_records: int = Field(..., description="Total rows matching the filters (ignoring pagination)")
    page: int
    page_size: int
    results: list[ClaimSummary]
