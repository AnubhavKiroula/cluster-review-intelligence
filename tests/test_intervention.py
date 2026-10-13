""""Did my fix work?" - the market-adjusted before/after check.

Simulated clusters (tests/sim_helpers.py) with known truth: a real fix must be
found, a market-wide change must NOT be credited to the property, and pattern-free
data must rarely produce a verdict. Rates over many seeds are in
docs/methodology.md section 12; these tests pin fixed seeds plus small-sample rates.
"""

import numpy as np
import pandas as pd
import pytest

from cri.changepoint import find_changepoint, shift_at, t_ppf
from cri.generate import generate
from cri.intervention import INTERVENTION_KEYS, VERDICTS, evaluate_intervention
from cri.pipeline import label_reviews
from sim_helpers import constant, simulate, step

OTHERS = [f"P{i}" for i in range(1, 6)]
FLAT = constant(0.6)


def _cluster(target, seed=0, others=OTHERS, other_p=FLAT, **kwargs):
    return simulate({"P0": target, **dict.fromkeys(others, other_p)}, seed=seed, **kwargs)


def _check(labelled, start="2025-06", **kwargs):
    result = evaluate_intervention(labelled, "P0", "Food", start, **kwargs)
    assert list(result) == INTERVENTION_KEYS
    assert result["verdict"] in VERDICTS
    return result


# --- statistics helpers ---------------------------------------------------------------


@pytest.mark.parametrize(("prob", "df", "expected"), [(0.975, 10, 2.2281), (0.95, 5, 2.0150),
                                                       (0.5, 7, 0.0), (0.025, 30, -2.0423)])
def test_t_ppf_matches_tables(prob, df, expected):
    assert t_ppf(prob, df) == pytest.approx(expected, abs=1e-3)


def test_shift_at_matches_the_searched_split():
    rng = np.random.default_rng(1)
    n = np.full(12, 20.0)
    means = np.r_[np.full(6, 0.4), np.full(6, -0.2)]
    values = [np.clip(rng.normal(m, 0.5, 20), -1, 1) for m in means]
    s = np.array([v.sum() for v in values])
    ss = np.array([(v ** 2).sum() for v in values])
    cp = find_changepoint(n, s, ss)
    shift = shift_at(n, s, ss, split=cp.index)
    assert shift.delta == pytest.approx(cp.delta)
    # The searched split pays a Bonferroni price; the pre-specified one does not.
    assert shift.p_value <= cp.p_value


def test_shift_at_rejects_empty_segments():
    n, s = np.array([5.0, 5.0]), np.array([1.0, 2.0])
    assert shift_at(n, s, s, split=0) is None
    assert shift_at(n, s, s, split=2) is None


# --- verdicts on simulated clusters ---------------------------------------------------


def test_a_real_fix_is_found_with_the_right_size():
    r = _check(_cluster(step(0.3, 0.8, "2025-06")))  # mean -0.4 -> +0.6: true effect +1.0
    assert r["verdict"] == "improved"
    assert r["ci_low"] <= 1.0 <= r["ci_high"]
    assert r["basis"] == "market"
    assert r["placebo_rank"] == 1 and r["n_placebo"] == len(OTHERS)
    assert r["detected_start"] == "2025-06"
    assert "Caution" not in r["summary"]


def test_a_market_wide_change_is_not_credited_to_the_property():
    """The headline behaviour: everyone improved, so the naive before/after says
    'improved' while the market-adjusted check does not."""
    everyone = step(0.4, 0.7, "2025-06")
    r = _check(_cluster(everyone, other_p=everyone))
    assert r["naive_delta"] > 0.4
    assert r["market_delta"] > 0.4
    assert r["verdict"] == "no detectable change"
    assert abs(r["effect"]) < r["mde"]


def test_rarely_a_verdict_when_nothing_changed():
    verdicts = [_check(_cluster(constant(0.6), seed=s))["verdict"] for s in range(30)]
    false = sum(v != "no detectable change" for v in verdicts)
    assert false <= 4  # nominal 5%; 100 seeds gave 6/100 (methodology section 12)


def test_a_fix_after_a_decline_is_compared_with_the_declined_level():
    def dip_then_fix(month):
        if month < pd.Timestamp("2025-01"):
            return 0.7
        return 0.2 if month < pd.Timestamp("2025-06") else 0.7

    r = _check(_cluster(dip_then_fix))
    assert r["baseline_start"] == "2025-01"
    assert r["verdict"] == "improved"
    # Against the whole history the same recovery looks like almost nothing.
    whole = _check(_cluster(dip_then_fix), baseline_start="2024-01")
    assert whole["effect"] < r["effect"] - 0.5


def test_a_change_that_began_before_the_fix_is_flagged():
    # Too close to the stated month for the baseline to absorb (< 4 months).
    r = _check(_cluster(step(0.8, 0.2, "2025-06")), start="2025-08")
    assert r["verdict"] == "worsened"
    assert r["detected_start"] == "2025-06"
    assert "Caution" in r["summary"]


def test_an_older_change_becomes_the_baseline():
    r = _check(_cluster(step(0.8, 0.2, "2025-03")), start="2025-08")
    assert r["baseline_start"] == "2025-03"
    assert r["verdict"] == "no detectable change"


def test_too_early_to_tell_with_few_reviews_after():
    r = _check(_cluster(constant(0.6), per_month=5), start="2025-12")
    assert r["verdict"] == "too early to tell"
    assert r["n_after"] < 10
    assert r["effect"] is None


def test_without_a_market_it_is_a_plain_before_after():
    r = _check(_cluster(step(0.3, 0.8, "2025-06"), others=["P1"]))
    assert r["basis"] == "own history"
    assert r["market_delta"] is None and r["placebo_rank"] is None
    assert r["effect"] == r["naive_delta"]
    assert "Too few properties" in r["summary"]


def test_no_data_cases():
    labelled = _cluster(constant(0.6))
    assert _check(labelled.assign(aspect="Room"))["verdict"] == "no data"
    r = _check(labelled, start="2024-01")  # nothing before the first month
    assert r["verdict"] == "no data"


def test_invalid_months_raise():
    labelled = _cluster(constant(0.6))
    with pytest.raises(ValueError, match="Not a date"):
        _check(labelled, start="soon")
    with pytest.raises(ValueError, match="before start"):
        _check(labelled, start="2025-06", baseline_start="2025-06")


# --- end to end on the SYNTHETIC sample -----------------------------------------------


@pytest.fixture(scope="module")
def sample():
    return label_reviews(generate(seed=42))


def test_sample_food_decline_at_property_f(sample):
    r = evaluate_intervention(sample, "Property F", "Food", "2025-06")
    assert r["verdict"] == "worsened"
    assert r["placebo_rank"] == 1


def test_sample_december_room_dip_is_the_market_not_the_property(sample):
    r = evaluate_intervention(sample, "Property A", "Room", "2025-12")
    assert r["naive_delta"] < -1.0  # a plain before/after looks alarming
    assert r["verdict"] == "no detectable change"  # but the whole market dipped


def test_demo_numbers(sample):
    """docs/DEMO.md quotes these (Property A, Room, December 2025)."""
    r = evaluate_intervention(sample, "Property A", "Room", "2025-12")
    assert (r["naive_delta"], r["market_delta"], r["effect"]) == pytest.approx(
        (-1.38, -0.95, -0.43), abs=0.005
    )
