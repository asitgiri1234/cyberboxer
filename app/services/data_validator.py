"""
app.services.data_validator
--------------------------
Validation helpers for the upload pipeline.

Two layers of validation:

* `validate_structure` — DataFrame-level checks that must pass before any row
  is processed (required columns present, no duplicate headers). A failure
  here means the whole file is unusable -> the caller returns HTTP 400.

* Row-level helpers (`is_missing`, `make_error`, `source_row_number`) — used
  while iterating rows so a single bad row can be rejected without aborting
  the entire upload.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


def validate_structure(
    df: pd.DataFrame, required_columns: Iterable[str]
) -> list[str]:
    """Return a list of structural error messages (empty list == valid).

    Checks:
      * no duplicate column names, and
      * every required column is present.
    """
    errors: list[str] = []

    columns = list(df.columns)
    duplicates = sorted({c for c in columns if columns.count(c) > 1})
    if duplicates:
        errors.append(f"Duplicate column names: {duplicates}")

    missing = [c for c in required_columns if c not in columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")

    return errors


def is_missing(value: Any) -> bool:
    """True if a cell value should be treated as absent (None / NaN / NaT)."""
    if value is None:
        return True
    # pd.isna handles NaN, NaT and pd.NA; guard against array-like inputs.
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def source_row_number(index: Any) -> int:
    """Translate a 0-based DataFrame index into a human CSV line number.

    Row 0 in the DataFrame corresponds to the second line of the file
    (line 1 is the header), so we add 2.
    """
    return int(index) + 2


def make_error(file: str, row: int, reason: str) -> dict[str, Any]:
    """Build a consistent error record for the upload summary."""
    return {"file": file, "row": row, "reason": reason}
