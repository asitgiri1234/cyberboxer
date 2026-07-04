"""
app.schemas.customer
-------------------
Response models for the customers endpoints.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class TopCustomer(BaseModel):
    """A customer ranked by total payout across all their claims."""

    customer_id: str
    customer_name: str
    total_claims: int
    total_payout: Decimal
    fraud_flag: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "C002",
                "customer_name": "Alice Johnson",
                "total_claims": 4,
                "total_payout": "246000.00",
                "fraud_flag": False,
            }
        }
    }
