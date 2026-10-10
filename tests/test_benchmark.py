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
from sim_helpers import constant, simulate, starting, step


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


def test_benchmark_flags_a_clear_laggard(labelled):
    bench = benchmark_vs_cluster(labelled)
    row = bench[(bench["property_id"] == "Property D") & (bench["aspect"] == "Food")].iloc[0]
    assert row["flag"] == "lag"
    assert row["ci_high"] < row["cluster_mean"] and row["q_value"] <= 0.05


def test_flags_never_contradict_the_interval_shown(labelled):
    bench = benchmark_vs_cluster(labelled)
    lead, lag = bench[bench["flag"] == "lead"], bench[bench["flag"] == "lag"]
    assert (lead["ci_low"] > lead["cluster_mean"]).all()
    assert (lag["ci_high"] < lag["cluster_mean"]).all()
    assert (bench.loc[bench["flag"] != "on_par", "q_value"] <= 0.05).all()


def test_property_f_all_time_food_gap_is_not_overclaimed(labelled):
    # F's all-time Food mean blends 17 good months and 7 bad ones: its gap is weak
    # once ~100 pairs are tested together. The real signal is the 2025-06 decline,
    # which the changepoint (and priority_actions) report.
    bench = benchmark_vs_cluster(labelled)
    row = bench[(bench["property_id"] == "Property F") & (bench["aspect"] == "Food")].iloc[0]
    assert row["diff"] < 0 and row["q_value"] > 0.05 and row["flag"] == "on_par"


def test_lead_lag_flags_are_fdr_controlled_on_a_null_cluster():
    # 12 identical properties x 4 aspects: every flag would be false.
    parts = [
        simulate({f"P{i}": constant(0.6) for i in range(12)}, aspect=a, per_month=3, seed=50 + j)
        .assign(review_id=lambda f, j=j: f["review_id"] + j * 10**6)
        for j, a in enumerate(["Food", "Room", "Staff", "Location"])
    ]
    bench = benchmark_vs_cluster(pd.concat(parts, ignore_index=True))
    assert (bench["flag"] == "on_par").all()


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
    # One review cannot give an interval: NaN, never a zero-width "certain" CI.
    assert all(np.isnan(bootstrap_mean_ci(np.array([3.0]), np.array([3.0]))))


def test_property_ci_is_identical_alone_or_in_the_full_run(labelled):
    full = benchmark_vs_cluster(labelled)
    alone = benchmark_vs_cluster(labelled, property_id="Property D")
    expected = full[full["property_id"] == "Property D"].reset_index(drop=True)
    pd.testing.assert_frame_equal(alone, expected)


def test_flags_need_enough_reviews(labelled):
    tiny = labelled[labelled["review_id"].isin(labelled["review_id"].unique()[:150])]
    bench = benchmark_vs_cluster(tiny)
    small = bench[bench["n_reviews"] < 10]
    assert len(small) > 0
    assert (small["flag"] == "on_par").all()
    assert small["ci_low"].isna().all() and small["ci_high"].isna().all()


# --- review units ------------------------------------------------------------------


def test_review_units_collapse_mentions_of_one_review(labelled):
    units = review_units(labelled)
    assert not units.duplicated(["review_id", "aspect"]).any()
    assert len(units) < len(labelled)  # some reviews mention an aspect twice


def test_review_units_fallback_without_review_id(labelled):
    units = review_units(labelled.drop(columns="review_id"))
    assert not units.duplicated(["property_id", "date", "aspect"]).any()


# --- regressions from the adversarial review -----------------------------------------


def test_property_entering_the_data_does_not_fake_declines_elsewhere():
    # E (strong, high volume) only appears from 2025: nobody actually changes.
    lab = simulate(
        {**{k: constant(0.5) for k in "ABCD"}, "E": starting(0.9, "2025-01")},
        per_month={"A": 15, "B": 15, "C": 15, "D": 15, "E": 45},
        seed=0,
    )
    assert detect_changepoints(lab).empty


def test_changepoint_test_is_calibrated_for_a_standout_property_in_a_small_cluster():
    # Null data: A is much better rated (low variance) than B and C. The market
    # error must use the competitors' variance, or A's p-values are too small.
    from cri.benchmark import _changepoints_from_units

    ps = []
    for s in range(150):
        lab = simulate({"A": constant(0.92), "B": constant(0.5), "C": constant(0.5)},
                       per_month=6, seed=1000 + s)
        raw = _changepoints_from_units(review_units(lab), 0.0, 1.0)
        ps.extend(raw.loc[raw["property_id"] == "A", "p_value"])
    assert np.mean(np.asarray(ps) <= 0.05) <= 0.06


def test_one_year_market_step_is_a_step_not_seasonality():
    lab = simulate({k: step(0.75, 0.35, "2025-07") for k in "ABCDEF"},
                   start="2025-01", end="2025-12", per_month=20, seed=1)
    patterns = detect_market_patterns(lab)
    assert (patterns["kind"] == "seasonal").sum() == 0
    steps = patterns[patterns["kind"] == "step"]
    assert len(steps) == 1 and steps.iloc[0]["change_month"] == "2025-07"


def test_aspect_reviewed_at_one_property_is_still_tested():
    food = simulate({k: constant(0.6) for k in "ABC"}, seed=3)
    spa = simulate({"A": step(0.9, 0.1, "2025-01")}, aspect="Spa", seed=4)
    lab = pd.concat([food, spa.assign(review_id=spa["review_id"] + 10**6)], ignore_index=True)
    cps = detect_changepoints(lab)
    spa_cp = cps[cps["aspect"] == "Spa"]
    assert len(spa_cp) == 1 and spa_cp.iloc[0]["change_month"] == "2025-01"
    assert np.isnan(spa_cp.iloc[0]["market_delta"])  # no market to compare with
    scope = market_wide_summary(lab).set_index("aspect")
    assert scope.at["Spa", "scope"] == "undetermined"


def test_missing_change_month_is_none_not_nan(labelled):
    # Seasonal (no change month) next to a step row: the gap must stay None, since
    # NaN is truthy and pandas 3 would otherwise store it in a string column.
    hit = _inject_market_step(labelled, "Staff", pd.Timestamp("2025-03-01"), flip=0.9)
    patterns = detect_market_patterns(hit)
    assert set(patterns["kind"]) == {"seasonal", "step"}
    seasonal = patterns[patterns["kind"] == "seasonal"]
    assert all(v is None for v in seasonal["change_month"])


def test_effect_floor_is_applied_before_rounding(monkeypatch):
    import cri.benchmark as b
    from cri.changepoint import Changepoint

    monkeypatch.setattr(
        b, "find_changepoint",
        lambda *a, **k: Changepoint(index=6, delta=-0.3996, raw_delta=-0.3996, p_value=1e-9),
    )
    lab = simulate({"A": constant(0.5)}, seed=0)
    assert b.detect_changepoints(lab).empty  # |delta| 0.3996 < 0.4, even though it rounds to 0.4
