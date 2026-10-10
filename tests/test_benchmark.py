"""End-to-end: the analysis must recover the injected ground-truth patterns, stay
quiet on pattern-free (null) data, and separate market-wide from property-specific.

Multi-seed recall / false-alarm rates are measured by ``python -m cri.calibration``
(see tests/test_calibration.py); these tests pin the behaviour on fixed seeds.
"""

import numpy as np
import pandas as pd
import pytest

from cri.benchmark import (
    benchmark_vs_cluster,
    bootstrap_mean_ci,
    detect_changepoints,
    detect_market_patterns,
    detect_seasonal_dips,
    market_wide_summary,
    review_units,
)
from cri.generate import generate
from cri.pipeline import label_reviews


@pytest.fixture(scope="module")
def labelled():
    return label_reviews(generate(seed=42))


@pytest.fixture(scope="module")
def null_labelled():
    return label_reviews(generate(seed=42, inject_patterns=False))


# --- injected patterns are recovered ---------------------------------------------


def test_recovers_property_f_food_changepoint(labelled):
    cps = detect_changepoints(labelled)
    pf = cps[(cps["property_id"] == "Property F") & (cps["aspect"] == "Food")]
    assert len(pf) == 1
    row = pf.iloc[0]
    assert row["change_month"] == "2025-06"
    assert row["direction"] == "negative"
    assert row["q_value"] <= 0.05


def test_food_decline_is_strongest_negative_shift(labelled):
    cps = detect_changepoints(labelled)
    negatives = cps[cps["direction"] == "negative"]
    strongest = negatives.loc[negatives["delta"].idxmin()]
    assert strongest["property_id"] == "Property F"
    assert strongest["aspect"] == "Food"


def test_food_decline_is_the_propertys_own_not_the_markets(labelled):
    row = detect_changepoints(labelled).iloc[0]
    assert abs(row["market_delta"]) < 0.1  # the market did not move with it
    assert row["raw_delta"] == pytest.approx(row["delta"], abs=0.1)


def test_december_heating_is_market_wide(labelled):
    summary = market_wide_summary(labelled)
    room = summary[summary["aspect"] == "Room"]
    assert len(room) == 1
    assert room.iloc[0]["scope"] == "market-wide"
    assert "December" in room.iloc[0]["pattern"]


def test_food_decline_is_property_specific(labelled):
    summary = market_wide_summary(labelled)
    food = summary[summary["aspect"] == "Food"]
    assert len(food) == 1
    assert food.iloc[0]["scope"] == "property-specific"
    assert "Property F" in food.iloc[0]["properties"]


def test_december_room_dip_affects_majority(labelled):
    dips = detect_seasonal_dips(labelled, month=12)
    room_props = dips[dips["aspect"] == "Room"]["property_id"].nunique()
    total = labelled["property_id"].nunique()
    assert room_props / total >= 0.6


def test_market_patterns_are_only_the_injected_one(labelled):
    patterns = detect_market_patterns(labelled)
    assert len(patterns) == 1
    row = patterns.iloc[0]
    assert (row["aspect"], row["kind"], int(row["calendar_month"])) == ("Room", "seasonal", 12)


def test_seasonal_food_decline_is_not_mistaken_for_seasonality(labelled):
    # Property F's Jun-Dec 2025 collapse must not look like a recurring dip.
    dips = detect_seasonal_dips(labelled)
    assert (dips["aspect"] == "Food").sum() == 0


def test_benchmark_flags_property_f_food_as_lagging(labelled):
    bench = benchmark_vs_cluster(labelled)
    row = bench[
        (bench["property_id"] == "Property F") & (bench["aspect"] == "Food")
    ].iloc[0]
    assert row["flag"] == "lag"
    assert row["ci_high"] < row["cluster_mean"]


# --- null data stays quiet --------------------------------------------------------


def test_null_data_has_no_changepoints_or_market_patterns(null_labelled):
    assert detect_changepoints(null_labelled).empty
    assert detect_market_patterns(null_labelled).empty
    assert market_wide_summary(null_labelled).empty


# --- market-wide step changes -----------------------------------------------------


def _inject_market_step(lab, aspect, start, flip=0.5, seed=0):
    """Synthetic market-wide decline: after ``start``, flip a share of the aspect's
    positive mentions to negative in EVERY property (e.g. a road closure)."""
    rng = np.random.default_rng(seed)
    mask = (lab["aspect"] == aspect) & (lab["date"] >= start) & (lab["sentiment"] > 0)
    flip_idx = lab.index[mask][rng.random(int(mask.sum())) < flip]
    out = lab.copy()
    out.loc[flip_idx, "sentiment"] = -1
    return out


def test_market_wide_step_is_market_wide_not_blamed_on_a_property(null_labelled):
    hit = _inject_market_step(null_labelled, "Location", pd.Timestamp("2025-03-01"))
    patterns = detect_market_patterns(hit)
    steps = patterns[(patterns["aspect"] == "Location") & (patterns["kind"] == "step")]
    assert len(steps) == 1
    assert steps.iloc[0]["change_month"] in {"2025-02", "2025-03", "2025-04"}
    scope = market_wide_summary(hit).set_index("aspect")
    assert scope.at["Location", "scope"] == "market-wide"
    # Relative to the market nothing changed, so no property is singled out.
    cps = detect_changepoints(hit)
    assert (cps["aspect"] == "Location").sum() == 0


# --- small clusters ----------------------------------------------------------------


def test_two_property_cluster_is_undetermined(labelled):
    two = labelled[labelled["property_id"].isin(["Property F", "Property A"])]
    summary = market_wide_summary(two)
    assert (summary["scope"] == "undetermined").all()
    assert detect_market_patterns(two).empty
    # A property's own change is still visible, measured on its raw series.
    cps = detect_changepoints(two)
    food = cps[(cps["property_id"] == "Property F") & (cps["aspect"] == "Food")]
    assert len(food) == 1 and np.isnan(food.iloc[0]["market_delta"])


def test_single_property_cluster_does_not_crash(labelled):
    one = labelled[labelled["property_id"] == "Property F"]
    assert (market_wide_summary(one)["scope"] == "undetermined").all()


def test_empty_input_returns_empty_frames():
    empty = label_reviews(generate(seed=1).head(0))
    assert detect_changepoints(empty).empty
    assert detect_market_patterns(empty).empty
    assert market_wide_summary(empty).empty


# --- bootstrap CIs ------------------------------------------------------------------


def test_bootstrap_ci_brackets_the_mean_and_is_deterministic():
    rng = np.random.default_rng(3)
    sums = rng.choice([-2, -1, 0, 1, 2], size=80).astype(float)
    counts = np.full(80, 2.0)
    lo, hi = bootstrap_mean_ci(sums, counts, seed=7)
    point = sums.sum() / counts.sum()
    assert lo < point < hi
    assert (lo, hi) == bootstrap_mean_ci(sums, counts, seed=7)


def test_bootstrap_ci_narrows_with_more_reviews():
    rng = np.random.default_rng(4)
    small = rng.choice([-1.0, 1.0], size=20)
    big = rng.choice([-1.0, 1.0], size=2000)
    lo_s, hi_s = bootstrap_mean_ci(small, np.ones(20), seed=1)
    lo_b, hi_b = bootstrap_mean_ci(big, np.ones(2000), seed=1)
    assert (hi_b - lo_b) < (hi_s - lo_s)


def test_bootstrap_ci_edge_cases():
    assert all(np.isnan(bootstrap_mean_ci(np.array([]), np.array([]))))
    assert bootstrap_mean_ci(np.array([3.0]), np.array([3.0])) == (1.0, 1.0)


def test_property_ci_is_identical_alone_or_in_the_full_run(labelled):
    full = benchmark_vs_cluster(labelled)
    alone = benchmark_vs_cluster(labelled, property_id="Property D")
    expected = full[full["property_id"] == "Property D"].reset_index(drop=True)
    pd.testing.assert_frame_equal(alone, expected)


def test_flags_need_enough_reviews(labelled):
    tiny = labelled[labelled["review_id"].isin(labelled["review_id"].unique()[:150])]
    bench = benchmark_vs_cluster(tiny)
    assert (bench.loc[bench["n_reviews"] < 10, "flag"] == "on_par").all()


# --- review units ------------------------------------------------------------------


def test_review_units_collapse_mentions_of_one_review(labelled):
    units = review_units(labelled)
    assert not units.duplicated(["review_id", "aspect"]).any()
    assert len(units) < len(labelled)  # some reviews mention an aspect twice


def test_review_units_fallback_without_review_id(labelled):
    units = review_units(labelled.drop(columns="review_id"))
    assert not units.duplicated(["property_id", "date", "aspect"]).any()
