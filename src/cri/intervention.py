""""Did my fix work?" - a market-adjusted before/after check for one change a
property made (new cook, heater replacement, housekeeping training...).

A naive before/after comparison mixes the property's change with everything else
that moved at the same time: the season, a road closure, a market-wide recovery.
Here the comparison is made *relative to the market*, with the same reference the
"Is it me?" changepoints use (other properties' deviations from their own levels),
so a change every property saw cancels out. In effect a difference-in-differences
with the rest of the cluster as the comparison group.

The month is chosen by the user before looking at the result, so it is ONE test:
no search over splits and no multiple-testing correction. Rules and limitations
are documented in docs/methodology.md section 12.
"""

from __future__ import annotations

import pandas as pd

from .benchmark import (
    CHANGEPOINT_MIN_EFFECT,
    CHANGEPOINT_MIN_MONTHS,
    CHANGEPOINT_MIN_UNITS,
    market_adjusted_months,
    review_units,
)
from .changepoint import find_changepoint, shift_at, t_ppf

ALPHA = 0.05  # one pre-specified test: the user picks the month before seeing the result
MIN_UNITS_PER_SIDE = CHANGEPOINT_MIN_UNITS  # reviews mentioning the aspect, each side
POWER_Z = 2.8016  # z(0.975) + z(0.80): minimum detectable effect at 80% power
TIMING_MIN_MONTHS = 2  # months each side when locating when the change really began

VERDICTS = ("improved", "worsened", "no detectable change", "too early to tell", "no data")
INTERVENTION_KEYS = [
    "property_id", "aspect", "start", "baseline_start", "verdict", "basis",
    "effect", "ci_low", "ci_high", "p_value", "naive_delta", "market_delta",
    "before_mean", "after_mean", "n_before", "n_after", "months_before", "months_after",
    "mde", "placebo_rank", "n_placebo", "detected_start", "summary",
]


def month(value) -> pd.Period:
    try:
        return pd.Period(pd.Timestamp(value), freq="M")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Not a date or month: {value!r} (use e.g. '2025-06')") from exc


def _empty(property_id: str, aspect: str, start: pd.Period, verdict: str, summary: str) -> dict:
    out = dict.fromkeys(INTERVENTION_KEYS)
    out.update(
        property_id=property_id, aspect=aspect, start=start.strftime("%Y-%m"),
        verdict=verdict, n_before=0, n_after=0, months_before=0, months_after=0,
        n_placebo=0, summary=summary,
    )
    return out


def no_dates(property_id: str, aspect: str, start: pd.Period) -> dict:
    """The result for a source without review dates: nothing can be compared."""
    return _empty(property_id, aspect, start, "no data",
                  "This source has no review dates, so a before/after check is not possible.")


def _detect_baseline(series: pd.DataFrame) -> pd.Period | None:
    """Start of the current level before the change: the latest significant shift
    relative to the market in the months before ``start``, if any.

    Managers usually act *after* something went wrong. Comparing with the whole
    history would then mix the good months before the problem with the bad months
    that prompted the fix, and could hide a real recovery.
    """
    cp = find_changepoint(
        series["n"], series["rs"], series["rss"], series["s"],
        market_var=series["mvar"],
        min_months=CHANGEPOINT_MIN_MONTHS, min_units=CHANGEPOINT_MIN_UNITS,
    )
    if cp is None or cp.p_value > ALPHA or abs(cp.delta) < CHANGEPOINT_MIN_EFFECT:
        return None
    return series["month"].iloc[cp.index]


def _detected_start(window: pd.DataFrame) -> pd.Period | None:
    """When the change in ``window`` actually began: the most significant split
    (searched, Bonferroni over splits), or None if no split is significant."""
    cp = find_changepoint(
        window["n"], window["rs"], window["rss"], window["s"],
        market_var=window["mvar"],
        min_months=TIMING_MIN_MONTHS, min_units=MIN_UNITS_PER_SIDE,
    )
    if cp is None or cp.p_value > ALPHA:
        return None
    return window["month"].iloc[cp.index]


def _shift(series: pd.DataFrame, baseline: pd.Period, start: pd.Period):
    window = series[series["month"] >= baseline]
    split = int((window["month"] < start).sum())
    shift = shift_at(
        window["n"], window["rs"], window["rss"], window["s"],
        split=split, market_var=window["mvar"],
    )
    return window, split, shift


def evaluate_intervention(
    labelled: pd.DataFrame,
    property_id: str,
    aspect: str,
    start,
    baseline_start=None,
) -> dict:
    """Did ``aspect`` at ``property_id`` change from ``start`` (the first month after
    the fix), relative to the market?

    * **effect**: after - before of the property's sentiment *minus the market's
      change over the same months* (-2..+2 scale; > 0 = better). ``ci_low``/
      ``ci_high`` are its 95% interval, ``p_value`` the two-sided test of no change.
    * **naive_delta**: the plain after - before change; ``market_delta`` the part the
      market shared (None without a market).
    * **baseline_start**: "before" begins here, the latest significant shift before
      ``start`` (so a fix made after a decline is compared with the declined level);
      the first month of data when there is none. Pass it to override.
    * **mde**: the smallest effect this much data detects with 80% power.
    * **placebo_rank** / **n_placebo**: every other property with enough reviews is
      put through the same check at the same months; rank 1 means no other property
      moved as much (an in-space placebo test). None without a market.
    * **detected_start**: when the data say the change began (searched over months,
      significant splits only). If it is well before ``start``, the change was
      already under way and may not be due to the fix: the summary warns.
    * **verdict**: ``improved`` / ``worsened`` (p <= 0.05), ``no detectable change``,
      ``too early to tell`` (fewer than 10 reviews mentioning the aspect after
      ``start``), or ``no data``. ``basis`` is ``market`` or ``own history`` (fewer
      than 3 properties review the aspect: the market cannot be removed).
    """
    start_m = month(start)
    base_m = None if baseline_start is None else month(baseline_start)
    if base_m is not None and base_m >= start_m:
        raise ValueError(f"baseline_start {base_m} must be before start {start_m}")

    units = review_units(labelled[labelled["aspect"] == aspect])
    if units.empty or property_id not in set(units["property_id"]):
        return _empty(property_id, aspect, start_m, "no data",
                      f"No reviews of {property_id} mention {aspect}.")
    g = market_adjusted_months(units)
    series = g[g["property_id"] == property_id].reset_index(drop=True)
    has_market = bool(series["residual"].iloc[0]) if not series.empty else False
    pre = series[series["month"] < start_m]
    post = series[series["month"] >= start_m]
    n_after = int(post["n"].sum())

    if base_m is None:
        base_m = _detect_baseline(pre) if len(pre) else None
        if base_m is None:
            base_m = pre["month"].min() if len(pre) else start_m
    before = pre[pre["month"] >= base_m]
    n_before = int(before["n"].sum())

    out = _empty(property_id, aspect, start_m, "", "")
    out.update(
        baseline_start=base_m.strftime("%Y-%m"),
        basis="market" if has_market else "own history",
        n_before=n_before, n_after=n_after,
        months_before=len(before), months_after=len(post),
    )
    if n_before < MIN_UNITS_PER_SIDE:
        out.update(
            verdict="no data",
            summary=(f"Only {n_before} reviews mention {aspect} before {start_m}: "
                     f"at least {MIN_UNITS_PER_SIDE} are needed as a baseline."),
        )
        return out
    if n_after < MIN_UNITS_PER_SIDE:
        out.update(
            verdict="too early to tell",
            summary=(f"Only {n_after} reviews mention {aspect} since {start_m}; "
                     f"check again after at least {MIN_UNITS_PER_SIDE}."),
        )
        return out

    window, split, shift = _shift(series, base_m, start_m)
    tcrit = t_ppf(1.0 - ALPHA / 2.0, shift.dof)
    b_n, a_n = window["n"].iloc[:split].sum(), window["n"].iloc[split:].sum()
    before_mean = float(window["s"].iloc[:split].sum() / b_n)
    after_mean = float(window["s"].iloc[split:].sum() / a_n)

    placebo_rank, n_placebo = None, 0
    if has_market:
        beats = 0
        for _prop, other in g[g["property_id"] != property_id].groupby("property_id"):
            o_before = other[(other["month"] >= base_m) & (other["month"] < start_m)]
            o_after = other[other["month"] >= start_m]
            if o_before["n"].sum() < MIN_UNITS_PER_SIDE or o_after["n"].sum() < MIN_UNITS_PER_SIDE:
                continue
            o_shift = _shift(other, base_m, start_m)[2]
            if o_shift is None:
                continue
            n_placebo += 1
            beats += abs(o_shift.delta) >= abs(shift.delta)
        placebo_rank = 1 + beats if n_placebo else None

    effect = shift.delta
    if shift.p_value <= ALPHA:
        verdict = "improved" if effect > 0 else "worsened"
    else:
        verdict = "no detectable change"
    out.update(
        verdict=verdict,
        effect=round(effect, 3),
        ci_low=round(effect - tcrit * shift.se, 3),
        ci_high=round(effect + tcrit * shift.se, 3),
        p_value=float(shift.p_value),
        naive_delta=round(shift.raw_delta, 3),
        market_delta=round(shift.raw_delta - effect, 3) if has_market else None,
        before_mean=round(before_mean, 3),
        after_mean=round(after_mean, 3),
        mde=round(POWER_Z * shift.se, 3),
        placebo_rank=placebo_rank,
        n_placebo=n_placebo,
    )
    found = _detected_start(window)
    out["detected_start"] = None if found is None else found.strftime("%Y-%m")
    out["summary"] = _summary(out)
    return out


def _summary(r: dict) -> str:
    aspect, start = r["aspect"], r["start"]
    since = f"from {r['baseline_start']}" if r["baseline_start"] else "before"
    own = (f"Your {aspect} sentiment went from {r['before_mean']:+.2f} ({since}) to "
           f"{r['after_mean']:+.2f} (since {start}).")
    if r["basis"] == "own history":
        market = (" Too few properties review this aspect to remove the market's own "
                  "change, so this is a plain before/after comparison.")
    else:
        market = (f" The market moved {r['market_delta']:+.2f} over the same months, so "
                  f"relative to the market the change is {r['effect']:+.2f} "
                  f"(95% CI {r['ci_low']:+.2f} to {r['ci_high']:+.2f}).")
    if r["verdict"] == "no detectable change":
        verdict = (f" That is not distinguishable from no change; with this much data only "
                   f"changes of about {r['mde']:.2f} or more are reliably detected.")
    else:
        verdict = f" That is a significant {'improvement' if r['effect'] > 0 else 'decline'}."
    placebo = ""
    if r["placebo_rank"] is not None:
        placebo = (f" Same check on the other {r['n_placebo']} properties: yours ranks "
                   f"#{r['placebo_rank']} of {r['n_placebo'] + 1} by size of change.")
    timing = ""
    found = r["detected_start"]
    if r["verdict"] in ("improved", "worsened") and found and month(found) < month(start) - 1:
        timing = (f" Caution: the change appears to begin around {found}, before {start}, "
                  "so it may not be caused by what you changed then.")
    return own + market + verdict + placebo + timing

