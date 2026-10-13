"""Every claim in docs/DEMO.md must stay true for the SYNTHETIC sample.

If a lexicon/aspect edit or a detector change breaks a line the presenter will say
or type live, this fails in CI instead of on stage. Numbers come from
``python scripts/demo.py``.
"""

import pytest
from scripts.demo import LIVE_EXAMPLES

from cri import api


@pytest.fixture(scope="module")
def d():
    return api.load_cluster()


def test_hook_two_near_identical_star_averages(d):
    stars = d.reviews.groupby("property_id")["rating"].mean().round(2)
    assert (stars["Property F"], stars["Property I"]) == (3.28, 3.33)
    assert api.priority_actions(d, "Property I").empty  # nothing flagged


def test_property_f_fix_food_first_since_june_and_it_is_theirs_alone(d):
    top = api.priority_actions(d, "Property F").iloc[0]
    assert (top["aspect"], top["started"], round(top["gap"], 2)) == ("Food", "2025-06", 1.05)
    assert top["whose_problem"] == "yours alone"
    assert top["whose_detail"] == (
        "you dropped 1.22 relative to the market from 2025-06; "
        "the market itself moved +0.01"
    )


def test_property_d_room_gap_is_its_own_despite_the_december_dip(d):
    room = api.priority_actions(d, "Property D").set_index("aspect").loc["Room"]
    assert room["whose_problem"] == "yours alone"
    assert room["whose_detail"].startswith("still 0.36 below the market outside December")


def test_same_chart_two_different_actions(d):
    scope = api.market_scope(d).set_index("aspect")
    assert scope.loc["Food", "scope"] == "property-specific"
    assert scope.loc["Food", "properties"] == "Property F"
    assert scope.loc["Room", "scope"] == "market-wide"
    assert "December (12/12 properties" in scope.loc["Room", "pattern"]


EXPECTED_LIVE = {
    "Khana accha tha lekin kamra ganda tha.":
        [("Food", 1), ("Room", -1), ("Cleanliness", -1)],
    "Khaana bahut swadisht tha but room thanda tha.": [("Food", 1), ("Room", -1)],
    "कमरा साफ़ था और view zabardast tha.":
        [("Room", 1), ("Location", 1), ("Cleanliness", 1)],
    "Heater kaam nahi kar raha tha, raat bhar thand lagi.": [("Room", -1)],
    "Staff bahut helpful tha, paisa vasool.": [("Staff", 1), ("Value for Money", 1)],
    "Khaana accha nahi tha.": [("Food", -1)],
}


@pytest.mark.parametrize("text", LIVE_EXAMPLES)
def test_live_examples_classify_as_rehearsed(text):
    found = api.classify_text(text)
    assert list(zip(found["aspect"], found["sentiment"], strict=True)) == EXPECTED_LIVE[text]


# --- The REAL cluster (pinned against the committed snapshot the site serves) ---------

from scripts.demo import load_real  # noqa: E402


@pytest.fixture(scope="module")
def real():
    return load_real()


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_real_snapshot_is_kausani_aggregates_without_text_or_dates(real):
    meta, prov = real["meta"], real["meta"]["provenance"]
    assert not meta["is_synthetic"] and not meta["has_dates"]
    assert (prov["town"], prov["hotels"], meta["n_reviews"]) == ("Kausani", 25, 2751)
    assert (prov["hotels_in_town"], prov["reviews_in_town"]) == (41, 2877)
    assert prov["median_reviews_per_hotel"] == 66
    # Real review text is never published: no text-bearing fields anywhere.
    assert not {"reviews", "mentions", "text", "sentence", "review"} & set(_keys(real))
    assert all(p.startswith("Property ") for p in real["per_property"])


def test_real_hook_two_similar_star_averages(real):
    i, y = real["per_property"]["Property I"], real["per_property"]["Property Y"]
    assert (i["stars"]["mean"], y["stars"]["mean"]) == (3.44, 3.49)
    assert i["priority_actions"] == []
    rows = [(r["aspect"], round(r["gap"], 2), r["whose_problem"]) for r in y["priority_actions"]]
    assert rows == [("Room", 0.42, "yours alone"), ("Cleanliness", 0.68, "yours alone")]
    assert all(r["started"] is None for r in y["priority_actions"])  # no dates in the source


def test_real_market_has_no_shared_weak_spot(real):
    assert real["market_headline"] is None
    scope = {r["aspect"]: r for r in real["market_scope"]}
    assert {r["scope"] for r in scope.values()} == {"property-specific"}
    assert scope["Room"]["properties"] == "Property M, Property O, Property U, Property Y"
    flagged = [p for p, v in real["per_property"].items() if v["priority_actions"]]
    assert len(flagged) == 7
    top = sorted(real["destination_summary"], key=lambda r: -r["pct_negative"])[:3]
    assert [(r["aspect"], round(r["pct_negative"] * 100)) for r in top] == [
        ("Housekeeping", 14), ("Cleanliness", 9), ("Value for Money", 8)]
