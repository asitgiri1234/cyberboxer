"""Unit tests for the pure business-rules layer (no database)."""

from datetime import date
from decimal import Decimal

import pytest

from app.services import business_rules as br
from app.services.business_rules import ClaimContext


# --- Validation (Rules 1-3) ------------------------------------------------ #

def test_negative_loss_is_invalid():
    result = br.validate_claim(ClaimContext(loss_amount=Decimal("-1")))
    assert result == {"valid": False, "errors": ["Loss amount cannot be negative"]}


def test_future_loss_date_is_invalid():
    result = br.validate_claim(
        ClaimContext(loss_date=date(2999, 1, 1)), reference_date=date(2026, 7, 4)
    )
    assert not result["valid"]
    assert "future" in result["errors"][0]


def test_claim_date_before_policy_issue_is_invalid():
    result = br.validate_claim(
        ClaimContext(claim_date=date(2020, 1, 1), policy_issue_date=date(2021, 1, 1))
    )
    assert not result["valid"]


def test_valid_claim_passes():
    result = br.validate_claim(
        ClaimContext(loss_amount=Decimal("100"), loss_date=date(2023, 1, 1)),
        reference_date=date(2026, 7, 4),
    )
    assert result == {"valid": True, "errors": []}


# --- Payout building blocks (Rules 4-7) ----------------------------------- #

def test_minor_rule_halves_payout():
    assert br.apply_minor_rule(Decimal("1000"), 16) == Decimal("500.00")


def test_adult_payout_unchanged():
    assert br.apply_minor_rule(Decimal("1000"), 40) == Decimal("1000")


def test_california_flood_applies_10_percent_deductible():
    assert br.apply_california_flood_rule(Decimal("1000"), "CA", "Flood") == Decimal("900.0")


@pytest.mark.parametrize("state,cause", [("CA", "Fire"), ("TX", "Flood"), (None, "Flood")])
def test_california_flood_rule_not_applied(state, cause):
    assert br.apply_california_flood_rule(Decimal("1000"), state, cause) == Decimal("1000")


def test_coverage_limit_caps_payout():
    assert br.apply_coverage_limit(Decimal("80000"), Decimal("50000")) == Decimal("50000")


# --- Fraud (Rule 8) -------------------------------------------------------- #

@pytest.mark.parametrize("count,expected", [(6, True), (5, False), (0, False)])
def test_detect_potential_fraud(count, expected):
    assert br.detect_potential_fraud(count) is expected


# --- End-to-end payout composition ---------------------------------------- #

def test_calculate_payout_minor_flood_capped():
    # 200000 * 0.5 (minor) = 100000 * 0.9 (CA flood) = 90000 -> capped at 50000.
    ctx = ClaimContext(
        loss_amount=Decimal("200000"),
        customer_age=16,
        customer_state="CA",
        cause="Flood",
        coverage_limit=Decimal("50000"),
    )
    assert br.calculate_payout(ctx) == Decimal("50000.00")


def test_evaluate_claim_returns_payout_and_fraud():
    ctx = ClaimContext(
        loss_amount=Decimal("50000"),
        customer_state="CA",
        cause="Flood",
        coverage_limit=Decimal("150000"),
        customer_claim_count=7,
    )
    evaluation = br.evaluate_claim(ctx)
    assert evaluation.valid is True
    assert evaluation.payout_amount == Decimal("45000.00")
    assert evaluation.fraud_flag is True


def test_evaluate_claim_short_circuits_on_invalid():
    evaluation = br.evaluate_claim(ClaimContext(loss_amount=Decimal("-5")))
    assert evaluation.valid is False
    assert evaluation.payout_amount is None
