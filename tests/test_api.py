"""Contract tests for the dashboard facade (docs/HACKATHON_PLAN.md section 3.2).

Every function must return at least the documented columns; additive extension
columns are allowed. Invalid input raises ValueError naming the valid options.
"""

import dataclasses

import pandas as pd
import pytest

from cri import api
from cri.classify import load_aspects
from cri.generate import generate

CONTRACT = {
    "property_scorecard": [
        "aspect", "mean", "ci_low", "ci_high", "n", "cluster_mean", "diff", "flag",
    ],
    "trend": ["month", "mean", "n"],
    "changepoints": ["property_id", "aspect", "change_month", "delta", "direction"],
    "market_scope": ["aspect", "scope", "fraction", "n_properties", "properties"],
    "destination_summary": ["aspect", "cluster_mean", "n", "pct_negative", "scope"],
    "priority_actions": ["aspect", "gap", "volume", "impact_score", "started", "rationale"],
}


@pytest.fixture(scope="module")
def d():
    return api.load_cluster()


def _has(frame, cols):
    missing = [c for c in cols if c not in frame.columns]
    assert not missing, f"missing contract columns {missing}"


# --- loading ------------------------------------------------------------------------


def test_default_load_is_labelled_synthetic(d):
    assert d.is_synthetic
    assert "SYNTHETIC" in d.source_name
    assert d.reviews["review_id"].is_unique
    assert set(d.labelled["review_id"]) <= set(d.reviews["review_id"])
    expected = ["review_id", "property_id", "date", "aspect", "sentiment"]
    assert list(d.labelled.columns[:5]) == expected


def test_cluster_data_is_frozen(d):
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.is_synthetic = False


def _write(df, path):
    df.to_csv(path, index=False)
    return path


def test_load_from_file_detects_synthetic_by_filename(tmp_path):
    sample = generate(seed=3).head(400)
    real = api.load_cluster(_write(sample, tmp_path / "partner_export.csv"))
    synth = api.load_cluster(_write(sample, tmp_path / "synthetic_reviews.csv"))
    assert not real.is_synthetic and real.source_name == "partner_export.csv"
    assert synth.is_synthetic
    assert len(real.reviews) == 400


def test_load_from_directory(tmp_path):
    sample = generate(seed=3)
    _write(sample.head(300), tmp_path / "a.csv")
    _write(sample.iloc[300:600], tmp_path / "b.csv")
    data = api.load_cluster(tmp_path)
    assert len(data.reviews) == 600 and data.reviews["review_id"].is_unique
    assert not data.is_synthetic
    _write(sample.iloc[600:700], tmp_path / "synthetic_extra.csv")
    assert api.load_cluster(tmp_path).is_synthetic  # any synthetic file -> banner


def test_load_raw_dir_from_env(tmp_path, monkeypatch):
    _write(generate(seed=4).head(200), tmp_path / "export.csv")
    monkeypatch.setenv("CRI_DATA_RAW_DIR", str(tmp_path))
    data = api.load_cluster(synthetic=False)
    assert len(data.reviews) == 200 and not data.is_synthetic


def test_empty_raw_dir_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("CRI_DATA_RAW_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        api.load_cluster(synthetic=False)


def test_supplied_review_ids_are_kept_and_must_be_unique(tmp_path):
    sample = generate(seed=5).head(50).assign(review_id=range(1001, 1051))
    data = api.load_cluster(_write(sample, tmp_path / "with_ids.csv"))
    assert data.reviews["review_id"].min() == 1001
    with pytest.raises(ValueError, match="review_id"):
        api.load_cluster(_write(sample.assign(review_id=7), tmp_path / "dupes.csv"))


# --- lookups ------------------------------------------------------------------------


def test_lookups(d):
    assert api.list_properties(d) == sorted(d.reviews["property_id"].unique())
    assert api.list_aspects() == list(load_aspects())
    lo, hi = api.date_range(d)
    assert isinstance(lo, pd.Timestamp) and lo < hi


# --- every analysis honours the contract --------------------------------------------


def test_contract_columns(d):
    _has(api.property_scorecard(d, "Property F"), CONTRACT["property_scorecard"])
    _has(api.trend(d, "Property F", "Food"), CONTRACT["trend"])
    _has(api.changepoints(d), CONTRACT["changepoints"])
    _has(api.market_scope(d), CONTRACT["market_scope"])
    _has(api.destination_summary(d), CONTRACT["destination_summary"])
    _has(api.priority_actions(d, "Property F"), CONTRACT["priority_actions"])


def test_property_scorecard_shape(d):
    sc = api.property_scorecard(d, "Property F")
    assert list(sc["aspect"]) == [a for a in api.list_aspects() if a in set(sc["aspect"])]
    assert set(sc["flag"]) <= {"lead", "lag", "on_par"}
    assert (sc["ci_low"] <= sc["mean"]).all() and (sc["mean"] <= sc["ci_high"]).all()


def test_cluster_matrix_shape(d):
    m = api.cluster_matrix(d)
    assert list(m.index) == api.list_properties(d)
    assert list(m.columns) == api.list_aspects()
    assert ((m >= -1) & (m <= 1)).all().all()


def test_trend_months_have_data(d):
    tr = api.trend(d, "Property F", "Food")
    assert (tr["n"] > 0).all() and tr["month"].is_monotonic_increasing


def test_changepoint_filters_keep_global_q_values(d):
    full = api.changepoints(d)
    only_f = api.changepoints(d, property_id="Property F", aspect="Food")
    expected = full[(full["property_id"] == "Property F") & (full["aspect"] == "Food")]
    pd.testing.assert_frame_equal(only_f, expected.reset_index(drop=True))
    none = api.changepoints(d, property_id="Property L")
    assert none.empty and list(none.columns) == list(full.columns)


def test_scope_values(d):
    assert set(api.market_scope(d)["scope"]) <= {"market-wide", "property-specific", "undetermined"}
    assert set(api.destination_summary(d)["scope"]) <= {
        "market-wide", "property-specific", "stable", "undetermined"
    }


def test_functions_do_not_mutate_inputs(d):
    before = (d.reviews.copy(), d.labelled.copy())
    api.property_scorecard(d, "Property F")
    api.priority_actions(d, "Property F")
    api.destination_summary(d)
    api.search_reviews(d, query="food")
    pd.testing.assert_frame_equal(d.reviews, before[0])
    pd.testing.assert_frame_equal(d.labelled, before[1])


# --- search_reviews -----------------------------------------------------------------


def test_search_filters_on_classified_clauses(d):
    hits = api.search_reviews(
        d, property_id="Property F", aspect="Food", sentiment=-1,
        start="2025-06-01", end="2025-12-31",
    )
    assert not hits.empty
    assert (hits["property_id"] == "Property F").all()
    assert (hits["aspect"] == "Food").all() and (hits["sentiment"] == -1).all()
    assert hits["date"].between("2025-06-01", "2025-12-31").all()
    assert hits["date"].is_monotonic_decreasing  # newest first


def test_search_end_date_is_inclusive(d):
    day = d.reviews["date"].max()
    assert (api.search_reviews(d, start=day, end=day)["date"] == day).all()
    assert not api.search_reviews(d, start=day, end=day).empty


def test_search_query_is_case_insensitive_and_literal(d):
    upper = api.search_reviews(d, query="KHAANA")
    assert not upper.empty
    assert upper["text"].str.lower().str.contains("khaana", regex=False).all()
    assert api.search_reviews(d, query="(.*").empty  # regex characters are literal


def test_search_without_clause_filters_keeps_every_review(d):
    out = api.search_reviews(d)
    assert set(out["review_id"]) == set(d.reviews["review_id"])
    assert str(out["sentiment"].dtype) == "Int64"


def test_search_empty_result_keeps_columns(d):
    out = api.search_reviews(d, query="no review says this zzzz")
    assert out.empty and list(out.columns) == api.SEARCH_COLUMNS


# --- invalid input ------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda d: api.property_scorecard(d, "Hotel X"),
        lambda d: api.trend(d, "Property F", "Spa"),
        lambda d: api.trend(d, "Hotel X", "Food"),
        lambda d: api.changepoints(d, aspect="Spa"),
        lambda d: api.priority_actions(d, "Property F", top_n=0),
        lambda d: api.priority_actions(d, "Property F", top_n=True),
        lambda d: api.priority_actions(d, "Hotel X"),
        lambda d: api.search_reviews(d, sentiment=2),
        lambda d: api.search_reviews(d, sentiment=True),
        lambda d: api.search_reviews(d, property_id="Hotel X"),
    ],
)
def test_invalid_input_raises_value_error(d, call):
    with pytest.raises(ValueError):
        call(d)
