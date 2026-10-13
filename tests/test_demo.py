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


def test_four_neighbours_share_a_location_decline(d):
    hood = api.neighbourhoods(d).iloc[0]
    assert (hood["aspect"], hood["change_month"], hood["radius_km"], hood["p_value"]) == (
        "Location", "2025-03", 0.27, 0.018
    )
    assert hood["members"] == "Property B, Property C, Property E, Property H"
    top = api.priority_actions(d, "Property B").iloc[0]
    assert (top["aspect"], top["started"], top["whose_problem"]) == (
        "Location", "2025-03", "your neighbourhood's"
    )
    # Only one of the four declines visibly on its own.
    own = api.changepoints(d, aspect="Location")
    assert list(own["property_id"]) == ["Property C"]


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
