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


# --- regressions from the adversarial review -----------------------------------------


def test_numeric_property_ids_work_everywhere(tmp_path):
    sample = generate(seed=3)
    ids = {f"Property {c}": 100 + i for i, c in enumerate("ABCDEFGHIJKL")}
    data = api.load_cluster(_write(sample.assign(property_id=sample["property_id"].map(ids)),
                                   tmp_path / "numeric_ids.csv"))
    first = api.list_properties(data)[0]
    assert first == "100"
    assert len(api.property_scorecard(data, first)) > 0
    assert not api.cluster_matrix(data).isna().all().all()
    assert len(api.trend(data, first, "Food")) > 0
    api.market_scope(data)
    api.destination_summary(data)


def test_properties_are_listed_in_natural_order(tmp_path):
    sample = generate(seed=3)
    renamed = sample.assign(property_id=sample["property_id"].str.replace("Property ", "P"))
    renamed = renamed.assign(property_id=renamed["property_id"].map(
        {f"P{c}": f"Hotel {i + 1}" for i, c in enumerate("ABCDEFGHIJKL")}))
    data = api.load_cluster(_write(renamed, tmp_path / "names.csv"))
    assert api.list_properties(data)[:3] == ["Hotel 1", "Hotel 2", "Hotel 3"]


@pytest.mark.parametrize("fmt", ["%Y-%m-%dT08:15:00Z", "%Y-%m-%dT10:00:00+05:30"])
def test_timezone_aware_dates_become_naive_local_time(tmp_path, fmt):
    sample = generate(seed=2)
    stamped = sample.assign(date=pd.to_datetime(sample["date"]).dt.strftime(fmt))
    data = api.load_cluster(_write(stamped, tmp_path / "tz.csv"))
    assert data.reviews["date"].dt.tz is None
    assert len(api.priority_actions(data, "Property F")) > 0
    assert not api.search_reviews(data, start="2025-01-01", end="2025-03-31").empty


def test_naive_evening_reviews_stay_in_their_month(tmp_path):
    # Naive dates are local time: 20:00 on the 30th must not move into the next month.
    sample = generate(seed=2)
    evening = sample.assign(date=pd.to_datetime(sample["date"]) + pd.Timedelta(hours=20))
    data = api.load_cluster(_write(evening, tmp_path / "evening.csv"))
    assert data.reviews["date"].tolist() == evening["date"].tolist()


def test_raw_columns_named_like_clause_columns_do_not_break_search(tmp_path):
    sample = generate(seed=2).assign(sentiment="positive", aspect="misc", sentence="x")
    data = api.load_cluster(_write(sample, tmp_path / "collide.csv"))
    assert (api.search_reviews(data, sentiment=-1)["sentiment"] == -1).all()
    assert (api.search_reviews(data, aspect="Food")["aspect"] == "Food").all()


def test_synthetic_detected_from_a_parent_folder(tmp_path):
    folder = tmp_path / "synthetic"
    folder.mkdir()
    data = api.load_cluster(_write(generate(seed=3).head(300), folder / "reviews.csv"))
    assert data.is_synthetic


def test_top_n_accepts_numpy_integers(d):
    import numpy as np

    assert len(api.priority_actions(d, "Property D", top_n=np.int64(2))) == 2


def test_empty_trend_has_typed_columns(tmp_path):
    sample = generate(seed=3).head(400)
    quiet = pd.DataFrame([{**sample.iloc[0].to_dict(), "property_id": "Property Z",
                           "text": "We stayed two nights."}])
    data = api.load_cluster(_write(pd.concat([sample, quiet]), tmp_path / "quiet.csv"))
    tr = api.trend(data, "Property Z", "Food")
    assert tr.empty
    assert pd.api.types.is_datetime64_any_dtype(tr["month"]) and tr["n"].dtype == "int64"
    unmatched = api.search_reviews(data, property_id="Property Z")
    assert len(unmatched) == 1 and unmatched["aspect"].isna().all()


def test_thresholds_the_ui_draws_are_exposed():
    assert 0 < api.MARKET_WIDE_FRACTION <= 1
    assert api.MIN_REVIEWS_FOR_FLAG >= 1


def test_classify_text_shows_each_aspect_with_its_clause():
    # Demo step 4: a typed Hinglish review is classified live, clause by clause.
    out = api.classify_text("Khana accha tha lekin kamra ganda tha.")
    assert list(out.columns) == api.CLASSIFY_COLUMNS == ["aspect", "sentiment", "sentence"]
    assert {("Food", 1), ("Room", -1)} <= set(zip(out["aspect"], out["sentiment"], strict=True))
    assert out.loc[out["aspect"] == "Food", "sentence"].iloc[0] == "khana accha tha"
    assert out["sentiment"].dtype == "int64"


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_classify_text_blank_input_is_an_empty_frame(blank):
    out = api.classify_text(blank)
    assert out.empty and list(out.columns) == api.CLASSIFY_COLUMNS


def test_classify_text_rejects_non_text():
    with pytest.raises(ValueError, match="text"):
        api.classify_text(42)


def test_the_classifier_is_built_once_per_configuration(monkeypatch):
    # The transformer backend loads a ~541 MB model: never once per typed review.
    calls = []
    real = api.get_classifier
    monkeypatch.setattr(api, "get_classifier", lambda name=None: calls.append(name) or real(name))
    api._classifier.cache_clear()
    try:
        api.classify_text("The food was good.")
        api.classify_text("The room was dirty.")
        assert len(calls) == 1
    finally:
        api._classifier.cache_clear()


# --- "Did my fix work?" ---------------------------------------------------------------


def test_intervention_check_contract(d):
    r = api.intervention_check(d, "Property A", "Room", "2025-12")
    assert list(r) == api.INTERVENTION_KEYS
    assert r["verdict"] == "no detectable change"
    assert r["naive_delta"] < r["effect"]  # the market's December dip is removed


@pytest.mark.parametrize(
    ("args", "match"),
    [
        (("Nope", "Food", "2025-06"), "Unknown property_id"),
        (("Property A", "Spa", "2025-06"), "Unknown aspect"),
        (("Property A", "Food", "2024-01"), "after the first month"),
        (("Property A", "Food", "2031-01"), "after the first month"),
        (("Property A", "Food", "someday"), "Not a date"),
    ],
)
def test_intervention_check_rejects_bad_input(d, args, match):
    with pytest.raises(ValueError, match=match):
        api.intervention_check(d, *args)


# --- Sources without review dates (e.g. the real Kausani corpus) ---------------------


@pytest.fixture(scope="module")
def undated(tmp_path_factory):
    path = tmp_path_factory.mktemp("undated") / "synthetic_undated.csv"
    generate(seed=42).drop(columns=["date"]).to_csv(path, index=False)
    return api.load_cluster(path)


def test_a_source_without_dates_is_accepted_and_never_filled(undated):
    assert not undated.has_dates and "date" not in undated.reviews.columns
    assert undated.labelled["date"].isna().all()  # missing, not invented
    assert api.load_cluster().has_dates
    assert all(pd.isna(x) for x in api.date_range(undated))


def test_time_based_results_are_empty_typed_frames_without_dates(undated):
    _has(api.trend(undated, "Property F", "Food"), CONTRACT["trend"])
    assert api.trend(undated, "Property F", "Food").empty
    cps = api.changepoints(undated)
    _has(cps, CONTRACT["changepoints"])
    assert cps.empty
    from cri import benchmark
    assert benchmark.detect_market_patterns(undated.labelled).empty
    assert list(benchmark.detect_seasonal_dips(undated.labelled).columns) == \
        benchmark.SEASONAL_COLUMNS
    assert benchmark.detect_seasonal_dips(undated.labelled).empty


def test_fix_check_without_dates_is_no_data_not_an_error(undated):
    r = api.intervention_check(undated, "Property A", "Room", "2025-12")
    assert set(r) == set(api.INTERVENTION_KEYS)
    assert r["verdict"] == "no data" and r["effect"] is None
    assert "no review dates" in r["summary"]


def test_priorities_without_dates_have_no_start_and_say_what_was_not_tested(undated):
    pa = api.priority_actions(undated, "Property D")
    assert len(pa) > 0 and pa["started"].isna().all()
    assert (pa["whose_problem"] == "yours alone").all()
    assert pa["whose_detail"].str.contains("no review dates").all()


def test_market_scope_without_dates_claims_no_time_pattern(undated):
    scope = api.market_scope(undated)
    assert len(scope) > 0
    assert not scope["pattern"].str.contains("seasonal|from 20|decline", regex=True).any()
    # Room's December dip exists in the data but cannot be seen without dates.
    assert set(scope["scope"]) <= {"property-specific", "market-wide", "undetermined"}
    dest = api.destination_summary(undated)
    assert not dest["pattern"].str.contains("shift").any()


def test_a_shared_weak_spot_is_market_wide_without_dates():
    # 5 properties: guests complain about Room at all of them, never about Food.
    rows, rid = [], 0
    for p in "ABCDE":
        for i in range(30):
            rid += 1
            rows += [(rid, f"Property {p}", "Food", 1),
                     (rid, f"Property {p}", "Room", -1 if i % 2 else 1)]
    labelled = pd.DataFrame(rows, columns=["review_id", "property_id", "aspect", "sentiment"])
    labelled = labelled.assign(date=pd.NaT, sentence="")
    d = api.ClusterData(labelled[["review_id", "property_id"]].drop_duplicates(), labelled,
                        True, "test", has_dates=False)
    room = api.market_scope(d).set_index("aspect").loc["Room"]
    assert room["scope"] == "market-wide" and room["n_properties"] == 5
    assert room["pattern"].startswith("shared weak spot")


def test_search_without_dates_rejects_a_date_filter(undated):
    hits = api.search_reviews(undated, property_id="Property F", aspect="Food")
    assert len(hits) > 0 and hits["date"].isna().all()
    with pytest.raises(ValueError, match="no review dates"):
        api.search_reviews(undated, start="2025-01-01")
