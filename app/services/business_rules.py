"""
app.services.business_rules
--------------------------
Pure business-logic layer for claims: validation, payout calculation and
fraud detection.

This module is intentionally free of any I/O — no database, no FastAPI, no
Pandas. Every function is deterministic and takes explicit inputs, so each
rule can be unit tested in isolation. Callers (e.g. the upload pipeline)
assemble a `ClaimContext` and call `evaluate_claim` (or the individual
functions) and act on the structured result.

Implemented rules:
  1. Loss amount cannot be negative.
  2. Loss date cannot be in the future.
  3. Claim date cannot be earlier than the policy issue date.
  4. Final payout cannot exceed the policy coverage limit.
  5. Final payout cannot be negative.
  6. Customers younger than 18 receive only 50% payout.
  7. Flood claims in California incur an additional 10% deductible.
  8. Customers with more than 5 claims are flagged as potential fraud.
(Rules 9 "no duplicate claims" and 10 "reject policies with unknown
 customers" are enforced structurally in the upload pipeline, not here.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

# --- Rule constants (single source of truth, easy to tune/test) ------------ #
MINOR_AGE_THRESHOLD = 18
MINOR_PAYOUT_FACTOR = Decimal("0.50")           # Rule 6: 50% payout for minors.
CALIFORNIA_STATE = "CA"
FLOOD_CAUSE = "flood"
CA_FLOOD_RETAINED_FACTOR = Decimal("0.90")      # Rule 7: keep 90% (10% deductible).
FRAUD_CLAIM_COUNT_THRESHOLD = 5                  # Rule 8: > 5 claims => fraud.

_ZERO = Decimal("0")
_CENTS = Decimal("0.01")


@dataclass
class ClaimContext:
    """All inputs a single claim needs for validation and payout.

    Grouping the inputs keeps function signatures small and makes the rules
    trivial to exercise from tests.
    """

    loss_amount: Decimal | None = None
    loss_date: date | None = None
    claim_date: date | None = None
    policy_issue_date: date | None = None
    coverage_limit: Decimal | None = None
    customer_age: int | None = None
    customer_state: str | None = None
    cause: str | None = None
    customer_claim_count: int = 0


@dataclass
class ClaimEvaluation:
    """Structured result of evaluating a claim."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    payout_amount: Decimal | None = None
    fraud_flag: bool = False

    def as_dict(self) -> dict:
        """Return a JSON-serialisable representation of the evaluation."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "payout_amount": self.payout_amount,
            "fraud_flag": self.fraud_flag,
        }


# --------------------------------------------------------------------------- #
# Validation (Rules 1-3).                                                      #
# --------------------------------------------------------------------------- #

def validate_claim(ctx: ClaimContext, reference_date: date | None = None) -> dict:
    """Validate a claim's core invariants.

    Returns a structured result::

        {"valid": bool, "errors": [str, ...]}

    `reference_date` overrides "today" (useful for deterministic tests).
    Rules whose inputs are missing are skipped rather than failing.
    """
    today = reference_date or date.today()
    errors: list[str] = []

    # Rule 1: loss amount cannot be negative.
    if ctx.loss_amount is not None and ctx.loss_amount < _ZERO:
        errors.append("Loss amount cannot be negative")

    # Rule 2: loss date cannot be in the future.
    if ctx.loss_date is not None and ctx.loss_date > today:
        errors.append("Loss date cannot be in the future")

    # Rule 3: claim date cannot precede the policy issue date.
    if (
        ctx.claim_date is not None
        and ctx.policy_issue_date is not None
        and ctx.claim_date < ctx.policy_issue_date
    ):
        errors.append("Claim date cannot be earlier than the policy issue date")

    return {"valid": not errors, "errors": errors}


# --------------------------------------------------------------------------- #
# Payout building blocks (Rules 4-7). Each is small and independently tested. #
# --------------------------------------------------------------------------- #

def apply_minor_rule(amount: Decimal, customer_age: int | None) -> Decimal:
    """Rule 6: customers younger than 18 receive only 50% of the payout."""
    if customer_age is not None and customer_age < MINOR_AGE_THRESHOLD:
        return amount * MINOR_PAYOUT_FACTOR
    return amount


def apply_california_flood_rule(
    amount: Decimal, customer_state: str | None, cause: str | None
) -> Decimal:
    """Rule 7: flood claims in California incur an extra 10% deductible."""
    is_california = (customer_state or "").strip().upper() == CALIFORNIA_STATE
    is_flood = (cause or "").strip().lower() == FLOOD_CAUSE
    if is_california and is_flood:
        return amount * CA_FLOOD_RETAINED_FACTOR
    return amount


def apply_coverage_limit(amount: Decimal, coverage_limit: Decimal | None) -> Decimal:
    """Rule 4: the payout can never exceed the policy coverage limit."""
    if coverage_limit is not None and amount > coverage_limit:
        return coverage_limit
    return amount


def _ensure_non_negative(amount: Decimal) -> Decimal:
    """Rule 5: the payout can never be negative."""
    return amount if amount > _ZERO else _ZERO


def _round_money(amount: Decimal) -> Decimal:
    """Round a monetary amount to 2 decimal places (banker-safe HALF_UP)."""
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


def calculate_payout(ctx: ClaimContext) -> Decimal:
    """Compute the final payout by applying the payout rules in order.

    Order: base loss -> minor rule -> CA flood deductible -> coverage cap
    -> non-negative floor -> round to cents. The order matters: percentage
    reductions apply to the loss first, and the coverage limit caps the result.
    """
    amount = ctx.loss_amount if ctx.loss_amount is not None else _ZERO
    amount = apply_minor_rule(amount, ctx.customer_age)
    amount = apply_california_flood_rule(amount, ctx.customer_state, ctx.cause)
    amount = apply_coverage_limit(amount, ctx.coverage_limit)
    amount = _ensure_non_negative(amount)
    return _round_money(amount)


# --------------------------------------------------------------------------- #
# Fraud detection (Rule 8).                                                    #
# --------------------------------------------------------------------------- #

def detect_potential_fraud(customer_claim_count: int) -> bool:
    """Rule 8: a customer with more than 5 claims is flagged as potential fraud."""
    return customer_claim_count > FRAUD_CLAIM_COUNT_THRESHOLD


# --------------------------------------------------------------------------- #
# Convenience aggregator used by the upload pipeline.                          #
# --------------------------------------------------------------------------- #

def evaluate_claim(ctx: ClaimContext, reference_date: date | None = None) -> ClaimEvaluation:
    """Validate a claim and, if valid, compute its payout and fraud flag.

    Invalid claims short-circuit: no payout is computed and the validation
    errors are returned so the caller can reject the row.
    """
    validation = validate_claim(ctx, reference_date)
    if not validation["valid"]:
        return ClaimEvaluation(valid=False, errors=validation["errors"])

    return ClaimEvaluation(
        valid=True,
        errors=[],
        payout_amount=calculate_payout(ctx),
        fraud_flag=detect_potential_fraud(ctx.customer_claim_count),
    )
