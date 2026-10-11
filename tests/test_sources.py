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
    frame = _export().rename(columns={"review_body": "review_text"})
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


ALIASED = {  # a partner export whose headers are documented aliases
    "hotel": ["Property A"], "source": ["partner"], "review_date": ["2025-01-01"],
    "stars": [4], "review_text": ["Clean room"], "lang": ["en"],
}


def test_load_source_without_mapping_uses_the_documented_aliases(tmp_path):
    path = tmp_path / "aliased.csv"
    pd.DataFrame(ALIASED).to_csv(path, index=False)
    out = load_source(path)
    assert out.loc[0, "text"] == "Clean room"
    assert out.loc[0, "property_id"] == "Property A"


def test_load_source_still_reads_standard_schema_files(tmp_path):
    # Canonical headers win outright, even if an alias-like extra column exists.
    path = tmp_path / "standard.csv"
    _export().rename(columns={
        "hotel_code": "property_id", "channel": "platform", "review_date": "date",
        "stars": "rating", "review_body": "text", "lang": "language_hint",
    }).assign(comment="manager reply").to_csv(path, index=False)
    assert load_source(path).loc[0, "text"] == "Great food"


def test_headers_that_collide_after_normalising_are_ambiguous():
    frame = pd.DataFrame(ALIASED).assign(**{"Review Text": ["other"]})
    with pytest.raises(SchemaError, match="Ambiguous"):
        map_columns(frame)


@pytest.mark.parametrize(
    "mapping, match",
    [
        ({"txt": "review_body"}, "unknown canonical"),
        ({"text": "channel", "platform": "channel"}, "more than one"),
        ({"text": 3}, "strings"),
    ],
)
def test_dict_mappings_are_validated_like_yaml_ones(mapping, match):
    with pytest.raises(SchemaError, match=match):
        map_columns(_export(), mapping)


def test_review_ids_survive_mapping():
    frame = _export().assign(ReviewID=["r-1"])
    out = adapt_frame(frame, {
        "property_id": "hotel_code", "platform": "channel", "date": "review_date",
        "rating": "stars", "text": "review_body", "language_hint": "lang",
        "review_id": "ReviewID",
    })
    assert out.loc[0, "review_id"] == "r-1"


STANDARD = {
    "property_id": ["Property A"], "platform": ["partner"], "date": ["2025-01-01"],
    "rating": [4], "text": ["Clean room"], "language_hint": ["en"],
}


def test_a_partial_mapping_still_prefers_exact_canonical_columns():
    frame = pd.DataFrame(STANDARD).rename(columns={"text": "review_body"}).assign(hotel="x")
    out = map_columns(frame, {"text": "review_body"})  # 'hotel' must not compete
    assert out.loc[0, "property_id"] == "Property A"


def test_aliases_never_reuse_a_column_the_mapping_already_took():
    frame = pd.DataFrame(STANDARD).drop(columns="property_id").assign(hotel="H1")
    with pytest.raises(SchemaError, match="Could not map.*property_id"):
        map_columns(frame.drop(columns="platform"), {"platform": "hotel"})


def test_canonical_headers_differing_only_in_case_are_ambiguous():
    frame = pd.DataFrame(STANDARD).assign(Text=["other"])
    with pytest.raises(SchemaError, match="Ambiguous.*text"):
        map_columns(frame)


def test_a_canonical_header_in_other_case_maps():
    assert map_columns(pd.DataFrame(STANDARD).rename(columns={"text": "Text"})).loc[
        0, "text"] == "Clean room"
