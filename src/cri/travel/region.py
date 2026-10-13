"""Local sellers, seller-category opportunity and the tourism-board region view.

Seller records and category seasonality are SYNTHETIC. Opportunity scores are
*visitor-exposure estimates* (expected demand x category seasonality), never sales.
"""

from __future__ import annotations

from datetime import date

from .. import api
from .alternatives import CEILING, find_alternatives
from .data import Evidence, Seller, TravelData
from .demand import DemandModel, demand_calendar, peak_periods, regional_overview

UNDER_SERVED_SCORE = 55
EXPOSURE_NOTE = "Visitor-exposure estimate (demand x category seasonality), not sales or income."


def sellers_for(td: TravelData, destination: str | None = None,
                category: str | None = None) -> list[Seller]:
    if destination is not None:
        td.destination(destination)
    if category is not None and category not in td.seller_categories:
        raise ValueError(f"Unknown category {category!r}; available: "
                         f"{', '.join(td.seller_categories)}")
    return [s for s in td.sellers
            if (destination is None or s.destination == destination)
            and (category is None or s.category == category)]


def seller_opportunities(td: TravelData, destination: str, start: date, days: int,
                         model: DemandModel | None = None) -> list[dict]:
    """Rank seller categories by expected visitor exposure over the window."""
    cal = demand_calendar(td, destination, start, days, model)
    rows = []
    for cat, season in td.category_season.items():
        score = round(100 * sum(d.index / 100 * season[d.day.month - 1] for d in cal) / len(cal))
        n = len(sellers_for(td, destination, cat))
        rows.append({
            "category": cat, "label": td.seller_categories[cat], "score": score,
            "sellers_listed": n, "under_served": score >= UNDER_SERVED_SCORE and n <= 1,
            "evidence": Evidence("Exposure score", score, "derived",
                                 f"mean over {days} days of demand index x assumed {cat} "
                                 "seasonality; " + EXPOSURE_NOTE),
        })
    return sorted(rows, key=lambda r: -r["score"])


def _arrivals(td: TravelData, dest_id: str) -> dict | None:
    if dest_id not in td.arrivals:
        return None
    year, total, source, note = td.arrivals[dest_id]
    return {"year": year, "total": total, "source": td.source(source).title, "note": note}


def region_dashboard(d: api.ClusterData, td: TravelData, start: date, days: int,
                     model: DemandModel | None = None) -> dict:
    """Tourism-board view: pressure vs assumed ceilings, peaks, redistribution, sellers."""
    overview = regional_overview(td, start, days, model)
    pressure = []
    for row in overview:
        dest = td.destinations[row["destination"]]
        cal = demand_calendar(td, row["destination"], start, days, model)
        ceiling = CEILING[dest.sensitivity]
        over = [c for c in cal if c.index >= ceiling]
        peaks = sorted(peak_periods(cal), key=lambda p: -p["max_index"])[:3]
        redistribution = None
        if over:
            first = over[0].day
            alt = find_alternatives(td, row["destination"], first, 2, model=model, top_n=2)
            redistribution = {
                "date": first,
                "alternatives": [{"destination": a.destination, "name": a.name,
                                  "mean_index": a.mean_index} for a in alt.alternatives],
            }
        rooms = sum(s.total_rooms for s in td.stays.values() if s.destination == dest.id)
        pressure.append({
            **row,
            "sensitivity": dest.sensitivity,
            "ceiling": Evidence(
                "Assumed ceiling", ceiling, "assumption",
                f"{dest.sensitivity} sensitivity; official carrying capacity unknown"),
            "days_at_or_over_ceiling": len(over),
            "peaks": peaks,
            "redistribution": redistribution,
            "profiled_rooms": rooms,
            "sellers_listed": len(sellers_for(td, dest.id)),
            "official_arrivals": _arrivals(td, dest.id),
        })
    under_served = []
    for dest_id in td.destinations:
        for opp in seller_opportunities(td, dest_id, start, days, model):
            if opp["under_served"]:
                under_served.append({"destination": dest_id, "name": td.destinations[dest_id].name,
                                     "category": opp["label"], "score": opp["score"],
                                     "sellers_listed": opp["sellers_listed"]})
    summary = api.destination_summary(d)
    return {
        "start": start, "days": days,
        "pressure": pressure,
        "under_served_categories": sorted(under_served, key=lambda r: -r["score"]),
        "review_issues": summary.where(summary.notna(), None).to_dict(orient="records"),
        "notes": [
            "Demand index: indicative estimate of relative visitor pressure, not live traffic.",
            "Ceilings are assumptions; no official carrying capacity exists for these places.",
            EXPOSURE_NOTE,
            "Review issues come from the SYNTHETIC review cluster (Properties A-L).",
        ],
    }
