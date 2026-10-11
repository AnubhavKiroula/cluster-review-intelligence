"""Source adapters map exports without bypassing schema and PII checks."""

import pandas as pd
import pytest

from cri.schema import SchemaError
from cri.sources import adapt_frame, load_mapping, load_source, map_columns


def _export() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hotel_code": ["Property A"],
            "channel": ["partner"],
            "review_date": ["2025-01-01"],
            "stars": [5],
            "review_body": ["Great food"],
            "lang": ["en"],
            "reviewer_name": ["Must not survive"],
        }
    )


def test_explicit_mapping_adapts_and_drops_identity():
    out = adapt_frame(
        _export(),
        {
            "property_id": "hotel_code",
            "platform": "channel",
            "date": "review_date",
            "rating": "stars",
            "text": "review_body",
            "language_hint": "lang",
        },
    )
    assert list(out.columns) == [
        "property_id", "platform", "date", "rating", "text", "language_hint"
    ]
    assert out.loc[0, "text"] == "Great food"
    assert pd.api.types.is_datetime64_any_dtype(out["date"])


def test_ambiguous_alias_requires_mapping():
    frame = _export().rename(columns={"review_body": "text"})
    frame["comment"] = "also text"
    with pytest.raises(SchemaError, match="Ambiguous"):
        map_columns(frame)


def test_missing_text_is_rejected():
    frame = _export().assign(review_body=[None])
    with pytest.raises(SchemaError, match="empty 'text'"):
        adapt_frame(
            frame,
            {
                "text": "review_body",
                "property_id": "hotel_code",
                "platform": "channel",
                "date": "review_date",
                "rating": "stars",
                "language_hint": "lang",
            },
        )


def test_mapping_cannot_relabel_identity_column():
    with pytest.raises(SchemaError, match="missing source column"):
        adapt_frame(_export(), {"text": "reviewer_name"})


def test_load_source_roundtrip(tmp_path):
    path = tmp_path / "export.csv"
    _export().to_csv(path, index=False)
    out = load_source(
        path,
        {
            "property_id": "hotel_code",
            "platform": "channel",
            "date": "review_date",
            "rating": "stars",
            "text": "review_body",
            "language_hint": "lang",
        },
    )
    assert len(out) == 1


def test_load_source_from_yaml_mapping(tmp_path):
    csv_path = tmp_path / "export.csv"
    config_path = tmp_path / "mapping.yaml"
    _export().to_csv(csv_path, index=False)
    config_path.write_text(
        "columns:\n"
        "  property_id: hotel_code\n"
        "  platform: channel\n"
        "  date: review_date\n"
        "  rating: stars\n"
        "  text: review_body\n"
        "  language_hint: lang\n",
        encoding="utf-8",
    )
    assert load_mapping(config_path)["text"] == "review_body"
    out = load_source(csv_path, mapping_file=config_path)
    assert len(out) == 1
