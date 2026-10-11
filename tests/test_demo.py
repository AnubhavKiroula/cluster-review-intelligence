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


def test_property_f_fix_food_first_since_june(d):
    top = api.priority_actions(d, "Property F").iloc[0]
    assert (top["aspect"], top["started"]) == ("Food", "2025-06")


def test_same_chart_two_different_actions(d):
    scope = api.market_scope(d).set_index("aspect")
    assert scope.loc["Food", "scope"] == "property-specific"
    assert scope.loc["Food", "properties"] == "Property F"
    assert scope.loc["Room", "scope"] == "market-wide"
    assert "December" in scope.loc["Room", "pattern"]


EXPECTED_LIVE = {
    "Khana accha tha lekin kamra ganda tha.":
        [("Food", 1), ("Room", -1), ("Cleanliness", -1)],
    "Khaana bahut swadisht tha but room thanda tha.": [("Food", 1), ("Room", -1)],
    "कमरा साफ़ था और view zabardast tha.":
        [("Room", 1), ("Location", 1), ("Cleanliness", 1)],
    "Heater kaam nahi kar raha tha, raat bhar thand lagi.": [("Room", -1)],
    "Staff bahut helpful tha, paisa vasool.": [("Staff", 1), ("Value for Money", 1)],
}


@pytest.mark.parametrize("text", LIVE_EXAMPLES)
def test_live_examples_classify_as_rehearsed(text):
    found = api.classify_text(text)
    assert list(zip(found["aspect"], found["sentiment"], strict=True)) == EXPECTED_LIVE[text]
