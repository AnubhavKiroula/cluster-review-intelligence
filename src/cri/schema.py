"""Review schema and validation.

See docs/data_schema.md for the human-readable contract. Reviewer identity
fields are intentionally absent and are stripped at load time.
"""

from __future__ import annotations

import warnings

import pandas as pd

REQUIRED_COLUMNS = ["property_id", "platform", "date", "rating", "text", "language_hint"]

# Any of these (case-insensitive) are dropped at ingestion to avoid storing PII.
IDENTITY_COLUMNS = {
    "reviewer_name", "reviewer_id", "reviewer", "user", "username", "user_id",
    "author", "name", "email", "phone", "profile_url",
}

RATING_MIN, RATING_MAX = 1, 5

# Uttarakhand clusters: naive dates are local time; dates with a UTC offset are
# converted here, so months are the calendar months the guests experienced.
LOCAL_TZ = "Asia/Kolkata"


class SchemaError(ValueError):
    """Raised when input reviews do not meet the schema contract."""


def drop_identity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove any reviewer-identity columns (PII) if present."""
    to_drop = [c for c in df.columns if c.strip().lower() in IDENTITY_COLUMNS]
    return df.drop(columns=to_drop)


def _to_local(stamp: pd.Timestamp) -> pd.Timestamp:
    return stamp.tz_convert(LOCAL_TZ).tz_localize(None) if stamp.tzinfo else stamp


def parse_dates(values: pd.Series) -> pd.Series:
    """Parse to naive ``LOCAL_TZ`` datetimes.

    Naive values are already local time and are kept as they are; values with a UTC
    offset (``Z``, ``+05:30``...) are converted to local time. Raises ``ValueError``
    or ``TypeError`` on unparseable input.
    """
    try:
        with warnings.catch_warnings():
            # Mixed offsets: pandas 2 warns and returns objects, pandas 3 raises.
            warnings.simplefilter("error", FutureWarning)
            parsed = pd.to_datetime(values, errors="raise")
    except (ValueError, TypeError, FutureWarning):
        parsed = None
    if parsed is None or parsed.dtype == object:
        # Mixed offsets, or naive mixed with aware: decide one value at a time.
        return pd.to_datetime(values.map(lambda v: _to_local(pd.Timestamp(v))))
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return parsed.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    return parsed


def validate_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and lightly coerce a reviews DataFrame.

    Raises SchemaError with an actionable message on the first problem found.
    Returns a cleaned copy with ``date`` parsed to naive local datetime (see
    ``parse_dates``).
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(
            f"Missing required column(s): {missing}. "
            f"Expected: {REQUIRED_COLUMNS}"
        )

    df = df.copy()

    try:
        df["date"] = parse_dates(df["date"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"Column 'date' is not parseable as a date: {exc}") from exc

    if df["date"].isna().any():
        raise SchemaError("Column 'date' contains missing values.")

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if df["rating"].isna().any():
        raise SchemaError("Column 'rating' contains non-numeric values.")
    out_of_range = ~df["rating"].between(RATING_MIN, RATING_MAX)
    if out_of_range.any():
        bad = df.loc[out_of_range, "rating"].unique().tolist()
        raise SchemaError(
            f"'rating' must be within [{RATING_MIN}, {RATING_MAX}]; found {bad}."
        )

    missing_text = df["text"].isna()
    text = df["text"].astype("string")
    empty = missing_text | text.str.strip().eq("")
    if empty.any():
        raise SchemaError(f"{int(empty.sum())} review(s) have empty 'text'.")
    df["text"] = text.astype(str)

    return df
