"""
app.services.claims_service
--------------------------
Read-side logic for claims: single-claim detail and a dynamically filtered,
sorted and paginated claim list.

Performance notes:
* Detail uses `joinedload` so the claim, its policy and its customer are
  fetched in a single query (no N+1).
* The list joins claim -> policy -> customer once and uses `contains_eager`
  to reuse that join for the loaded relationships.
* Filters are compiled into a single list of conditions, shared by both the
  count query and the data query, so there is no duplicated query code.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.models import Claim, Customer, Policy
from app.schemas.claim import ClaimSortField, SortOrder

# Map an API sort field to the actual ORM column (avoids exposing internals
# and prevents arbitrary/unsafe sort columns).
_SORT_COLUMNS = {
    ClaimSortField.claim_date: Claim.claim_date,
    ClaimSortField.loss_date: Claim.loss_date,
    ClaimSortField.payout_amount: Claim.payout_amount,
    ClaimSortField.loss_amount: Claim.loss_amount,
    ClaimSortField.city: Customer.city,
    ClaimSortField.state: Customer.state,
}


def _full_name(customer: Customer) -> str:
    """Join first/last name into a single display name."""
    return f"{customer.first_name} {customer.last_name}".strip()


def get_claim_detail(db: Session, claim_id: str) -> dict[str, Any] | None:
    """Return a claim with its policy and customer, or None if not found.

    A single query eager-loads policy and customer to avoid N+1 access.
    """
    stmt = (
        select(Claim)
        .where(Claim.claim_id == claim_id)
        .options(joinedload(Claim.policy).joinedload(Policy.customer))
    )
    claim = db.execute(stmt).unique().scalar_one_or_none()
    if claim is None:
        return None

    policy = claim.policy
    customer = policy.customer if policy else None

    return {
        "claim_id": claim.claim_id,
        "cause": claim.cause,
        "loss_date": claim.loss_date,
        "claim_date": claim.claim_date,
        "loss_amount": claim.loss_amount,
        "payout_amount": claim.payout_amount,
        "fraud_flag": claim.fraud_flag,
        "status": claim.status,
        "policy": {
            "policy_id": policy.policy_id,
            "policy_type": policy.policy_type,
            "coverage_limit": policy.coverage_limit,
            "premium_amount": policy.premium_amount,
            "issue_date": policy.issue_date,
            "expiry_date": policy.expiry_date,
            "status": policy.status,
        },
        "customer": {
            "customer_id": customer.customer_id,
            "customer_name": _full_name(customer),
            "city": customer.city,
            "state": customer.state,
            "email": customer.email,
        },
    }


def _build_conditions(
    *,
    city: str | None,
    state: str | None,
    cause: str | None,
    start_date: date | None,
    end_date: date | None,
    min_payout: Decimal | None,
    max_payout: Decimal | None,
) -> list:
    """Translate optional filters into a list of SQLAlchemy conditions.

    Only provided filters produce a condition, so the query is built
    dynamically. The date range applies to the claim's `loss_date`.
    """
    conditions: list = []
    if city is not None:
        conditions.append(func.lower(Customer.city) == city.strip().lower())
    if state is not None:
        conditions.append(func.lower(Customer.state) == state.strip().lower())
    if cause is not None:
        conditions.append(func.lower(Claim.cause) == cause.strip().lower())
    if start_date is not None:
        conditions.append(Claim.loss_date >= start_date)
    if end_date is not None:
        conditions.append(Claim.loss_date <= end_date)
    if min_payout is not None:
        conditions.append(Claim.payout_amount >= min_payout)
    if max_payout is not None:
        conditions.append(Claim.payout_amount <= max_payout)
    return conditions


def _to_summary(claim: Claim) -> dict[str, Any]:
    """Map a loaded Claim (with policy+customer) to a compact summary dict."""
    customer = claim.policy.customer
    return {
        "claim_id": claim.claim_id,
        "cause": claim.cause,
        "loss_date": claim.loss_date,
        "claim_date": claim.claim_date,
        "loss_amount": claim.loss_amount,
        "payout_amount": claim.payout_amount,
        "fraud_flag": claim.fraud_flag,
        "policy_id": claim.policy_id,
        "customer_id": customer.customer_id,
        "customer_name": _full_name(customer),
        "city": customer.city,
        "state": customer.state,
    }


def list_claims(
    db: Session,
    *,
    city: str | None = None,
    state: str | None = None,
    cause: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    min_payout: Decimal | None = None,
    max_payout: Decimal | None = None,
    sort_by: ClaimSortField = ClaimSortField.claim_date,
    order: SortOrder = SortOrder.desc,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Return a paginated, filtered and sorted list of claims.

    Returns a dict with `total_records`, `page`, `page_size` and `results`.
    """
    conditions = _build_conditions(
        city=city, state=state, cause=cause,
        start_date=start_date, end_date=end_date,
        min_payout=min_payout, max_payout=max_payout,
    )

    # Single join reused for filtering, counting, sorting and eager loading.
    base = select(Claim).join(Claim.policy).join(Policy.customer).where(*conditions)

    # total_records: count the filtered rows (before pagination).
    total_records = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    # Resolve the sort column + direction.
    sort_column = _SORT_COLUMNS[sort_by]
    order_expr = sort_column.desc() if order == SortOrder.desc else sort_column.asc()

    data_stmt = (
        base.options(contains_eager(Claim.policy).contains_eager(Policy.customer))
        # Secondary key keeps ordering deterministic when the sort column ties.
        .order_by(order_expr, Claim.claim_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    claims = db.execute(data_stmt).unique().scalars().all()

    return {
        "total_records": total_records,
        "page": page,
        "page_size": page_size,
        "results": [_to_summary(c) for c in claims],
    }
