"""Holiday-aware visitor-demand index (0-100) per destination and day.

A transparent points model, not a trained forecaster: there is no historical daily
footfall to train or validate on (docs/AI_MODEL.md). The index is the sum of the
factors it shows, so every point is explained:

    prior (popularity tier) + season[month] + weekend + gazetted holiday
    + long weekend + assumed school / year-end window, clipped to 0..100

It estimates *relative visitor pressure*. It is not live traffic, not a road-congestion
reading and not a booking forecast. Swap in a trained model by implementing
:class:`DemandModel`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from .data import Destination, Evidence, TravelData

MAX_DAYS = 120
LONG_WEEKEND_MIN = 3
NOTE_INDICATIVE = "Indicative estimate of relative visitor pressure, not live traffic or bookings."


@dataclass(frozen=True)
class DemandDay:
    day: date
    index: int
    category: str
    borderline: bool
    factors: tuple[Evidence, ...]
    notes: tuple[str, ...]


class DemandModel(Protocol):
    """Anything that scores (destination, days) -> one :class:`DemandDay` per day."""

    name: str
    version: str

    def predict(self, td: TravelData, dest: Destination, days: list[date]) -> list[DemandDay]: ...


def daterange(start: date, n: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def off_days(td: TravelData, days: Iterable[date]) -> dict[date, list[str]]:
    """Weekends and gazetted holidays (only within the holiday coverage)."""
    out: dict[date, list[str]] = {}
    for d in days:
        reasons = ["weekend"] if d.weekday() >= 5 else []
        reasons += [h.name for h in td.holiday_on(d)]
        if reasons:
            out[d] = reasons
    return out


def long_weekends(td: TravelData, start: date, end: date) -> dict[date, tuple[date, date, str]]:
    """Days inside a run of >= 3 consecutive off-days that contains a holiday.

    Runs are found on a padded range so a long weekend crossing the window edge is
    still recognised. Returns day -> (run start, run end, holiday names).
    """
    pad = timedelta(days=LONG_WEEKEND_MIN + 1)
    days = daterange(start - pad, (end - start).days + 1 + 2 * pad.days)
    off = off_days(td, days)
    result: dict[date, tuple[date, date, str]] = {}
    run: list[date] = []
    for d in days + [None]:  # sentinel flushes the last run
        if d is not None and d in off:
            run.append(d)
            continue
        holidays = sorted({n for r in run for n in off[r] if n != "weekend"})
        if len(run) >= LONG_WEEKEND_MIN and holidays:
            for r in run:
                result[r] = (run[0], run[-1], ", ".join(holidays))
        run = []
    return result


def categorise(td: TravelData, index: int) -> tuple[str, bool]:
    cfg = td.demand
    cuts = cfg["categories"]
    label = next(name for bound, name in cuts if index < bound)
    borderline = any(abs(index - bound) <= cfg["borderline"] for bound, _ in cuts[:-1])
    return label, borderline


class HeuristicDemandModel:
    """The transparent points model described in the module docstring."""

    name = "heuristic-points"
    version = "1"

    def predict(self, td: TravelData, dest: Destination, days: list[date]) -> list[DemandDay]:
        if not days:
            return []
        cfg = td.demand
        lw = long_weekends(td, min(days), max(days))
        out = []
        for d in days:
            f: list[Evidence] = [
                Evidence("Popularity tier", cfg["prior_points"][dest.popularity], "assumption",
                         f"{dest.popularity} tier: {dest.evidence}"),
                Evidence("Season", round(cfg["season_max"] * dest.season[d.month - 1]), "synthetic",
                         f"{cfg['season_max']} x {dest.season[d.month - 1]:.1f} "
                         f"(assumed season curve, {d:%B})"),
            ]
            if d.weekday() >= 5:
                f.append(Evidence("Weekend", cfg["weekend"], "assumption", f"{d:%A}"))
            for h in td.holiday_on(d):
                note = "; date may shift with moon sighting" if h.moon_dependent else ""
                f.append(Evidence("Gazetted holiday", cfg["holiday"], "fact",
                                  f"{h.name}: {td.source(h.source).title}{note}"))
            if d in lw:
                a, b, names = lw[d]
                f.append(Evidence("Long weekend", cfg["long_weekend"], "derived",
                                  f"{(b - a).days + 1} consecutive days off "
                                  f"({a:%a %d %b} - {b:%a %d %b}) including {names}"))
            for w in td.windows:
                if w.contains(d):
                    f.append(Evidence(w.name, cfg["window"], "assumption", w.note))
            raw = sum(int(e.value) for e in f)
            index = max(0, min(100, raw))
            if index != raw:
                f.append(Evidence("Capped at 100", index - raw, "derived", f"raw total {raw}"))
            notes = [NOTE_INDICATIVE]
            if not td.in_coverage(d):
                notes.append(f"No holiday data for {d}: the holiday lists cover "
                             f"{td.coverage[0]} to {td.coverage[1]}, so holiday and "
                             "long-weekend points are 0.")
            category, borderline = categorise(td, index)
            out.append(DemandDay(d, index, category, borderline, tuple(f), tuple(notes)))
        return out


DEFAULT_MODEL = HeuristicDemandModel()


def _check_days(days: int, limit: int = MAX_DAYS) -> None:
    if not 1 <= days <= limit:
        raise ValueError(f"days must be between 1 and {limit}, got {days}")


def demand_calendar(td: TravelData, dest_id: str, start: date, days: int,
                    model: DemandModel | None = None) -> list[DemandDay]:
    _check_days(days)
    return (model or DEFAULT_MODEL).predict(td, td.destination(dest_id), daterange(start, days))


@dataclass(frozen=True)
class TripDemand:
    destination: str
    start: date
    nights: int
    mean_index: float
    category: str
    days: tuple[DemandDay, ...]

    def drivers(self, top: int = 2) -> list[tuple[str, int]]:
        """Factors adding the most points over the trip (excluding the baseline prior)."""
        totals: dict[str, int] = {}
        for d in self.days:
            for e in d.factors:
                if e.label != "Popularity tier" and isinstance(e.value, int) and e.value > 0:
                    totals[e.label] = totals.get(e.label, 0) + e.value
        ranked = sorted(totals.items(), key=lambda kv: -kv[1])[:top]
        return [(label, round(pts / len(self.days))) for label, pts in ranked]


def trip_demand(td: TravelData, dest_id: str, start: date, nights: int,
                model: DemandModel | None = None) -> TripDemand:
    """Demand over the nights of a stay (arrival day .. last night)."""
    _check_days(nights, 30)
    days = demand_calendar(td, dest_id, start, nights, model)
    mean = sum(d.index for d in days) / len(days)
    return TripDemand(dest_id, start, nights, round(mean, 1), categorise(td, round(mean))[0],
                      tuple(days))


@dataclass(frozen=True)
class QuieterOption:
    start: date
    offset_days: int
    mean_index: float
    category: str
    drop: float
    avoids: tuple[str, ...]


def quieter_dates(td: TravelData, dest_id: str, start: date, nights: int,
                  model: DemandModel | None = None, top: int = 3) -> list[QuieterOption]:
    """Same trip shifted by up to +-N days, kept only if clearly quieter."""
    base = trip_demand(td, dest_id, start, nights, model)
    base_labels = {e.label for d in base.days for e in d.factors if int_value(e) > 0}
    window, min_drop = td.demand["quieter_window"], td.demand["quieter_min_drop"]
    options = []
    for k in range(-window, window + 1):
        if k == 0:
            continue
        t = trip_demand(td, dest_id, start + timedelta(days=k), nights, model)
        drop = round(base.mean_index - t.mean_index, 1)
        if drop >= min_drop:
            labels = {e.label for d in t.days for e in d.factors if int_value(e) > 0}
            avoids = tuple(sorted(base_labels - labels - {"Popularity tier", "Season"}))
            options.append(QuieterOption(t.start, k, t.mean_index, t.category, drop, avoids))
    options.sort(key=lambda o: (o.mean_index, abs(o.offset_days)))
    return options[:top]


def int_value(e: Evidence) -> int:
    return e.value if isinstance(e.value, int) else 0


def regional_overview(td: TravelData, start: date, days: int,
                      model: DemandModel | None = None) -> list[dict]:
    """Per destination: mean index, peak day and days per category over the window."""
    _check_days(days)
    rows = []
    for dest_id, dest in td.destinations.items():
        cal = demand_calendar(td, dest_id, start, days, model)
        peak = max(cal, key=lambda d: d.index)
        counts = {name: 0 for _, name in td.demand["categories"]}
        for d in cal:
            counts[d.category] += 1
        rows.append({
            "destination": dest_id, "name": dest.name, "region": dest.region,
            "state": dest.place.state, "mean_index": round(sum(d.index for d in cal) / days, 1),
            "peak_day": peak.day, "peak_index": peak.index, "peak_category": peak.category,
            "days_by_category": counts,
        })
    return sorted(rows, key=lambda r: -r["mean_index"])


def peak_periods(cal: list[DemandDay], categories: tuple[str, ...] = ("High", "Very High"),
                 ) -> list[dict]:
    """Consecutive runs of days in the given categories, with what drives them."""
    runs: list[list[DemandDay]] = []
    for d in cal:
        if d.category in categories:
            if runs and (d.day - runs[-1][-1].day).days == 1:
                runs[-1].append(d)
            else:
                runs.append([d])
    out = []
    for r in runs:
        drivers = sorted({e.label for d in r for e in d.factors
                          if int_value(e) > 0 and e.label not in ("Popularity tier", "Season")})
        out.append({"start": r[0].day, "end": r[-1].day, "days": len(r),
                    "max_index": max(d.index for d in r), "drivers": drivers})
    return out
