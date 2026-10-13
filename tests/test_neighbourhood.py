"""The neighbourhood scan: finds a decline shared by nearby properties, and does not
mistake one property, a scattered set, or the whole market for a neighbourhood."""

import numpy as np
import pandas as pd
import pytest

from cri import api
from cri import generate as gen
from cri.generate import PROPERTIES, ROAD_WORKS_PROPERTIES, generate_locations
from cri.insights import _whose_problem, priority_actions
from cri.neighbourhood import NEIGHBOURHOOD_COLUMNS, detect_neighbourhoods, neighbourhood_findings
from sim_helpers import constant, simulate, step

NEIGHBOURS = list(ROAD_WORKS_PROPERTIES)
PERMS = 99  # enough to resolve p <= 0.05 in tests; the default is larger


def _cluster(declining, seed=0):
    base = np.random.default_rng(10_000 + seed).uniform(0.45, 0.85, size=len(PROPERTIES))
    spec = {
        p: step(b, 0.15, "2025-03") if p in declining else constant(b)
        for p, b in zip(PROPERTIES, base, strict=True)
    }
    return simulate(spec, aspect="Location", per_month=3, seed=seed)


def test_clustered_decline_is_found_with_its_members_and_month():
    found = neighbourhood_findings(
        _cluster(NEIGHBOURS), generate_locations(0), permutations=PERMS
    )
    assert len(found) == 1
    f = found[0]
    assert (f["aspect"], f["members"]) == ("Location", sorted(NEIGHBOURS))
    # The month is estimated from 3 reviews per property-month: within one month.
    assert f["change_month"] in {"2025-02", "2025-03", "2025-04"}
    assert f["p_value"] <= 0.05 and f["delta"] < 0
    assert all(gap < 0 for gap in f["gaps"].values())
    assert f["radius_km"] <= gen.NEIGHBOURHOOD_RADIUS_KM


@pytest.mark.parametrize(
    "declining, clustered",
    [
        (NEIGHBOURS, False),  # the same four, scattered over the town
        (NEIGHBOURS[:1], True),  # one property, inside the neighbourhood
        ([], True),  # nothing happens
    ],
)
def test_no_neighbourhood_without_a_spatially_shared_decline(declining, clustered):
    found = neighbourhood_findings(
        _cluster(declining), generate_locations(0, neighbourhood=clustered), permutations=PERMS
    )
    assert found == []


def test_without_positions_or_with_too_few_nothing_is_tested():
    labelled = _cluster(NEIGHBOURS)
    assert neighbourhood_findings(labelled, None) == []
    few = generate_locations(0).head(5)  # half of 5 is below the 3-property minimum
    assert neighbourhood_findings(labelled, few, permutations=PERMS) == []
    empty = detect_neighbourhoods(labelled, None)
    assert empty.empty and list(empty.columns) == NEIGHBOURHOOD_COLUMNS


def test_same_seed_same_result():
    labelled, loc = _cluster(NEIGHBOURS, seed=3), generate_locations(3)
    a = neighbourhood_findings(labelled, loc, permutations=PERMS, seed=7)
    b = neighbourhood_findings(labelled, loc, permutations=PERMS, seed=7)
    assert a == b


def test_members_are_told_it_is_their_neighbourhoods():
    labelled = _cluster(NEIGHBOURS)
    found = neighbourhood_findings(labelled, generate_locations(0), permutations=PERMS)
    row = priority_actions(labelled, NEIGHBOURS[0], neighbourhoods=found).set_index("aspect")
    assert row.loc["Location", "whose_problem"] == "your neighbourhood's"
    assert row.loc["Location", "started"] == "2025-03"
    detail = row.loc["Location", "whose_detail"]
    assert all(n in detail for n in NEIGHBOURS[1:]) and "p = " in detail
    outsider = priority_actions(labelled, "Property A", neighbourhoods=found)
    assert "your neighbourhood's" not in set(outsider["whose_problem"])


def test_a_market_wide_pattern_takes_precedence():
    labelled = _cluster(NEIGHBOURS)
    hood = {"aspect": "Location", "members": NEIGHBOURS, "gaps": dict.fromkeys(NEIGHBOURS, -0.5),
            "change_month": "2025-03", "delta": -0.5, "radius_km": 0.3, "p_value": 0.01}
    market = {"aspect": "Location", "kind": "step", "change_month": "2025-03",
              "calendar_month": None, "drop": 0.5, "coverage": 12, "n_tested": 12,
              "gaps": dict.fromkeys(PROPERTIES, 0.5), "p_value": 0.001, "q_value": 0.001}
    near = {"Location": hood}
    whose, _ = _whose_problem(labelled, NEIGHBOURS[0], "Location", None, [market], near)
    assert whose != "your neighbourhood's"
    whose, _ = _whose_problem(labelled, NEIGHBOURS[0], "Location", None, [], near)
    assert whose == "your neighbourhood's"


def test_location_templates_keep_the_random_stream_aligned():
    # Changing a Location polarity must consume the generator's random stream
    # identically, or every later synthetic review (and the demo numbers) would move.
    pos, neg = gen.TEMPLATES[("Location", "pos")], gen.TEMPLATES[("Location", "neg")]
    assert len(pos) == len(neg)
    assert [lang for lang, _ in pos] == [lang for lang, _ in neg]


def test_road_works_changes_only_the_neighbours_location_reviews(monkeypatch):
    with_works = gen.generate(seed=42)
    monkeypatch.setattr(gen, "ROAD_WORKS_PROPERTIES", ())
    without = gen.generate(seed=42)
    changed = (with_works != without).any(axis=1)
    rows = with_works[changed]
    assert set(rows["property_id"]) <= set(NEIGHBOURS)
    assert (pd.to_datetime(rows["date"]) >= gen.ROAD_WORKS_MONTH).all()
    assert rows["text"].str.contains("ocation").all()
    assert set(with_works.columns[(with_works != without).any()]) <= {"text", "rating"}


def test_synthetic_sample_finds_the_road_works():
    d = api.load_cluster()
    hoods = api.neighbourhoods(d)
    assert list(hoods["aspect"]) == ["Location"]
    assert hoods.iloc[0]["members"] == ", ".join(NEIGHBOURS)
    assert hoods.iloc[0]["change_month"] == "2025-03"
    scope = api.market_scope(d).set_index("aspect")
    assert scope.loc["Location", "scope"] == "neighbourhood-wide"
    # The injected ground truth agrees.
    truth = gen.INJECTED_PATTERNS["road_works"]
    assert (truth["aspect"], truth["change_month"], truth["scope"]) == (
        "Location", "2025-03", "neighbourhood-wide"
    )
