"""The calibration harness must reproduce the documented SYNTHETIC recovery rates.

Uses two seeds to stay fast; `python -m cri.calibration --seeds 1-20` runs the
full measurement quoted in docs/methodology.md.
"""

import pytest

from cri.calibration import _parse_seeds, calibrate, wilson_interval


def test_calibration_recovers_patterns_and_stays_quiet_on_null_data():
    per_seed, summary = calibrate([1, 11])
    assert per_seed["food_decline_found"].all()
    assert per_seed["room_december_market_wide"].all()
    assert per_seed["food_property_specific"].all()
    assert (per_seed["null_changepoints"] == 0).all()
    assert (per_seed["null_market_patterns"] == 0).all()
    assert summary["food_decline_found"]["k"] == 2


def test_wilson_interval_known_value():
    lo, hi = wilson_interval(6, 10)  # 0.6 with n=10 -> about 0.31-0.83
    assert lo == pytest.approx(0.313, abs=0.002)
    assert hi == pytest.approx(0.832, abs=0.002)
    assert wilson_interval(0, 0) != wilson_interval(0, 0)  # NaNs


def test_seed_parsing():
    assert _parse_seeds("1-3,7") == [1, 2, 3, 7]
