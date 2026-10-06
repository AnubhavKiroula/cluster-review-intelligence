"""Schema validation drops PII and rejects malformed input with clear errors."""

import pandas as pd
import pytest

from cri.loader import load_reviews
from cri.schema import REQUIRED_COLUMNS, SchemaError, drop_identity_columns, validate_reviews


def _valid_frame():
    return pd.DataFrame(
        {
            "property_id": ["Property A", "Property B"],
            "platform": ["GoogleMaps", "Booking"],
            "date": ["2024-01-05", "2024-02-10"],
            "rating": [5, 2],
            "text": ["Great food and clean room", "Rude staff, dirty bathroom"],
            "language_hint": ["en", "en"],
        }
    )


def test_drop_identity_columns():
    df = _valid_frame()
    df["reviewer_name"] = ["Asha", "Ravi"]
    df["email"] = ["a@x.com", "b@x.com"]
    cleaned = drop_identity_columns(df)
    assert "reviewer_name" not in cleaned.columns
    assert "email" not in cleaned.columns
    assert list(cleaned.columns) == REQUIRED_COLUMNS


def test_validate_ok():
    out = validate_reviews(_valid_frame())
    assert pd.api.types.is_datetime64_any_dtype(out["date"])


def test_missing_column_raises():
    df = _valid_frame().drop(columns=["rating"])
    with pytest.raises(SchemaError, match="Missing required column"):
        validate_reviews(df)


def test_rating_out_of_range_raises():
    df = _valid_frame()
    df.loc[0, "rating"] = 9
    with pytest.raises(SchemaError, match="rating"):
        validate_reviews(df)


def test_empty_text_raises():
    df = _valid_frame()
    df.loc[1, "text"] = "   "
    with pytest.raises(SchemaError, match="empty"):
        validate_reviews(df)


def test_loader_roundtrip_drops_pii(tmp_path):
    df = _valid_frame()
    df["reviewer_id"] = [101, 102]
    path = tmp_path / "reviews.csv"
    df.to_csv(path, index=False)
    loaded = load_reviews(path)
    assert "reviewer_id" not in loaded.columns
    assert len(loaded) == 2
