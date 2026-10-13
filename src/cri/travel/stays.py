"""Star-free stay profiles and decision-support insights for providers.

A stay is compared on what a traveller can check (price, rooms, listed amenities,
self-reported practices) and on aspect-level guest feedback computed from review
text by the G5 core (``cri.api``), never on a star average. Amenities and practices
are self-reported in SYNTHETIC data: nothing here is labelled verified.

Provider insights are decision support with a reason and evidence each, not revenue
predictions or automatic pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .. import api
from .data import Evidence, Stay, TravelData
from .demand import DemandModel, demand_calendar, peak_periods

AMENITY_CUES: dict[str, tuple[str, ...]] = {
    "room heating": ("heater", "heating", "हीटर"),
    "hot water": ("hot water", "geyser", "garam paani"),
    "wifi": ("wifi", "wi-fi", "internet"),
    "parking": ("parking",),
}
MIN_COMPLAINTS = 5
LOW_ROOM_SHARE = 0.20
OFFER_MIN_DAYS = 3
PROFILE_NOTE = ("Amenities and practices are self-reported in SYNTHETIC data; nothing here is "
                "verified. Guest feedback is computed from SYNTHETIC review text.")


def price_band(price: int) -> str:
    return "budget" if price < 2000 else "mid-range" if price < 4000 else "premium"


def _room_share(stay: Stay, categories: set[str]) -> float:
    return sum(r.count for r in stay.rooms if r.category in categories) / stay.total_rooms


def suitability(stay: Stay) -> list[Evidence]:
    """Rule-based 'good for' tags, each with the reason (derived from the listing)."""
    cheapest = min(r.price for r in stay.rooms)
    out = []
    if cheapest < 2000:
        out.append(Evidence("Students and budget travellers", "yes", "derived",
                            f"rooms from INR {cheapest:,}/night"))
    family = [r for r in stay.rooms if r.category == "family"]
    if family:
        out.append(Evidence("Families", "yes", "derived",
                            f"{sum(r.count for r in family)} family room(s) for up to 4"))
    if stay.total_rooms >= 15 or any(r.category == "dorm" for r in stay.rooms):
        out.append(Evidence("Groups", "yes", "derived", f"{stay.total_rooms} rooms in total"))
    if dict(stay.practices).get("step-free access"):
        out.append(Evidence("Step-free access", "self-reported", "synthetic",
                            "reported by the property, not verified"))
    if "wifi" in stay.amenities:
        out.append(Evidence("Remote work", "possible", "derived", "wifi listed (speed unknown)"))
    return out


def _feedback(d: api.ClusterData, pid: str) -> list[dict]:
    sc = api.property_scorecard(d, pid)
    rows = []
    for r in sc.itertuples(index=False):
        rows.append({
            "aspect": r.aspect, "mean": _num(r.mean), "ci_low": _num(r.ci_low),
            "ci_high": _num(r.ci_high), "n": int(r.n), "cluster_mean": _num(r.cluster_mean),
            "flag": r.flag,
        })
    return rows


def _num(v) -> float | None:
    return None if pd.isna(v) else round(float(v), 3)


def stay_profiles(d: api.ClusterData, td: TravelData, destination: str | None = None,
                  property_id: str | None = None) -> list[dict]:
    """One star-free profile per stay (optionally for one destination or property)."""
    if destination is not None:
        td.destination(destination)
    if property_id is not None:
        td.stay(property_id)
    cps = api.changepoints(d)
    out = []
    for pid, stay in td.stays.items():
        if destination and stay.destination != destination:
            continue
        if property_id and pid != property_id:
            continue
        prices = [r.price for r in stay.rooms]
        mine = cps[(cps["property_id"] == pid) & (cps["direction"] == "negative")]
        declines = [f"{r.aspect} from {r.change_month}" for r in mine.itertuples()]
        feedback = _feedback(d, pid)
        out.append({
            "property_id": pid, "destination": stay.destination,
            "destination_name": td.destinations[stay.destination].name, "kind": stay.kind,
            "price_from": min(prices), "price_to": max(prices),
            "price_band": price_band(min(prices)),
            "rooms": [vars(r) for r in stay.rooms], "total_rooms": stay.total_rooms,
            "amenities": sorted(stay.amenities),
            "practices": [{"practice": k, "status": "reported" if v else "not reported"}
                          for k, v in stay.practices],
            "suitability": suitability(stay),
            "feedback": feedback,
            "leads": [f["aspect"] for f in feedback if f["flag"] == "lead"],
            "lags": [f["aspect"] for f in feedback if f["flag"] == "lag"],
            "consistency": Evidence(
                "Significant declines vs the market", len(declines), "measured",
                "; ".join(declines) if declines
                else "none detected (FDR 5%, methodology section 6)"),
            "note": PROFILE_NOTE,
        })
    return out


@dataclass(frozen=True)
class Insight:
    kind: str
    priority: str  # high | medium | low
    title: str
    why: str
    evidence: tuple[Evidence, ...]
    period: str | None = None


def _amenity_insights(d: api.ClusterData, stay: Stay) -> list[Insight]:
    neg = api.search_reviews(d, sentiment=-1)
    n_reviews = d.reviews.groupby("property_id")["review_id"].nunique()
    scope = api.market_scope(d).set_index("aspect")
    out = []
    for amenity, cues in AMENITY_CUES.items():
        hit = neg[neg["sentence"].str.lower().str.contains("|".join(cues), regex=True, na=False)]
        mine = hit[hit["property_id"] == stay.property_id]
        n = mine["review_id"].nunique()
        if n < MIN_COMPLAINTS:
            continue
        rate = 100 * n / n_reviews[stay.property_id]
        cluster_rate = 100 * hit["review_id"].nunique() / n_reviews.sum()
        months = pd.to_datetime(mine["date"]).dt.strftime("%B").value_counts()
        top_month, share = months.index[0], months.iloc[0] / months.sum()
        listed = amenity in stay.amenities
        title = (f"Guests report problems with the {amenity} you list" if listed else
                 f"Complaints about {amenity}, which your listing does not mention")
        why = (f"{n} negative review clauses mention {amenity} "
               f"({rate:.1f} per 100 of your reviews vs {cluster_rate:.1f} across the cluster); "
               f"{share:.0%} of them in {top_month}.")
        aspects = set(mine["aspect"])
        for aspect in sorted(aspects & set(scope.index)):
            row = scope.loc[aspect]
            if row["scope"] == "market-wide":
                why += (f" {aspect} complaints are market-wide ({row['pattern']}), so this is "
                        "partly a destination issue to raise with the tourism board, but guests "
                        "still judge your rooms.")
        examples = tuple(Evidence("Example clause", s, "synthetic", "SYNTHETIC review")
                         for s in mine["sentence"].drop_duplicates().head(3))
        out.append(Insight(
            "amenity_gap", "high" if not listed or rate > cluster_rate else "medium", title, why,
            (Evidence("Complaining reviews", n, "measured", "search_reviews(sentiment=-1)"),
             Evidence("Per 100 reviews (you)", round(rate, 1), "measured", ""),
             Evidence("Per 100 reviews (cluster)", round(cluster_rate, 1), "measured", ""))
            + examples,
            period=top_month,
        ))
    return out


def provider_insights(d: api.ClusterData, td: TravelData, property_id: str, start: date,
                      days: int = 90, model: DemandModel | None = None) -> list[Insight]:
    """Ranked, explained opportunities for one property (decision support only)."""
    stay = td.stay(property_id)
    dest = td.destinations[stay.destination]
    insights: list[Insight] = []

    for rank, r in enumerate(api.priority_actions(d, property_id).itertuples()):
        started = f" since {r.started}" if r.started else ""
        title = (f"Fix {r.aspect} first{started}" if rank == 0
                 else f"Also improve {r.aspect}{started}")
        insights.append(Insight(
            "review_priority", "high" if rank == 0 else "medium", title, r.rationale,
            (Evidence("Gap to reference", round(float(r.gap), 2), "measured", str(r.basis)),
             Evidence("Share of your mentions", round(float(r.volume), 2), "measured", ""))))

    insights += _amenity_insights(d, stay)

    cal = demand_calendar(td, stay.destination, start, days, model)
    family = _room_share(stay, {"family"})
    budget = _room_share(stay, {"dorm", "budget"})
    for p in sorted(peak_periods(cal), key=lambda p: -p["max_index"])[:2]:
        drivers = ", ".join(p["drivers"]) or "season"
        notes, prio = [], "medium"
        if family < LOW_ROOM_SHARE and any("School" in x or "Year-end" in x for x in p["drivers"]):
            notes.append(f"family rooms are only {family:.0%} of your inventory during a "
                         "family-travel period")
            prio = "high"
        if budget < LOW_ROOM_SHARE and any(x in ("Weekend", "Long weekend") for x in p["drivers"]):
            notes.append(f"budget rooms are {budget:.0%} of inventory when students travel")
        period = f"{p['start']:%d %b} - {p['end']:%d %b %Y}"
        insights.append(Insight(
            "demand_peak", prio,
            f"Expected {('Very High' if p['max_index'] >= 75 else 'High')} demand in {dest.name}, "
            f"{period}",
            f"Demand index up to {p['max_index']}/100 driven by {drivers}."
            + (" Note: " + "; ".join(notes) + "." if notes else "")
            + " An estimate, not a booking forecast.",
            (Evidence("Peak index", p["max_index"], "derived", "heuristic demand index"),
             Evidence("Family-room share", f"{family:.0%}", "synthetic", "your listed rooms"),
             Evidence("Budget-room share", f"{budget:.0%}", "synthetic", "your listed rooms")),
            period=period))

    windows, run = [], []
    for day in cal + [None]:
        if day is not None and day.category == "Low":
            run.append(day)
            continue
        if len(run) >= OFFER_MIN_DAYS:
            windows.append(run)
        run = []
    if windows:
        periods = [f"{w[0].day:%d %b} - {w[-1].day:%d %b}" for w in windows]
        insights.append(Insight(
            "offer_window", "medium",
            f"{len(windows)} low-demand window(s) of {OFFER_MIN_DAYS}+ days: consider offers",
            f"{sum(len(w) for w in windows)} days in the next {days} are estimated Low "
            f"(max {max(x.index for w in windows for x in w)}/100), first {periods[0]}. A weekday "
            "or long-stay offer for students or remote workers could fill rooms.",
            tuple(Evidence("Low-demand window", p_, "derived", "heuristic demand index")
                  for p_ in periods[:6]),
            period=periods[0]))

    missing = [k for k, v in stay.practices if not v]
    if missing:
        insights.append(Insight(
            "sustainability", "low", "Sustainability practices not reported",
            "Travellers compare stays on reported practices instead of stars; these show as "
            f"'not reported': {', '.join(missing)}. Reporting them (and later verifying them) "
            "makes your profile comparable.",
            tuple(Evidence(k, "not reported", "synthetic", "self-reported listing")
                  for k in missing)))

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(insights, key=lambda i: order[i.priority])
