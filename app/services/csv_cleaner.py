"""
app.services.csv_cleaner
-----------------------
Pandas-based preprocessing for uploaded CSVs.

Pure data-wrangling only — no database access and no business rules. Each
function is deterministic and easy to unit test. The two entry points are:

* `standardize_columns` — normalise header names to lowercase snake_case.
* `clean_dataframe`     — trim, normalise missing values, de-duplicate, and
                          coerce numeric/date columns while preserving the
                          original row index for error reporting.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

# Tokens that should be treated as "missing" regardless of case/whitespace.
_MISSING_TOKEN_RE = r"(?i)^\s*(na|n/a|null|none|nan|-)?\s*$"


def to_snake_case(name: str) -> str:
    """Convert an arbitrary column header to `lower_snake_case`.

    Examples:
        "Customer ID"  -> "customer_id"
        "CustomerId"   -> "customer_id"
        "  customer_id" -> "customer_id"
    """
    text = str(name).strip()
    # Insert underscore at camelCase / PascalCase boundaries (fooBar -> foo_Bar).
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    # Any run of spaces, hyphens or dots becomes a single underscore.
    text = re.sub(r"[\s\-.]+", "_", text)
    # Drop anything that is not alphanumeric or underscore.
    text = re.sub(r"[^0-9a-zA-Z_]", "", text)
    # Collapse repeated underscores and trim leading/trailing ones.
    text = re.sub(r"_+", "_", text).strip("_")
    return text.lower()


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with headers normalised to snake_case."""
    return df.rename(columns={col: to_snake_case(col) for col in df.columns})


def clean_dataframe(
    df: pd.DataFrame,
    numeric_columns: Iterable[str] = (),
    date_columns: Iterable[str] = (),
) -> pd.DataFrame:
    """Clean a DataFrame in place-safe fashion and return the result.

    Steps (in order):
      1. Trim whitespace on all string cells.
      2. Replace empty strings / common missing tokens with `pd.NA`.
      3. Drop fully-duplicated rows (keeping the first occurrence).
      4. Coerce `numeric_columns` to numbers (unparseable -> NA).
      5. Coerce `date_columns` to datetimes (unparseable -> NaT).

    The DataFrame index is intentionally NOT reset, so each surviving row keeps
    its original position — this lets the caller report the true source row
    number when a row is later rejected.
    """
    df = df.copy()

    # 1. Trim whitespace on object (string) columns only.
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)

    # 2. Normalise empty strings and missing-value tokens to NA.
    df = df.replace(to_replace=_MISSING_TOKEN_RE, value=pd.NA, regex=True)

    # 3. Remove exact duplicate rows but preserve the original index.
    df = df.drop_duplicates(keep="first")

    # 4. Numeric coercion (bad values become NA rather than raising).
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. Date coercion (bad/blank values become NaT).
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df
