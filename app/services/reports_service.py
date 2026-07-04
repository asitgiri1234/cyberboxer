"""
app.services.reports_service
--------------------------
Aggregate reporting.

* `get_state_report` uses the ORM aggregate API.
* `get_top_cities_by_payout` and `get_average_payout_by_cause` are the two
  required RAW SQL reports, written with SQLAlchemy `text()` and exposed here
  as service functions (routes never contain SQL).

All three join claim -> policy -> customer once and group in the database, so
there is no N+1 access and only the aggregated fields cross the wire.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Claim, Customer, Policy


def get_state_report(db: Session) -> list[dict[str, Any]]:
    """Aggregate claim metrics grouped by customer state (ORM aggregate).

    Sorted by total payout descending.
    """
    total_payout = func.coalesce(func.sum(Claim.payout_amount), 0).label("total_payout")

    stmt = (
        select(
            Customer.state.label("state"),
            func.count(Claim.id).label("total_claims"),
            func.round(func.coalesce(func.avg(Claim.payout_amount), 0), 2).label("average_payout"),
            func.coalesce(func.max(Claim.payout_amount), 0).label("maximum_payout"),
            total_payout,
        )
        .join(Policy, Policy.customer_id == Customer.customer_id)
        .join(Claim, Claim.policy_id == Policy.policy_id)
        .group_by(Customer.state)
        .order_by(total_payout.desc())
    )

    return [dict(row) for row in db.execute(stmt).mappings().all()]


# --------------------------------------------------------------------------- #
# RAW SQL reports (requirement: at least two, using text()).                   #
# --------------------------------------------------------------------------- #

# Report 1: top cities by total payout.
_TOP_CITIES_SQL = text(
    """
    SELECT cu.city                            AS city,
           COUNT(cl.id)                       AS total_claims,
           COALESCE(SUM(cl.payout_amount), 0) AS total_payout
    FROM claims cl
    JOIN policies p   ON cl.policy_id = p.policy_id
    JOIN customers cu ON p.customer_id = cu.customer_id
    WHERE cu.city IS NOT NULL
    GROUP BY cu.city
    ORDER BY total_payout DESC
    LIMIT :limit
    """
)

# Report 2: average payout grouped by claim cause.
_AVG_BY_CAUSE_SQL = text(
    """
    SELECT cl.cause                              AS cause,
           COUNT(cl.id)                          AS total_claims,
           ROUND(COALESCE(AVG(cl.payout_amount), 0), 2) AS average_payout
    FROM claims cl
    GROUP BY cl.cause
    ORDER BY average_payout DESC
    """
)


def get_top_cities_by_payout(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    """RAW SQL report: cities ranked by total payout (descending)."""
    rows = db.execute(_TOP_CITIES_SQL, {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


def get_average_payout_by_cause(db: Session) -> list[dict[str, Any]]:
    """RAW SQL report: average payout grouped by claim cause (descending)."""
    rows = db.execute(_AVG_BY_CAUSE_SQL).mappings().all()
    return [dict(row) for row in rows]
