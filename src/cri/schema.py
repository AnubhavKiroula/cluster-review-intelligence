"""Review schema and validation.

See docs/data_schema.md for the human-readable contract. Reviewer identity
fields are intentionally absent and are stripped at load time.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["property_id", "platform", "date", "rating", "text", "language_hint"]

# Any of these (case-insensitive) are dropped at ingestion to avoid storing PII.
IDENTITY_COLUMNS = {
    "reviewer_name", "reviewer_id", "reviewer", "user", "username", "user_id",
    "author", "name", "email", "phone", "profile_url",
}

RATING_MIN, RATING_MAX = 1, 5


class SchemaError(ValueError):
    """Raised when input reviews do not meet the schema contract."""


def drop_identity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove any reviewer-identity columns (PII) if present."""
    to_drop = [c for c in df.columns if c.strip().lower() in IDENTITY_COLUMNS]
    return df.drop(columns=to_drop)


def validate_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and lightly coerce a reviews DataFrame.

    Raises SchemaError with an actionable message on the first problem found.
    Returns a cleaned copy with ``date`` parsed to datetime.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(
            f"Missing required column(s): {missing}. "
            f"Expected: {REQUIRED_COLUMNS}"
        )

    df = df.copy()

    try:
        df["date"] = pd.to_datetime(df["date"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"Column 'date' is not parseable as a date: {exc}") from exc

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if df["rating"].isna().any():
        raise SchemaError("Column 'rating' contains non-numeric values.")
    out_of_range = ~df["rating"].between(RATING_MIN, RATING_MAX)
    if out_of_range.any():
        bad = df.loc[out_of_range, "rating"].unique().tolist()
        raise SchemaError(
            f"'rating' must be within [{RATING_MIN}, {RATING_MAX}]; found {bad}."
        )

    df["text"] = df["text"].astype(str)
    empty = df["text"].str.strip() == ""
    if empty.any():
        raise SchemaError(f"{int(empty.sum())} review(s) have empty 'text'.")

    return df
