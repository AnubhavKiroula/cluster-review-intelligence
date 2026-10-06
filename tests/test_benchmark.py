"""End-to-end: the analysis must recover the injected ground-truth patterns.

Recovery is reported honestly: we assert the injected patterns are found and are
the dominant signals, not that the simple detectors are free of false positives.
"""

import pytest

from cri.benchmark import (
    benchmark_vs_cluster,
    detect_changepoints,
    detect_seasonal_dips,
    market_wide_summary,
)
from cri.generate import generate
from cri.pipeline import label_reviews


@pytest.fixture(scope="module")
def labelled():
    return label_reviews(generate(seed=42))


def test_recovers_property_f_food_changepoint(labelled):
    cps = detect_changepoints(labelled)
    pf = cps[(cps["property_id"] == "Property F") & (cps["aspect"] == "Food")]
    assert len(pf) == 1
    row = pf.iloc[0]
    assert row["change_month"] == "2025-06"
    assert row["direction"] == "negative"


def test_food_decline_is_strongest_negative_shift(labelled):
    cps = detect_changepoints(labelled)
    negatives = cps[cps["direction"] == "negative"]
    strongest = negatives.loc[negatives["delta"].idxmin()]
    assert strongest["property_id"] == "Property F"
    assert strongest["aspect"] == "Food"


def test_december_heating_is_market_wide(labelled):
    summary = market_wide_summary(labelled)
    room = summary[summary["aspect"] == "Room"]
    assert len(room) == 1
    assert room.iloc[0]["scope"] == "market-wide"


def test_food_decline_is_property_specific(labelled):
    summary = market_wide_summary(labelled)
    food = summary[summary["aspect"] == "Food"]
    assert len(food) == 1
    assert food.iloc[0]["scope"] == "property-specific"
    assert "Property F" in food.iloc[0]["properties"]


def test_december_room_dip_affects_majority(labelled):
    dips = detect_seasonal_dips(labelled)
    room_props = dips[dips["aspect"] == "Room"]["property_id"].nunique()
    total = labelled["property_id"].nunique()
    assert room_props / total >= 0.6


def test_benchmark_flags_property_f_food_as_lagging(labelled):
    bench = benchmark_vs_cluster(labelled)
    row = bench[
        (bench["property_id"] == "Property F") & (bench["aspect"] == "Food")
    ].iloc[0]
    assert row["flag"] == "lag"
