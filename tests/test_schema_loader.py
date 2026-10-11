"""Schema validation drops PII and rejects malformed input with clear errors."""

import pandas as pd
import pytest

from cri.loader import load_dir, load_reviews
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


def test_missing_text_raises():
    df = _valid_frame()
    df.loc[1, "text"] = None
    with pytest.raises(SchemaError, match="empty"):
        validate_reviews(df)


def _dates(values):
    df = _valid_frame().assign(date=values)
    out = validate_reviews(df)["date"]
    assert out.dt.tz is None  # always naive local time downstream
    return [str(v) for v in out]


def test_naive_dates_are_local_time_and_never_shifted():
    # A naive evening review must stay on its day (and month) - not move +05:30.
    assert _dates(["2025-06-30 20:00", "2025-06-30"]) == [
        "2025-06-30 20:00:00", "2025-06-30 00:00:00",
    ]


@pytest.mark.parametrize(
    "values",
    [
        ["2025-06-30T14:30:00Z", "2025-06-30T14:30:00Z"],  # one offset (UTC)
        ["2025-06-30T20:00:00+05:30", "2025-06-30T20:00:00+05:30"],  # one offset (IST)
        ["2025-06-30T14:30:00+00:00", "2025-06-30T20:00:00+05:30"],  # mixed offsets
        ["2025-06-30 20:00", "2025-06-30T14:30:00Z"],  # naive mixed with aware
    ],
)
def test_dates_with_offsets_become_local_wall_time(values):
    assert _dates(values) == ["2025-06-30 20:00:00"] * 2


def test_mixed_timezone_offsets_are_parseable():
    assert _dates(["2025-01-01T23:30:00+00:00", "2025-01-02T05:30:00+05:30"]) == [
        "2025-01-02 05:00:00", "2025-01-02 05:30:00",
    ]


def test_unparseable_date_raises():
    with pytest.raises(SchemaError, match="date"):
        validate_reviews(_valid_frame().assign(date=["2025-06-30", "not a date"]))


def test_missing_date_raises():
    df = _valid_frame()
    df.loc[0, "date"] = None
    with pytest.raises(SchemaError, match="date.*missing"):
        validate_reviews(df)


def test_loader_roundtrip_drops_pii(tmp_path):
    df = _valid_frame()
    df["reviewer_id"] = [101, 102]
    path = tmp_path / "reviews.csv"
    df.to_csv(path, index=False)
    loaded = load_reviews(path)
    assert "reviewer_id" not in loaded.columns
    assert len(loaded) == 2


def test_load_dir_drops_rows_repeated_across_files_with_a_warning(tmp_path):
    df = _valid_frame()
    df.to_csv(tmp_path / "part_a.csv", index=False)
    df.iloc[[1]].to_csv(tmp_path / "part_b.csv", index=False)  # overlapping export
    with pytest.warns(UserWarning, match="Dropped 1 review"):
        loaded = load_dir(tmp_path)
    assert len(loaded) == 2


def test_load_dir_keeps_identical_reviews_within_one_file(tmp_path):
    # Two guests can post the same short review on the same day: both are real.
    _valid_frame().iloc[[0, 0, 1]].to_csv(tmp_path / "only.csv", index=False)
    assert len(load_dir(tmp_path)) == 3


def test_load_dir_keeps_the_bundled_sample_whole():
    # The SYNTHETIC sample has two genuinely identical review pairs.
    assert len(load_dir("data/sample")) == len(load_reviews("data/sample/synthetic_reviews.csv"))


def test_inconsistent_day_month_order_is_an_error_not_a_guess():
    # 13/01 only parses day-first; guessing per value would swap 05/01 -> 1 May.
    with pytest.raises(SchemaError, match="date"):
        validate_reviews(_valid_frame().iloc[[0, 1, 1]].assign(
            date=["05/01/2024", "13/01/2024", "02/03/2024"]))


@pytest.mark.parametrize("unit, value", [("s", 1706731200), ("ms", 1706731200000)])
def test_epoch_numbers_are_utc_instants(unit, value):
    # 2024-01-31 20:00 UTC = 2024-02-01 01:30 in Asia/Kolkata.
    assert _dates([value, value]) == ["2024-02-01 01:30:00"] * 2


def test_json_epoch_dates_are_utc_instants(tmp_path):
    df = _valid_frame().assign(date=[1706731200000, 1706731200000])
    path = tmp_path / "export.json"
    df.to_json(path, orient="records")
    assert str(load_reviews(path).loc[0, "date"]) == "2024-02-01 01:30:00"


def test_load_dir_drops_repeats_even_when_column_types_differ(tmp_path):
    rows = _valid_frame().assign(language_hint=["en", None])
    rows.to_csv(tmp_path / "part_a.csv", index=False)  # rating int, hint text/NaN
    # part_b repeats part_a's second row, but a half-star makes its ratings float
    # and its hints are all empty (a float column): per-file hashes used to differ.
    newer = rows.iloc[[1]].assign(property_id="Property C", rating=4.5)
    pd.concat([rows.iloc[[1]], newer]).to_csv(tmp_path / "part_b.csv", index=False)
    with pytest.warns(UserWarning, match="Dropped 1 review"):
        loaded = load_dir(tmp_path)
    assert len(loaded) == 3
