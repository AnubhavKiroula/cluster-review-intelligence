"""Travel layer: resources, demand index, alternatives, stays, sellers, planner.

The demand index and recommendations are heuristics on SYNTHETIC profiles, so these
tests pin *invariants* (sums, monotonicity, guards, provenance labels) rather than
accuracy, which cannot be measured without real footfall data (docs/AI_MODEL.md).
"""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date

import pytest

from cri import api
from cri.generate import PROPERTIES
from cri.travel import alternatives as alt
from cri.travel import demand as dm
from cri.travel import planner, region, stays
from cri.travel.data import (
    BASES,
    Evidence,
    UnknownIdError,
    _read,
    build,
    load_travel_data,
)


@pytest.fixture(scope="module")
def td():
    return load_travel_data()


@pytest.fixture(scope="module")
def cluster():
    return api.load_cluster(synthetic=True)


# --- resources ----------------------------------------------------------------------------


def test_facts_are_sourced_and_synthetic_is_labelled(td):
    assert td.holidays and all(h.source in td.sources for h in td.holidays)
    assert all(f.source in td.sources for f in td.emission_factors.values())
    assert all(url.startswith("https://") for url in (s.url for s in td.sources.values()))
    raw = _read("travel_synthetic.yaml")
    assert raw["label"] == "SYNTHETIC"
    bad = copy.deepcopy(raw)
    bad.pop("label")
    with pytest.raises(ValueError, match="SYNTHETIC"):
        build(_read("travel_facts.yaml"), bad)


def test_holiday_weekday_mismatch_is_rejected():
    facts = copy.deepcopy(_read("travel_facts.yaml"))
    facts["holidays"]["items"][0]["weekday"] = "Friday"  # 2026-01-26 is a Monday
    with pytest.raises(ValueError, match="listed as Friday"):
        build(facts, _read("travel_synthetic.yaml"))


def test_every_synthetic_property_has_exactly_one_stay(td):
    assert sorted(td.stays) == sorted(PROPERTIES)
    belt = {s.destination for s in td.stays.values()}
    assert all(td.destinations[d].belt for d in belt)


def test_official_distance_wins_and_estimates_say_so(td):
    official = td.road_km("delhi", "shimla")
    assert (official.value, official.basis) == (370, "fact")
    estimate = td.road_km("delhi", "kanatal")
    assert estimate.basis == "derived" and "straight line" in estimate.detail
    assert 1.0 < td.road_factor < 3.0


def test_evidence_rejects_unknown_basis():
    with pytest.raises(ValueError):
        Evidence("x", 1, "guess")
    assert "fact" in BASES


# --- demand -------------------------------------------------------------------------------


def test_index_equals_sum_of_factors_and_is_bounded(td):
    for dest in td.destinations:
        for d in dm.demand_calendar(td, dest, date(2026, 12, 20), 21):
            assert 0 <= d.index <= 100
            assert d.index == sum(int(e.value) for e in d.factors)
            assert all(e.basis in BASES for e in d.factors)


def test_christmas_2026_is_a_long_weekend_and_dussehra_is_not(td):
    xmas = dm.demand_calendar(td, "mussoorie", date(2026, 12, 25), 3)  # Fri-Sun
    assert all(any(e.label == "Long weekend" for e in d.factors) for d in xmas)
    dussehra = dm.demand_calendar(td, "mussoorie", date(2026, 10, 20), 1)[0]  # Tuesday
    labels = {e.label for e in dussehra.factors}
    assert "Gazetted holiday" in labels and "Long weekend" not in labels


def test_adding_a_holiday_never_lowers_demand():
    facts, syn = _read("travel_facts.yaml"), _read("travel_synthetic.yaml")
    base = build(facts, syn)
    more = copy.deepcopy(facts)
    more["holidays"]["items"].append(
        {"date": date(2026, 11, 16), "weekday": "Monday", "name": "Test holiday",
         "source": "holidays_2026_uk"})
    extra = build(more, syn)
    a = dm.demand_calendar(base, "nainital", date(2026, 11, 10), 14)
    b = dm.demand_calendar(extra, "nainital", date(2026, 11, 10), 14)
    assert all(y.index >= x.index for x, y in zip(a, b, strict=True))
    assert sum(y.index for y in b) > sum(x.index for x in a)


def test_beyond_coverage_has_no_holiday_points_and_says_so(td):
    day = dm.demand_calendar(td, "shimla", date(2028, 1, 26), 1)[0]  # Republic Day 2028
    assert not any(e.label == "Gazetted holiday" for e in day.factors)
    assert any("No holiday data" in n for n in day.notes)


def test_quieter_dates_are_quieter_and_within_window(td):
    base = dm.trip_demand(td, "mussoorie", date(2026, 12, 25), 2)
    options = dm.quieter_dates(td, "mussoorie", date(2026, 12, 25), 2)
    assert options
    for o in options:
        assert abs(o.offset_days) <= td.demand["quieter_window"]
        assert base.mean_index - o.mean_index >= td.demand["quieter_min_drop"]


def test_a_custom_demand_model_is_used(td):
    class Flat:
        name, version = "flat", "0"

        def predict(self, td, dest, days):
            return [dm.DemandDay(d, 50, "Moderate", False, (), ()) for d in days]

    cal = dm.demand_calendar(td, "manali", date(2026, 12, 25), 3, model=Flat())
    assert {d.index for d in cal} == {50}


def test_days_are_validated(td):
    with pytest.raises(ValueError):
        dm.demand_calendar(td, "manali", date(2026, 12, 25), 0)
    with pytest.raises(UnknownIdError):
        dm.demand_calendar(td, "atlantis", date(2026, 12, 25), 3)


# --- alternatives --------------------------------------------------------------------------


def test_alternatives_exclude_origin_and_respect_the_capacity_guard(td):
    res = alt.find_alternatives(td, "mussoorie", date(2026, 12, 25), 2, top_n=10)
    assert res.alternatives
    for a in res.alternatives:
        assert a.destination != "mussoorie"
        assert res.origin_demand.mean_index - a.mean_index >= 100 * alt.MIN_RELIEF
        assert a.mean_index < alt.CEILING[td.destinations[a.destination].sensitivity]
        assert set(a.explanation) == {"why_origin_busy", "why_similar", "expected_crowd",
                                      "trade_off", "limitations"}
        assert all(a.explanation.values())
    assert any("capacity guard" in reason for _, reason in res.excluded)


def test_weights_change_the_ranking(td):
    args = (td, "mussoorie", date(2026, 12, 25), 2)
    default = [a.destination for a in alt.find_alternatives(*args, top_n=10).alternatives]
    travel = alt.Weights(landscape=0, activities=0, budget=0, travel=1, season=0)
    by_travel = [a.destination for a in alt.find_alternatives(*args, weights=travel,
                                                              top_n=10).alternatives]
    assert sorted(default) == sorted(by_travel) and default != by_travel


# --- stays + provider insights -------------------------------------------------------------


def test_stay_profiles_have_no_star_rating(td, cluster):
    profiles = stays.stay_profiles(cluster, td)
    assert len(profiles) == len(PROPERTIES)
    text = repr(profiles).lower()
    assert "star" not in text and "'rating'" not in text
    assert "verified" in stays.PROFILE_NOTE.lower()
    for p in profiles:
        assert {f["aspect"] for f in p["feedback"]} == set(api.list_aspects())
        assert all(x["status"] in ("reported", "not reported") for x in p["practices"])


def test_heating_insight_matches_review_search(td, cluster):
    insights = stays.provider_insights(cluster, td, "Property J", date(2026, 10, 13), 90)
    gap = next(i for i in insights if i.kind == "amenity_gap" and "room heating" in i.title)
    neg = api.search_reviews(cluster, property_id="Property J", sentiment=-1)
    expected = neg[neg["sentence"].str.contains("heater|heating|हीटर", regex=True)][
        "review_id"].nunique()
    assert gap.evidence[0].value == expected
    assert "market-wide" in gap.why  # December Room complaints hit every property
    assert all(i.why for i in insights)


def test_property_f_food_decline_is_the_first_priority(td, cluster):
    first = stays.provider_insights(cluster, td, "Property F", date(2026, 10, 13), 90)[0]
    assert first.kind == "review_priority" and first.title == "Fix Food first since 2025-06"


# --- sellers + region ----------------------------------------------------------------------


def test_sellers_exclude_restaurants_and_are_unverified(td):
    assert "restaurants" not in td.seller_categories
    assert all(s.verification == "unverified (SYNTHETIC)" for s in td.sellers)
    with pytest.raises(ValueError):
        region.sellers_for(td, category="restaurants")


def test_seller_opportunity_is_labelled_not_sales(td):
    rows = region.seller_opportunities(td, "kanatal", date(2026, 12, 1), 30)
    assert rows == sorted(rows, key=lambda r: -r["score"])
    assert all("not sales" in r["evidence"].detail for r in rows)


def test_region_dashboard_covers_every_destination(td, cluster):
    view = region.region_dashboard(cluster, td, date(2026, 12, 15), 30)
    assert {p["destination"] for p in view["pressure"]} == set(td.destinations)
    assert view["review_issues"] and any("not live traffic" in n for n in view["notes"])


# --- planner -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def plan(td, cluster):
    req = planner.PlanInput(origin="delhi", destination="mussoorie", start=date(2026, 12, 25),
                            nights=2, travellers=4, budget=40000, interests=("nature",),
                            stay_pref="family", transport="car")
    return planner.plan_trip(cluster, td, req)


def test_plan_lines_add_up(plan):
    assert plan.total == sum(int(e.value) for e in plan.costs)
    assert plan.per_person == round(plan.total / 4)
    assert plan.within_budget == (plan.total <= 40000)
    assert len(plan.itinerary) == 3 and plan.stay["category"] == "family"


def test_plan_carbon_uses_the_sourced_factors(td, plan):
    km = td.road_km("delhi", "mussoorie").value
    car = next(e for e in plan.carbon if "car" in e.label)
    bus = next(e for e in plan.carbon if "bus" in e.label)
    assert car.value == round(2 * km * td.emission_factors["car"].value * 1, 1)
    assert bus.value == round(2 * km * td.emission_factors["bus"].value * 4, 1)


def test_plan_variants_are_cheaper_or_quieter(plan):
    by_label = {v["label"]: v for v in plan.variants}
    assert by_label["Lower budget"]["delta_cost"] < 0
    assert by_label["Lower crowd"]["delta_index"] < 0


def test_plan_input_is_validated(td, cluster, plan):
    for bad in ({"nights": 0}, {"travellers": 13}, {"budget": 0}, {"transport": "rocket"},
                {"interests": ("skydiving",)}):
        with pytest.raises(ValueError):
            planner.plan_trip(cluster, td, replace(plan.request, **bad))
