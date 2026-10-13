"""Crowd-aware alternative destinations with a carrying-capacity guard.

    sim      = sum(w * s) / sum(w) over landscape, activities, budget, travel time, season
    relief   = (D_origin - D_candidate) / 100        (trip-average demand index)
    headroom = (ceiling(sensitivity) - D_candidate) / 100
    score    = sim * min(relief, headroom)

Candidates are excluded (with the reason) if they are not clearly quieter
(relief < MIN_RELIEF) or already at their assumed ceiling (headroom <= 0), so the
engine never just moves pressure onto a more fragile place. Ceilings are an
assumption: no official carrying capacity exists for these destinations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .data import Destination, Evidence, TravelData
from .demand import DemandModel, TripDemand, daterange, trip_demand

CEILING = {"low": 90, "medium": 80, "high": 70}  # assumed max demand index before guard
MIN_RELIEF = 0.10


@dataclass(frozen=True)
class Weights:
    landscape: float = 0.30
    activities: float = 0.30
    budget: float = 0.15
    travel: float = 0.15
    season: float = 0.10

    def __post_init__(self) -> None:
        values = list(vars(self).values())
        if any(v < 0 or v > 1 for v in values) or sum(values) <= 0:
            raise ValueError("weights must be within 0..1 and not all zero")


@dataclass(frozen=True)
class Alternative:
    destination: str
    name: str
    score: float
    similarity: float
    mean_index: float
    category: str
    components: tuple[Evidence, ...]
    explanation: dict[str, str]


@dataclass(frozen=True)
class AlternativesResult:
    origin: str
    origin_name: str
    start: date
    nights: int
    origin_demand: TripDemand
    alternatives: tuple[Alternative, ...]
    excluded: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def travel_hours(td: TravelData, from_place: str, dest: str) -> tuple[float, Evidence]:
    km = td.road_km(from_place, dest)
    speed = td.costs["avg_road_speed_kmh"]
    return km.value / speed, km


def _season_share(dest: Destination, start: date, nights: int) -> float:
    return sum(d.month in dest.suitable for d in daterange(start, nights)) / nights


def find_alternatives(td: TravelData, origin: str, start: date, nights: int, *,
                      home: str = "delhi", weights: Weights | None = None, top_n: int = 3,
                      model: DemandModel | None = None) -> AlternativesResult:
    """Rank quieter destinations similar to ``origin`` for the same dates."""
    w = weights or Weights()
    o = td.destination(origin)
    td.origin(home)
    od = trip_demand(td, origin, start, nights, model)
    o_hours, _ = travel_hours(td, home, origin)
    drivers = od.drivers()
    why_busy = (
        f"{o.name} averages {od.mean_index:.0f}/100 ({od.category}) for these nights"
        + (": " + ", ".join(f"{label} (+{pts}/day)" for label, pts in drivers) if drivers else "")
        + f", on top of a {o.popularity}-popularity baseline."
    )
    ranked, excluded = [], []
    for cid, c in td.destinations.items():
        if cid == origin:
            continue
        cd = trip_demand(td, cid, start, nights, model)
        relief = (od.mean_index - cd.mean_index) / 100
        headroom = (CEILING[c.sensitivity] - cd.mean_index) / 100
        if relief < MIN_RELIEF:
            excluded.append(
                (cid, f"not clearly quieter ({cd.mean_index:.0f} vs {od.mean_index:.0f})"))
            continue
        if headroom <= 0:
            excluded.append((cid, f"capacity guard: {cd.mean_index:.0f} is at or above the assumed "
                                  f"ceiling {CEILING[c.sensitivity]} for a {c.sensitivity}-"
                                  "sensitivity destination"))
            continue
        c_hours, km = travel_hours(td, home, cid)
        extra = c_hours - o_hours
        s = {
            "landscape": jaccard(o.landscape, c.landscape),
            "activities": jaccard(o.tags, c.tags),
            "budget": 1 - abs(o.budget - c.budget) / 2,
            "travel": max(0.0, 1 - max(0.0, extra) / 4),
            "season": _season_share(c, start, nights),
        }
        wv = vars(w)
        sim = sum(wv[k] * s[k] for k in s) / sum(wv.values())
        score = sim * min(relief, headroom)
        components = tuple(
            Evidence(k.capitalize(), round(v, 2), "derived", f"weight {wv[k]}")
            for k, v in s.items()
        ) + (
            Evidence("Crowd relief", round(relief, 2), "derived",
                     f"({od.mean_index:.0f} - {cd.mean_index:.0f}) / 100"),
            Evidence("Capacity headroom", round(headroom, 2), "assumption",
                     f"(assumed ceiling {CEILING[c.sensitivity]} - {cd.mean_index:.0f}) / 100"),
        )
        shared = sorted((o.landscape & c.landscape) | (o.tags & c.tags))
        budget_word = ("similar" if c.budget == o.budget else
                       "lower" if c.budget < o.budget else "higher")
        ranked.append(Alternative(
            destination=cid, name=c.name, score=round(score, 3), similarity=round(sim, 2),
            mean_index=cd.mean_index, category=cd.category, components=components,
            explanation={
                "why_origin_busy": why_busy,
                "why_similar": (f"Shares {', '.join(shared) if shared else 'little'}"
                                f" with {o.name}; budget level is {budget_word}."),
                "expected_crowd": (f"{cd.category} ({cd.mean_index:.0f}/100) on the same dates, "
                                   f"{relief * 100:.0f} points below {o.name}."),
                "trade_off": (f"About {c_hours:.1f} h by road from {td.places[home].name} "
                              f"({'+' if extra >= 0 else ''}{extra:.1f} h vs {o.name}; "
                              f"{km.value} km, "
                              f"{'official' if km.basis == 'fact' else 'estimated'} distance); "
                              f"budget level {c.budget} vs {o.budget} (1 low - 3 high)."),
                "limitations": (f"Capacity is unknown: the ceiling of {CEILING[c.sensitivity]} "
                                f"for a {c.sensitivity}-sensitivity place is an assumption. "
                                "Season and profile are SYNTHETIC; weather and road status are "
                                "not modelled."
                                + ("" if c.belt else " No profiled stays here yet.")),
            },
        ))
    ranked.sort(key=lambda a: -a.score)
    return AlternativesResult(origin, o.name, start, nights, od, tuple(ranked[:top_n]),
                              tuple(excluded))
