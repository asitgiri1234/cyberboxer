"""
app.schemas.report
------------------
Response models for the reporting endpoints (aggregate + raw SQL).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class StateReport(BaseModel):
    """Aggregated claim metrics for a single state."""

    state: str | None = None
    total_claims: int
    average_payout: Decimal
    maximum_payout: Decimal
    total_payout: Decimal

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": "CA",
                "total_claims": 5,
                "average_payout": "50200.00",
                "maximum_payout": "144000.00",
                "total_payout": "251000.00",
            }
        }
    }


class CityPayout(BaseModel):
    """Raw-SQL report row: a city ranked by total payout."""

    city: str | None = None
    total_claims: int
    total_payout: Decimal


class CausePayout(BaseModel):
    """Raw-SQL report row: average payout grouped by claim cause."""

    cause: str | None = None
    total_claims: int
    average_payout: Decimal
