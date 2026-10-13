"""Typed, validated access to the travel-layer resources.

Two files, kept apart on purpose (CLAUDE.md rules 1 and 2):

- ``resources/travel_facts.yaml``: verifiable facts only, each with a source
  (coordinates, gazetted holidays, official distances and arrivals, emission factors).
- ``resources/travel_synthetic.yaml``: SYNTHETIC / assumed values that make the demo
  work (season curves, stays for Properties A-L, sellers, prices, demand weights).

Every number the travel engines show is an :class:`Evidence` whose ``basis`` says
which of the two it came from (or that it was derived from them).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from importlib import resources

import yaml

BASES = ("fact", "synthetic", "assumption", "derived", "measured")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
SENSITIVITIES = ("low", "medium", "high")
TIERS = ("low", "medium", "high")


class UnknownIdError(ValueError):
    """An id (destination, property, seller…) that is not in the data."""


@dataclass(frozen=True)
class Evidence:
    """One number shown to a user, with where it came from.

    ``basis`` is one of :data:`BASES`; ``detail`` is the formula or source with its
    inputs filled in, e.g. ``"212 km x 2 x INR 12/km"``.
    """

    label: str
    value: float | int | str
    basis: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.basis not in BASES:
            raise ValueError(f"basis must be one of {BASES}, got {self.basis!r}")


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    url: str


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    state: str
    district: str
    lat: float
    lon: float
    elevation_m: int
    wikidata: str
    kind: str  # destination | origin


@dataclass(frozen=True)
class Holiday:
    day: date
    name: str
    source: str
    moon_dependent: bool = False


@dataclass(frozen=True)
class Window:
    """An assumed travel window (school vacation, year-end), never a fact."""

    name: str
    start: date
    end: date
    note: str

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


@dataclass(frozen=True)
class Activity:
    name: str
    price: int
    tags: frozenset[str]


@dataclass(frozen=True)
class Destination:
    place: Place
    region: str
    belt: bool
    popularity: str
    evidence: str
    season: tuple[float, ...]  # Jan..Dec, 0..1
    suitable: frozenset[int]
    budget: int  # 1 low .. 3 high
    sensitivity: str
    landscape: frozenset[str]
    activities: tuple[Activity, ...]

    @property
    def id(self) -> str:
        return self.place.id

    @property
    def name(self) -> str:
        return self.place.name

    @property
    def tags(self) -> frozenset[str]:
        return frozenset(t for a in self.activities for t in a.tags)


@dataclass(frozen=True)
class Room:
    category: str
    count: int
    price: int


@dataclass(frozen=True)
class Stay:
    property_id: str
    destination: str
    kind: str
    rooms: tuple[Room, ...]
    amenities: frozenset[str]
    practices: tuple[tuple[str, bool], ...]

    @property
    def total_rooms(self) -> int:
        return sum(r.count for r in self.rooms)


@dataclass(frozen=True)
class Seller:
    id: str
    name: str
    destination: str
    category: str
    offering: str
    price: str
    verification: str = "unverified (SYNTHETIC)"


@dataclass(frozen=True)
class EmissionFactor:
    mode: str
    value: float
    unit: str
    per: str  # vehicle-km | passenger-km
    source: str
    note: str


@dataclass(frozen=True)
class TravelData:
    sources: dict[str, Source]
    places: dict[str, Place]
    destinations: dict[str, Destination]
    distances: dict[frozenset[str], tuple[int, str]]
    holidays: tuple[Holiday, ...]
    coverage: tuple[date, date]
    windows: tuple[Window, ...]
    arrivals: dict[str, tuple[int, int, str, str]]  # place -> (year, total, source, note)
    emission_factors: dict[str, EmissionFactor]
    stays: dict[str, Stay]
    sellers: tuple[Seller, ...]
    seller_categories: dict[str, str]
    category_season: dict[str, tuple[float, ...]]
    typical_room_price: dict[int, int]
    costs: dict
    demand: dict
    road_factor: float = field(default=0.0)

    # --- lookups ---------------------------------------------------------------------
    def destination(self, dest_id: str) -> Destination:
        try:
            return self.destinations[dest_id]
        except KeyError:
            raise UnknownIdError(
                f"Unknown destination {dest_id!r}; available: {', '.join(self.destinations)}"
            ) from None

    def origin(self, origin_id: str) -> Place:
        place = self.places.get(origin_id)
        if place is None or place.kind != "origin":
            origins = [p.id for p in self.places.values() if p.kind == "origin"]
            raise UnknownIdError(f"Unknown origin {origin_id!r}; available: {', '.join(origins)}")
        return place

    def stay(self, property_id: str) -> Stay:
        try:
            return self.stays[property_id]
        except KeyError:
            raise UnknownIdError(
                f"Unknown property {property_id!r}; available: {', '.join(self.stays)}"
            ) from None

    def source(self, key: str) -> Source:
        return self.sources[key]

    def holiday_on(self, day: date) -> list[Holiday]:
        return [h for h in self.holidays if h.day == day]

    def in_coverage(self, day: date) -> bool:
        return self.coverage[0] <= day <= self.coverage[1]

    def road_km(self, a: str, b: str) -> Evidence:
        """Road distance between two places: official if published, else an estimate."""
        if a == b:
            return Evidence("Road distance", 0, "derived", "same place")
        official = self.distances.get(frozenset((a, b)))
        if official:
            km, source = official
            return Evidence("Road distance", km, "fact", self.sources[source].title)
        pa, pb = self.places[a], self.places[b]
        straight = haversine_km(pa.lat, pa.lon, pb.lat, pb.lon)
        km = round(straight * self.road_factor)
        return Evidence(
            "Road distance (estimate)",
            km,
            "derived",
            f"straight line {straight:.0f} km x {self.road_factor:.2f} (median road/straight-line "
            f"ratio of the {len(self.distances)} official distances)",
        )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --- loading + validation ------------------------------------------------------------


def _read(name: str) -> dict:
    text = resources.files("cri").joinpath("resources", name).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{name}: expected a mapping at the top level")
    return data


def _months(values: list, what: str) -> tuple[float, ...]:
    if len(values) != 12 or not all(0 <= float(v) <= 1 for v in values):
        raise ValueError(f"{what}: needs 12 values between 0 and 1")
    return tuple(float(v) for v in values)


def build(facts: dict, synthetic: dict) -> TravelData:
    """Validate the two resource mappings and build :class:`TravelData`."""
    if synthetic.get("label") != "SYNTHETIC":
        raise ValueError("travel_synthetic.yaml must carry `label: SYNTHETIC` (CLAUDE.md rule 2)")

    sources = {k: Source(k, v["title"], v["url"]) for k, v in facts["sources"].items()}

    def src(key: str, where: str) -> str:
        if key not in sources:
            raise ValueError(f"{where}: unknown source {key!r}")
        return key

    places = {pid: Place(id=pid, **p) for pid, p in facts["places"].items()}
    for p in places.values():
        if p.kind not in ("destination", "origin"):
            raise ValueError(f"place {p.id}: kind must be destination or origin")

    distances: dict[frozenset[str], tuple[int, str]] = {}
    for d in facts["distances_km"]:
        if d["from"] not in places or d["to"] not in places:
            raise ValueError(f"distance {d}: unknown place")
        distances[frozenset((d["from"], d["to"]))] = (int(d["km"]), src(d["source"], "distance"))

    holidays = []
    for h in facts["holidays"]["items"]:
        day = h["date"]
        if WEEKDAYS[day.weekday()] != h["weekday"]:
            raise ValueError(f"holiday {h['name']} {day}: listed as {h['weekday']}, is not")
        holidays.append(Holiday(day, h["name"], src(h["source"], "holiday"),
                                bool(h.get("moon_dependent", False))))
    cov = facts["holidays"]["coverage"]
    coverage = (cov["start"], cov["end"])
    if any(not (coverage[0] <= h.day <= coverage[1]) for h in holidays):
        raise ValueError("a holiday falls outside the declared coverage")

    arrivals = {
        a["place"]: (int(a["year"]), int(a["total"]), src(a["source"], "arrivals"),
                     a.get("note", ""))
        for a in facts["arrivals"]
    }
    factors = {
        mode: EmissionFactor(mode, float(f["value"]), f["unit"], f["per"],
                             src(f["source"], "emission factor"), f.get("note", ""))
        for mode, f in facts["emission_factors"].items()
    }

    destinations = {}
    for did, d in synthetic["destinations"].items():
        place = places.get(did)
        if place is None or place.kind != "destination":
            raise ValueError(f"destination {did}: no matching place in travel_facts.yaml")
        if d["popularity"] not in TIERS or d["sensitivity"] not in SENSITIVITIES:
            raise ValueError(f"destination {did}: bad popularity or sensitivity")
        if d["budget"] not in (1, 2, 3):
            raise ValueError(f"destination {did}: budget must be 1, 2 or 3")
        destinations[did] = Destination(
            place=place, region=d["region"], belt=bool(d["belt"]), popularity=d["popularity"],
            evidence=d["evidence"], season=_months(d["season"], f"{did} season"),
            suitable=frozenset(int(m) for m in d["suitable"]), budget=int(d["budget"]),
            sensitivity=d["sensitivity"], landscape=frozenset(d["landscape"]),
            activities=tuple(Activity(a["name"], int(a["price"]), frozenset(a["tags"]))
                             for a in d["activities"]),
        )
    missing = [p.id for p in places.values()
               if p.kind == "destination" and p.id not in destinations]
    if missing:
        raise ValueError(f"destinations without a profile: {missing}")

    stays = {}
    for pid, s in synthetic["stays"].items():
        if s["destination"] not in destinations:
            raise ValueError(f"stay {pid}: unknown destination {s['destination']!r}")
        stays[pid] = Stay(
            property_id=pid, destination=s["destination"], kind=s["kind"],
            rooms=tuple(Room(r["category"], int(r["count"]), int(r["price"])) for r in s["rooms"]),
            amenities=frozenset(s["amenities"]),
            practices=tuple((k, bool(v)) for k, v in s["practices"].items()),
        )

    categories = dict(synthetic["seller_categories"])
    sellers = []
    for s in synthetic["sellers"]:
        if s["destination"] not in destinations or s["category"] not in categories:
            raise ValueError(f"seller {s['id']}: unknown destination or category")
        sellers.append(Seller(**s))
    category_season = {c: _months(v, f"category {c}")
                       for c, v in synthetic["category_season"].items()}
    if set(category_season) != set(categories):
        raise ValueError("category_season must cover exactly the seller categories")

    windows = tuple(Window(w["name"], w["start"], w["end"], w["note"])
                    for w in synthetic["windows"])

    data = TravelData(
        sources=sources, places=places, destinations=destinations, distances=distances,
        holidays=tuple(sorted(holidays, key=lambda h: h.day)), coverage=coverage, windows=windows,
        arrivals=arrivals, emission_factors=factors, stays=stays, sellers=tuple(sellers),
        seller_categories=categories, category_season=category_season,
        typical_room_price={int(k): int(v) for k, v in synthetic["typical_room_price"].items()},
        costs=dict(synthetic["costs"]), demand=dict(synthetic["demand"]),
    )
    # Derived, not assumed: how much longer hill roads are than the straight line,
    # measured on the official distances above.
    ratios = []
    for pair, (km, _) in distances.items():
        a, b = sorted(pair)
        straight = haversine_km(places[a].lat, places[a].lon, places[b].lat, places[b].lon)
        ratios.append(km / straight)
    object.__setattr__(data, "road_factor", round(statistics.median(ratios), 2))
    return data


@lru_cache(maxsize=1)
def load_travel_data() -> TravelData:
    """Load and validate the packaged travel resources (cached)."""
    return build(_read("travel_facts.yaml"), _read("travel_synthetic.yaml"))
