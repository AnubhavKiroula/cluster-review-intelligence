"""Statistics toolkit: Student-t tail, Benjamini-Hochberg, and the split search."""

import math

import numpy as np
import pytest

from cri.changepoint import bh_qvalues, find_changepoint, t_sf


@pytest.mark.parametrize(
    ("t", "df", "upper_tail"),
    [
        (2.228, 10, 0.025),  # textbook two-sided 5% critical values
        (2.571, 5, 0.025),
        (12.706, 1, 0.025),
        (4.032, 5, 0.005),  # two-sided 1%
        (3.169, 10, 0.005),
        (1.96, 1e6, 0.025),  # converges to the normal
    ],
)
def test_t_sf_matches_critical_values(t, df, upper_tail):
    assert t_sf(t, df) == pytest.approx(upper_tail, abs=2e-5)


def test_t_sf_symmetry_and_edges():
    assert t_sf(0.0, 7) == pytest.approx(0.5)
    assert t_sf(-2.228, 10) == pytest.approx(1 - t_sf(2.228, 10))
    assert t_sf(math.inf, 3) == 0.0
    assert math.isnan(t_sf(1.0, 0))


def test_bh_qvalues_hand_example():
    # sorted p: .005 .01 .03 .04 -> p*m/rank = .02 .02 .04 .04 (then monotone)
    q = bh_qvalues([0.01, 0.04, 0.03, 0.005])
    assert q == pytest.approx([0.02, 0.04, 0.04, 0.02])
    assert len(bh_qvalues([])) == 0


def _monthly(months):
    n = np.array([len(m) for m in months], dtype=float)
    s = np.array([np.sum(m) for m in months], dtype=float)
    ss = np.array([np.sum(np.square(m)) for m in months], dtype=float)
    return n, s, ss


def test_finds_a_real_step_at_the_right_month():
    rng = np.random.default_rng(0)
    before = [rng.choice([-1, 1], size=6, p=[0.2, 0.8]) for _ in range(16)]
    after = [rng.choice([-1, 1], size=6, p=[0.85, 0.15]) for _ in range(8)]
    cp = find_changepoint(*_monthly(before + after))
    assert cp is not None
    assert cp.index == 16
    assert cp.delta < -1.0
    assert cp.p_value < 1e-6


def test_flat_series_is_not_significant():
    rng = np.random.default_rng(1)
    flat = [rng.choice([-1, 1], size=6, p=[0.4, 0.6]) for _ in range(24)]
    cp = find_changepoint(*_monthly(flat))
    assert cp is not None and cp.p_value > 0.05


def test_too_short_or_too_sparse_returns_none():
    assert find_changepoint(*_monthly([[1, -1]] * 7)) is None  # < 2 x min_months
    assert find_changepoint(*_monthly([[1]] * 10)) is None  # < min_units per side


def test_zero_variance_step_is_handled():
    cp = find_changepoint(*_monthly([[1] * 6] * 6 + [[-1] * 6] * 6))
    assert cp.index == 6
    assert cp.delta == pytest.approx(-2.0)
    assert cp.p_value == 0.0


def test_delta_vs_market_differs_from_raw_delta():
    # Property goes +1 -> -1 (raw shift -2) while the market goes 0 -> -1, so the
    # shift relative to the market is only -1.
    raw = [[1] * 6] * 6 + [[-1] * 6] * 6
    market = np.array([0.0] * 6 + [-1.0] * 6)
    n, s, _ = _monthly(raw)
    resid = [np.array(m, dtype=float) - mk for m, mk in zip(raw, market, strict=True)]
    _, rs, rss = _monthly(resid)
    cp = find_changepoint(n, rs, rss, raw_s=s)
    assert cp.index == 6
    assert cp.delta == pytest.approx(-1.0)
    assert cp.raw_delta == pytest.approx(-2.0)
