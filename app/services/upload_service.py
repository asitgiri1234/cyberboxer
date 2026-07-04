"""
app.services.upload_service
--------------------------
Orchestrates the CSV upload pipeline end to end:

    read CSV (pandas) -> standardize columns -> clean -> validate structure
    -> validate relationships -> insert rows (SQLAlchemy ORM) -> summary

Design notes:
* Pandas is used ONLY for preprocessing; all persistence uses the ORM.
* Each row is inserted inside its own SAVEPOINT (`begin_nested`). A bad row is
  rolled back and recorded as "rejected" without aborting the whole upload.
* Entities are committed in dependency order (customers -> policies -> claims)
  so foreign keys to previously-inserted business ids are satisfied.
* Nothing sensitive (names, emails, addresses) is ever logged — only counts,
  row numbers and non-PII business ids/reasons.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import logging
import pandas as pd
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Claim, Customer, Policy
from app.services import csv_cleaner
from app.services.data_validator import (
    is_missing,
    make_error,
    source_row_number,
    validate_structure,
)

logger = logging.getLogger(__name__)


class StructureValidationError(Exception):
    """Raised when a file's structure is invalid (-> HTTP 400)."""

    def __init__(self, errors: list[dict[str, Any]]):
        self.errors = errors
        super().__init__("CSV structure validation failed")


class CSVReadError(Exception):
    """Raised when a file cannot be read/parsed as CSV (-> HTTP 400)."""


# --------------------------------------------------------------------------- #
# Per-entity configuration (column aliases, required columns, typed columns).  #
# Keeping this declarative avoids duplicated logic across the three entities.  #
# --------------------------------------------------------------------------- #

CUSTOMER_ALIASES: dict[str, str] = {}
POLICY_ALIASES: dict[str, str] = {"policy_issue_date": "issue_date"}
CLAIM_ALIASES: dict[str, str] = {}

CUSTOMER_REQUIRED = ["customer_id"]
POLICY_REQUIRED = ["policy_id", "customer_id"]
CLAIM_REQUIRED = ["claim_id", "policy_id"]

CUSTOMER_DATE_COLS = ["date_of_birth"]
CUSTOMER_NUM_COLS: list[str] = []
POLICY_DATE_COLS = ["issue_date", "expiry_date"]
POLICY_NUM_COLS = ["coverage_limit", "premium_amount"]
CLAIM_DATE_COLS = ["loss_date", "claim_date"]
CLAIM_NUM_COLS = ["loss_amount", "payout_amount"]


# --------------------------------------------------------------------------- #
# Low-level cell extractors: convert a pandas cell to a clean Python value.    #
# --------------------------------------------------------------------------- #

def _get(row: pd.Series, key: str) -> Any:
    """Return the cell value or None if absent/missing."""
    if key not in row:
        return None
    value = row[key]
    return None if is_missing(value) else value


def _as_str(row: pd.Series, key: str) -> str | None:
    value = _get(row, key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_decimal(row: pd.Series, key: str) -> Decimal | None:
    value = _get(row, key)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _as_date(row: pd.Series, key: str):
    value = _get(row, key)
    if value is None:
        return None
    try:
        return pd.Timestamp(value).date()
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------- #
# Row -> ORM model builders.                                                   #
# --------------------------------------------------------------------------- #

def _build_customer(row: pd.Series) -> Customer:
    """Map a cleaned customer row to a Customer model instance.

    Supports either explicit `first_name`/`last_name` columns or a single
    `name` column that is split on the first space.
    """
    first = _as_str(row, "first_name")
    last = _as_str(row, "last_name")
    if first is None:
        full = _as_str(row, "name")
        if full:
            parts = full.split()
            first = parts[0]
            last = " ".join(parts[1:]) if len(parts) > 1 else last

    return Customer(
        customer_id=_as_str(row, "customer_id"),
        first_name=first or "",
        last_name=last or "",
        date_of_birth=_as_date(row, "date_of_birth"),
        email=_as_str(row, "email"),
        phone=_as_str(row, "phone"),
        address=_as_str(row, "address"),
        city=_as_str(row, "city"),
        state=_as_str(row, "state"),
    )


def _build_policy(row: pd.Series) -> Policy:
    return Policy(
        policy_id=_as_str(row, "policy_id"),
        customer_id=_as_str(row, "customer_id"),
        policy_type=_as_str(row, "policy_type"),
        issue_date=_as_date(row, "issue_date"),
        expiry_date=_as_date(row, "expiry_date"),
        coverage_limit=_as_decimal(row, "coverage_limit"),
        premium_amount=_as_decimal(row, "premium_amount"),
        status=_as_str(row, "status"),
    )


def _build_claim(row: pd.Series) -> Claim:
    fraud = _as_str(row, "fraud_flag")
    fraud_flag = str(fraud).lower() in {"true", "1", "yes", "y"} if fraud else False
    return Claim(
        claim_id=_as_str(row, "claim_id"),
        policy_id=_as_str(row, "policy_id"),
        cause=_as_str(row, "cause"),
        loss_date=_as_date(row, "loss_date"),
        claim_date=_as_date(row, "claim_date"),
        loss_amount=_as_decimal(row, "loss_amount"),
        payout_amount=_as_decimal(row, "payout_amount"),
        fraud_flag=fraud_flag,
        status=_as_str(row, "status"),
    )


# --------------------------------------------------------------------------- #
# CSV reading + preparation.                                                   #
# --------------------------------------------------------------------------- #

def _prepare(
    upload: UploadFile,
    filename: str,
    aliases: dict[str, str],
    numeric_cols: list[str],
    date_cols: list[str],
) -> pd.DataFrame:
    """Read, standardise and clean a single uploaded CSV into a DataFrame."""
    try:
        upload.file.seek(0)
        # Read everything as strings so WE control missing-value handling.
        df = pd.read_csv(upload.file, dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001 - surface any parse failure as 400.
        raise CSVReadError(f"{filename}: unable to parse CSV ({exc})") from exc

    df = csv_cleaner.standardize_columns(df)
    # Apply entity-specific column aliases (e.g. policy_issue_date -> issue_date).
    if aliases:
        df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    df = csv_cleaner.clean_dataframe(df, numeric_columns=numeric_cols, date_columns=date_cols)
    return df


# --------------------------------------------------------------------------- #
# Generic per-entity insertion loop.                                          #
# --------------------------------------------------------------------------- #

def _insert_entity(
    db: Session,
    df: pd.DataFrame,
    *,
    filename: str,
    id_column: str,
    builder: Callable[[pd.Series], Any],
    existing_ids: set[str],
    errors: list[dict[str, Any]],
    parent_ids: set[str] | None = None,
    parent_column: str | None = None,
    parent_reason: str | None = None,
) -> dict[str, int]:
    """Insert all rows of one entity, rejecting bad rows individually.

    Returns a `{total, inserted, rejected}` counter dict and appends any row
    errors to `errors`. `existing_ids` is updated with successfully inserted
    business ids so later entities can validate their foreign keys against it.
    """
    total = len(df)
    inserted = 0
    seen_ids: set[str] = set()

    for index, row in df.iterrows():
        line = source_row_number(index)
        business_id = _as_str(row, id_column)

        # Required business identifier must be present.
        if business_id is None:
            errors.append(make_error(filename, line, f"Missing {id_column}"))
            continue

        # Reject duplicates (within this file or already in the database).
        if business_id in seen_ids or business_id in existing_ids:
            errors.append(make_error(filename, line, f"Duplicate {id_column}"))
            continue

        # Relationship (foreign key) validation, when applicable.
        if parent_ids is not None and parent_column is not None:
            parent_ref = _as_str(row, parent_column)
            if parent_ref is None or parent_ref not in parent_ids:
                errors.append(make_error(filename, line, parent_reason or "Parent not found"))
                continue

        # Persist the row inside its own savepoint so a failure is isolated.
        try:
            obj = builder(row)
            with db.begin_nested():
                db.add(obj)
                db.flush()
        except SQLAlchemyError as exc:
            # e.g. integrity/constraint violation not caught by pre-checks.
            reason = "Database constraint violation"
            logger.warning("%s row %d rejected: %s", filename, line, type(exc).__name__)
            errors.append(make_error(filename, line, reason))
            continue

        seen_ids.add(business_id)
        existing_ids.add(business_id)
        inserted += 1

    rejected = total - inserted
    logger.info(
        "%s processed: total=%d inserted=%d rejected=%d",
        filename, total, inserted, rejected,
    )
    return {"total": total, "inserted": inserted, "rejected": rejected}


def _load_existing_ids(db: Session, column) -> set[str]:
    """Fetch the set of already-present business ids for one column."""
    return {value for (value,) in db.execute(select(column)).all() if value is not None}


# --------------------------------------------------------------------------- #
# Public entry point.                                                          #
# --------------------------------------------------------------------------- #

def process_upload(
    customer_file: UploadFile,
    policy_file: UploadFile,
    claims_file: UploadFile,
    db: Session,
) -> dict[str, Any]:
    """Run the full upload pipeline and return a summary dict.

    Raises:
        CSVReadError: a file could not be parsed (-> HTTP 400).
        StructureValidationError: required columns/headers invalid (-> HTTP 400).
    """
    logger.info("Upload started")

    # --- Step 2-4: read + clean each file --------------------------------- #
    customers_df = _prepare(customer_file, "customer.csv", CUSTOMER_ALIASES, CUSTOMER_NUM_COLS, CUSTOMER_DATE_COLS)
    policies_df = _prepare(policy_file, "policy.csv", POLICY_ALIASES, POLICY_NUM_COLS, POLICY_DATE_COLS)
    claims_df = _prepare(claims_file, "claims.csv", CLAIM_ALIASES, CLAIM_NUM_COLS, CLAIM_DATE_COLS)

    # --- Step 5: structural validation (fail fast with 400) --------------- #
    structure_errors: list[dict[str, Any]] = []
    for df, required, fname in (
        (customers_df, CUSTOMER_REQUIRED, "customer.csv"),
        (policies_df, POLICY_REQUIRED, "policy.csv"),
        (claims_df, CLAIM_REQUIRED, "claims.csv"),
    ):
        for message in validate_structure(df, required):
            structure_errors.append(make_error(fname, 0, message))
    if structure_errors:
        logger.warning("Upload rejected: structural validation failed (%d issues)", len(structure_errors))
        raise StructureValidationError(structure_errors)

    errors: list[dict[str, Any]] = []

    # Existing business ids in the DB (for duplicate + FK checks across uploads).
    existing_customer_ids = _load_existing_ids(db, Customer.customer_id)
    existing_policy_ids = _load_existing_ids(db, Policy.policy_id)
    existing_claim_ids = _load_existing_ids(db, Claim.claim_id)

    try:
        # --- Step 6-7: insert in dependency order --------------------------- #
        customer_summary = _insert_entity(
            db, customers_df,
            filename="customer.csv", id_column="customer_id",
            builder=_build_customer, existing_ids=existing_customer_ids, errors=errors,
        )
        db.commit()  # commit customers so policies can reference them.

        policy_summary = _insert_entity(
            db, policies_df,
            filename="policy.csv", id_column="policy_id",
            builder=_build_policy, existing_ids=existing_policy_ids, errors=errors,
            parent_ids=existing_customer_ids, parent_column="customer_id",
            parent_reason="Customer not found",
        )
        db.commit()

        claim_summary = _insert_entity(
            db, claims_df,
            filename="claims.csv", id_column="claim_id",
            builder=_build_claim, existing_ids=existing_claim_ids, errors=errors,
            parent_ids=existing_policy_ids, parent_column="policy_id",
            parent_reason="Policy not found",
        )
        db.commit()
    except SQLAlchemyError:
        # Unexpected DB failure: roll back and let the route return HTTP 500.
        db.rollback()
        logger.exception("Unexpected database error during upload")
        raise

    logger.info(
        "Upload finished: customers=%d/%d policies=%d/%d claims=%d/%d errors=%d",
        customer_summary["inserted"], customer_summary["total"],
        policy_summary["inserted"], policy_summary["total"],
        claim_summary["inserted"], claim_summary["total"],
        len(errors),
    )

    return {
        "customers": customer_summary,
        "policies": policy_summary,
        "claims": claim_summary,
        "errors": errors,
    }
