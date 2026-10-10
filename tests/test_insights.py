"""priority_actions ("fix this first") and the destination view."""

import pytest

from cri.generate import generate
from cri.insights import (
    DESTINATION_COLUMNS,
    PRIORITY_COLUMNS,
    destination_summary,
    priority_actions,
)
from cri.pipeline import label_reviews


@pytest.fixture(scope="module")
def labelled():
    return label_reviews(generate(seed=42))


def test_property_f_should_fix_food_first(labelled):
    pa = priority_actions(labelled, "Property F")
    assert list(pa.columns) == PRIORITY_COLUMNS
    top = pa.iloc[0]
    assert top["aspect"] == "Food"
    assert top["started"] == "2025-06"
    assert top["gap"] > 0.5
    assert top["basis"] == "cluster"
    # the gap is measured on the same months for both sides
    assert top["gap"] == pytest.approx(top["reference_mean"] - top["current_mean"], abs=1e-3)
    assert "2025-06" in top["rationale"] and "Food" in top["rationale"]
    assert "relative to the market" in top["rationale"]


def test_ranking_is_by_impact_and_every_row_is_behind(labelled):
    pa = priority_actions(labelled, "Property D")
    assert len(pa) >= 2
    assert pa["impact_score"].is_monotonic_decreasing
    assert (pa["gap"] > 0).all()
    assert pa["impact_score"].to_numpy() == pytest.approx(
        (pa["gap"] * pa["volume"]).to_numpy(), abs=1e-3
    )


def test_top_n_limits_rows(labelled):
    assert len(priority_actions(labelled, "Property D", top_n=2)) == 2


def test_a_property_with_no_supported_gaps_gets_an_empty_list(labelled):
    pa = priority_actions(labelled, "Property L")  # the strongest property
    assert pa.empty
    assert list(pa.columns) == PRIORITY_COLUMNS


def test_unknown_property_gives_empty_frame(labelled):
    assert priority_actions(labelled, "Property Z").empty


def test_missing_started_is_none_not_nan():
    lab = label_reviews(generate(seed=2))  # F has a decline AND an overall lag here
    pa = priority_actions(lab, "Property F", top_n=8)
    assert pa["started"].notna().any() and pa["started"].isna().any()
    assert all(v is None for v in pa["started"] if not isinstance(v, str))


def test_two_property_cluster_does_not_claim_a_market_comparison(labelled):
    two = labelled[labelled["property_id"].isin(["Property A", "Property F"])]
    top = priority_actions(two, "Property F").iloc[0]
    assert top["aspect"] == "Food" and top["basis"] == "own history"
    assert "relative to the market" not in top["rationale"]
    assert "too few properties" in top["rationale"]


def test_single_property_upload_still_gets_its_own_declines(labelled):
    one = labelled[labelled["property_id"] == "Property F"]
    pa = priority_actions(one, "Property F")
    assert len(pa) >= 1
    top = pa.iloc[0]
    assert top["aspect"] == "Food" and top["started"] == "2025-06"
    assert top["basis"] == "own history" and top["gap"] > 0.5


def test_destination_summary_labels_each_aspect(labelled):
    ds = destination_summary(labelled).set_index("aspect")
    assert list(destination_summary(labelled).columns) == DESTINATION_COLUMNS
    assert len(ds) == labelled["aspect"].nunique()
    assert ds.at["Room", "scope"] == "market-wide"
    assert "December" in ds.at["Room", "pattern"]
    assert ds.at["Food", "scope"] == "property-specific"
    assert set(ds["scope"]) <= {"market-wide", "property-specific", "stable"}
    assert (ds["n_properties_reviewed"] == 12).all()
    assert ((ds["pct_negative"] >= 0) & (ds["pct_negative"] <= 1)).all()


def test_destination_summary_is_worst_first(labelled):
    assert destination_summary(labelled)["cluster_mean"].is_monotonic_increasing


def test_destination_summary_small_cluster_is_undetermined(labelled):
    two = labelled[labelled["property_id"].isin(["Property A", "Property B"])]
    assert (destination_summary(two)["scope"] == "undetermined").all()
