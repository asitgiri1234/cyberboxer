"""
app.services.customers_service
-----------------------------
Read-side logic for customer rankings.

`get_top_customers` aggregates claims per customer in a single grouped query
(customer -> policy -> claim), avoiding N+1 access, and returns only the
fields the API exposes.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Claim, Customer, Policy


def get_top_customers(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    """Return customers ranked by total payout (descending).

    Each row includes customer_id, customer_name, total_claims, total_payout
    and a fraud_flag that is True if ANY of the customer's claims is flagged.
    """
    total_payout = func.coalesce(func.sum(Claim.payout_amount), 0).label("total_payout")

    stmt = (
        select(
            Customer.customer_id.label("customer_id"),
            func.concat(Customer.first_name, " ", Customer.last_name).label("customer_name"),
            func.count(Claim.id).label("total_claims"),
            total_payout,
            func.bool_or(Claim.fraud_flag).label("fraud_flag"),
        )
        # Join on the business identifiers used as foreign keys.
        .join(Policy, Policy.customer_id == Customer.customer_id)
        .join(Claim, Claim.policy_id == Policy.policy_id)
        .group_by(Customer.customer_id, Customer.first_name, Customer.last_name)
        .order_by(total_payout.desc())
        .limit(limit)
    )

    return [dict(row) for row in db.execute(stmt).mappings().all()]
