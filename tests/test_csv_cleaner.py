"""Unit tests for CSV preprocessing and structural validation (no database)."""

import pandas as pd

from app.services import csv_cleaner
from app.services.data_validator import (
    is_missing,
    source_row_number,
    validate_structure,
)


# --- Column standardisation ------------------------------------------------ #

def test_to_snake_case_variants():
    assert csv_cleaner.to_snake_case("Customer ID") == "customer_id"
    assert csv_cleaner.to_snake_case("CustomerId") == "customer_id"
    assert csv_cleaner.to_snake_case("  customer_id ") == "customer_id"


def test_standardize_columns():
    df = pd.DataFrame(columns=["Policy ID", "Coverage-Limit"])
    out = csv_cleaner.standardize_columns(df)
    assert list(out.columns) == ["policy_id", "coverage_limit"]


# --- Cleaning -------------------------------------------------------------- #

def test_clean_dataframe_trims_and_normalises_missing():
    df = pd.DataFrame({"a": ["  x ", "", "NA"], "b": ["1", "2", "3"]})
    out = csv_cleaner.clean_dataframe(df)
    assert out.loc[0, "a"] == "x"
    assert pd.isna(out.loc[1, "a"])   # empty string -> NA
    assert pd.isna(out.loc[2, "a"])   # "NA" token -> NA


def test_clean_dataframe_drops_exact_duplicates_and_preserves_index():
    df = pd.DataFrame({"id": ["A", "B", "A"], "v": ["1", "2", "1"]})
    out = csv_cleaner.clean_dataframe(df)
    assert len(out) == 2
    # Original indices are preserved (0 and 1 kept, duplicate row 2 dropped).
    assert list(out.index) == [0, 1]


def test_clean_dataframe_coerces_numeric_and_dates():
    df = pd.DataFrame({"amount": ["100", "bad"], "d": ["2023-01-01", "nope"]})
    out = csv_cleaner.clean_dataframe(df, numeric_columns=["amount"], date_columns=["d"])
    assert out.loc[0, "amount"] == 100
    assert pd.isna(out.loc[1, "amount"])
    assert out.loc[0, "d"] == pd.Timestamp("2023-01-01")
    assert pd.isna(out.loc[1, "d"])


# --- Structural validation ------------------------------------------------- #

def test_validate_structure_reports_missing_columns():
    df = pd.DataFrame(columns=["claim_id"])
    errors = validate_structure(df, required_columns=["claim_id", "policy_id"])
    assert any("policy_id" in e for e in errors)


def test_validate_structure_passes_when_all_present():
    df = pd.DataFrame(columns=["claim_id", "policy_id"])
    assert validate_structure(df, required_columns=["claim_id", "policy_id"]) == []


def test_is_missing_and_row_number_helpers():
    assert is_missing(None) is True
    assert is_missing(pd.NA) is True
    assert is_missing("x") is False
    # DataFrame row 0 == CSV line 2 (header is line 1).
    assert source_row_number(0) == 2
