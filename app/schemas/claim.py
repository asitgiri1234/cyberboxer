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

    model_config = {
        "json_schema_extra": {
            "example": {
                "claim_id": "CL002",
                "cause": "Flood",
                "loss_date": "2023-01-20",
                "claim_date": None,
                "loss_amount": "50000.00",
                "payout_amount": "45000.00",
                "fraud_flag": False,
                "status": None,
                "policy": {
                    "policy_id": "P1002",
                    "policy_type": None,
                    "coverage_limit": "150000.00",
                    "premium_amount": None,
                    "issue_date": "2021-07-15",
                    "expiry_date": None,
                    "status": None,
                },
                "customer": {
                    "customer_id": "C002",
                    "customer_name": "Alice Johnson",
                    "city": "San Francisco",
                    "state": "CA",
                    "email": None,
                },
            }
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_records": 4,
                "page": 1,
                "page_size": 3,
                "results": [
                    {
                        "claim_id": "CL013",
                        "cause": "Flood",
                        "loss_date": "2023-10-10",
                        "claim_date": None,
                        "loss_amount": "160000.00",
                        "payout_amount": "144000.00",
                        "fraud_flag": False,
                        "policy_id": "P1002",
                        "customer_id": "C002",
                        "customer_name": "Alice Johnson",
                        "city": "San Francisco",
                        "state": "CA",
                    }
                ],
            }
        }
    }
