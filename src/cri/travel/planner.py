"""Affordable, crowd-aware trip planner with a transparent cost and carbon estimate.

Every cost and emission line is an :class:`Evidence` with its formula filled in.
Prices are illustrative (SYNTHETIC); nothing here is a booking, a quote or live
availability. Carbon uses sourced emission factors (travel_facts.yaml) applied to a
road distance that is official where published and estimated otherwise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from .. import api
from .alternatives import find_alternatives
from .data import Evidence, Stay, TravelData
from .demand import DemandModel, quieter_dates, trip_demand
from .region import sellers_for

MODES = ("car", "bus")
STAY_PREFS = ("any", "budget", "standard", "family")
PREF_CATEGORIES = {"budget": ("dorm", "budget"), "standard": ("standard", "deluxe"),
                   "family": ("family",), "any": ("dorm", "budget", "standard", "family", "deluxe")}
NOTE = ("Illustrative SYNTHETIC prices and inventory: not a quote, booking or live availability. "
        "Demand is an indicative estimate, not live traffic.")


@dataclass(frozen=True)
class PlanInput:
    origin: str
    destination: str
    start: date
    nights: int
    travellers: int
    budget: int
    interests: tuple[str, ...] = ()
    stay_pref: str = "any"
    transport: str = "car"
    sustainability: bool = False

    def validate(self, td: TravelData) -> None:
        td.origin(self.origin)
        td.destination(self.destination)
        if not 1 <= self.nights <= 14:
            raise ValueError("nights must be between 1 and 14")
        if not 1 <= self.travellers <= 12:
            raise ValueError("travellers must be between 1 and 12")
        if not 0 < self.budget <= 10_000_000:
            raise ValueError("budget must be a positive amount up to 10,000,000")
        if self.stay_pref not in STAY_PREFS:
            raise ValueError(f"stay_pref must be one of {STAY_PREFS}")
        if self.transport not in MODES:
            raise ValueError(f"transport must be one of {MODES}")
        known = {t for dest in td.destinations.values() for t in dest.tags}
        unknown = set(self.interests) - known
        if unknown:
            raise ValueError(f"Unknown interests {sorted(unknown)}; available: {sorted(known)}")


@dataclass(frozen=True)
class TripPlan:
    request: PlanInput
    destination_name: str
    end: date
    demand: dict
    stay: dict | None
    itinerary: tuple[dict, ...]
    costs: tuple[Evidence, ...]
    total: int
    per_person: int
    within_budget: bool
    carbon: tuple[Evidence, ...]
    sellers: tuple[dict, ...]
    variants: tuple[dict, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = (NOTE,)


def _pick_stay(d: api.ClusterData, td: TravelData, inp: PlanInput) -> tuple[Stay, str, int] | None:
    """Stay with a room category matching the preference and enough rooms.

    Ranked by (fewest guest-feedback lags, then price); with a sustainability priority,
    more reported practices come first. Returns (stay, category, rooms needed).
    """
    per_room = td.costs["persons_per_room"]
    options = []
    for stay in td.stays.values():
        if stay.destination != inp.destination:
            continue
        lags = int((api.property_scorecard(d, stay.property_id)["flag"] == "lag").sum())
        for room in stay.rooms:
            if room.category not in PREF_CATEGORIES[inp.stay_pref]:
                continue
            need = math.ceil(inp.travellers / per_room[room.category])
            if need > room.count:
                continue
            green = -sum(v for _, v in stay.practices) if inp.sustainability else 0
            options.append(((green, lags, room.price * need), stay, room.category, need))
    if not options:
        return None
    _, stay, category, need = min(options, key=lambda o: o[0])
    return stay, category, need


def _build(d: api.ClusterData, td: TravelData, inp: PlanInput, model: DemandModel | None,
           with_variants: bool) -> TripPlan:
    inp.validate(td)
    dest = td.destination(inp.destination)
    costs_cfg, T = td.costs, inp.travellers
    km = td.road_km(inp.origin, inp.destination)
    kind = "official" if km.basis == "fact" else "estimated"
    dist_note = f"{km.value} km each way ({kind}: {km.detail})"
    vehicles = math.ceil(T / costs_cfg["car_capacity"])

    if inp.transport == "car":
        rate = costs_cfg["car_per_vehicle_km"]
        transport = Evidence("Transport (car, return)", 2 * km.value * rate * vehicles, "synthetic",
                             f"2 x {km.value} km x INR {rate}/vehicle-km x {vehicles} car(s); "
                             f"{dist_note}")
    else:
        rate = costs_cfg["bus_per_passenger_km"]
        transport = Evidence("Transport (bus, return)", round(2 * km.value * rate * T), "synthetic",
                             f"2 x {km.value} km x INR {rate}/passenger-km x {T}; {dist_note}")

    picked = _pick_stay(d, td, inp)
    if picked:
        stay, category, rooms = picked
        price = next(r.price for r in stay.rooms if r.category == category)
        stay_line = Evidence("Stay", price * rooms * inp.nights, "synthetic",
                             f"{stay.property_id} ({stay.kind}), {rooms} x {category} room at "
                             f"INR {price:,}/night x {inp.nights} night(s)")
        stay_info = {"property_id": stay.property_id, "kind": stay.kind, "category": category,
                     "rooms": rooms, "price_per_night": price}
    else:
        price, rooms = td.typical_room_price[dest.budget], math.ceil(T / 2)
        stay_line = Evidence("Stay (typical, no profiled stay)", price * rooms * inp.nights,
                             "synthetic", f"{rooms} room(s) x typical INR {price:,}/night for "
                             f"budget level {dest.budget} x {inp.nights} night(s)")
        stay_info = None

    wanted = set(inp.interests)
    acts = sorted(dest.activities, key=lambda a: (-len(a.tags & wanted), a.price))
    if wanted:
        acts = [a for a in acts if a.tags & wanted] or acts
    slots = max(1, (inp.nights - 1) * 2 + 1)
    chosen = acts[:slots]
    listing = " + ".join(f"{a.name} INR {a.price}" for a in chosen)
    activities = Evidence("Activities", sum(a.price for a in chosen) * T, "synthetic",
                          f"{listing} per person x {T}")
    food_rate = costs_cfg["food_per_person_day"][dest.budget]
    food = Evidence("Food", food_rate * T * (inp.nights + 1), "synthetic",
                    f"INR {food_rate}/person/day (budget level {dest.budget}) x {T} x "
                    f"{inp.nights + 1} day(s)")
    lines = (transport, stay_line, activities, food)
    total = sum(int(e.value) for e in lines)

    carbon = []
    for mode in MODES:
        f = td.emission_factors[mode]
        if mode == "car":
            kg = 2 * km.value * f.value * vehicles
            detail = f"2 x {km.value} km x {f.value} {f.unit}/{f.per} x {vehicles} car(s)"
        else:
            kg = 2 * km.value * f.value * T
            detail = f"2 x {km.value} km x {f.value} {f.unit}/{f.per} x {T} traveller(s)"
        carbon.append(Evidence(
            f"Travel emissions by {mode}{' (your choice)' if mode == inp.transport else ''}",
            round(kg, 1), "derived",
            f"{detail}. Factor: {td.source(f.source).title}; {f.note}. "
            "Stay emissions not estimated."))

    td_trip = trip_demand(td, inp.destination, inp.start, inp.nights, model)
    sellers = sellers_for(td, inp.destination)
    itinerary = []
    n_days = inp.nights + 1
    queue = list(chosen)
    for i in range(n_days):
        day = inp.start + timedelta(days=i)
        items = []
        if i == 0:
            items.append(f"Travel from {td.places[inp.origin].name} "
                         f"(~{km.value / costs_cfg['avg_road_speed_kmh']:.1f} h by road)")
        take = 1 if i in (0, n_days - 1) else 2
        items += [f"{a.name} (INR {a.price} pp)" for a in queue[:take]]
        queue = queue[take:]
        if sellers:
            s = sellers[i % len(sellers)]
            items.append(f"Visit {s.name}: {s.offering} ({s.price})")
        if i == n_days - 1:
            items.append(f"Return to {td.places[inp.origin].name}")
        demand_day = next((x for x in td_trip.days if x.day == day), None)
        itinerary.append({"day": day, "items": items,
                          "demand": demand_day.category if demand_day else None})

    plan = TripPlan(
        request=inp, destination_name=dest.name, end=inp.start + timedelta(days=inp.nights),
        demand={"mean_index": td_trip.mean_index, "category": td_trip.category,
                "drivers": td_trip.drivers()},
        stay=stay_info, itinerary=tuple(itinerary), costs=lines, total=total,
        per_person=round(total / T), within_budget=total <= inp.budget, carbon=tuple(carbon),
        sellers=tuple({"id": s.id, "name": s.name, "category": s.category, "offering": s.offering,
                       "price": s.price, "verification": s.verification} for s in sellers),
    )
    if not with_variants:
        return plan

    variants = []
    cheap = replace(inp, stay_pref="budget", transport="bus")
    try:
        alt = _build(d, td, cheap, model, with_variants=False)
    except ValueError:
        alt = None
    if alt and alt.total < plan.total:
        variants.append(_variant("Lower budget", "budget rooms and bus", alt, plan))

    quieter = quieter_dates(td, inp.destination, inp.start, inp.nights, model, top=1)
    others = find_alternatives(td, inp.destination, inp.start, inp.nights, home=inp.origin,
                               model=model, top_n=1).alternatives
    options = []
    if quieter:
        options.append((quieter[0].mean_index, replace(inp, start=quieter[0].start),
                        f"same place, starting {quieter[0].start:%d %b}"))
    if others:
        options.append((others[0].mean_index, replace(inp, destination=others[0].destination),
                        f"{others[0].name} on the same dates"))
    if options:
        _, req, how = min(options, key=lambda o: o[0])
        variants.append(_variant("Lower crowd", how, _build(d, td, req, model, False), plan))
    return replace(plan, variants=tuple(variants))


def _variant(label: str, how: str, v: TripPlan, base: TripPlan) -> dict:
    return {
        "label": label, "how": how, "destination": v.request.destination,
        "destination_name": v.destination_name, "start": v.request.start,
        "transport": v.request.transport, "total": v.total, "per_person": v.per_person,
        "delta_cost": v.total - base.total, "mean_index": v.demand["mean_index"],
        "category": v.demand["category"],
        "delta_index": round(v.demand["mean_index"] - base.demand["mean_index"], 1),
    }


def plan_trip(d: api.ClusterData, td: TravelData, inp: PlanInput,
              model: DemandModel | None = None) -> TripPlan:
    """Itinerary, transparent costs, carbon and cheaper / quieter variants."""
    return _build(d, td, inp, model, with_variants=True)
