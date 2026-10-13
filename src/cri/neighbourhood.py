"""Is it my neighbourhood? A spatial scan for declines shared by nearby properties.

"Yours alone" and "everyone's" miss a third case: road works on one street, a
water cut in one ward. Each affected property may have too few reviews for its own
decline to pass the per-property test, but pooled with its neighbours it shows.

Method (docs/methodology.md section 13):

1. Candidate neighbourhoods: for each located property, the properties within
   ``NEIGHBOURHOOD_RADIUS_KM`` of it, if there are at least
   ``NEIGHBOURHOOD_MIN_PROPERTIES`` and at most ``NEIGHBOURHOOD_MAX_SHARE`` of the
   cluster (a larger group is the market, which ``market_wide_summary`` covers).
2. Group test: the group's review values, each centred on its property's own level,
   minus the market of the properties OUTSIDE the group, month by month; the best
   single negative step (``find_changepoint``: Bonferroni over splits, the market
   estimate's variance included). The score is the WEAKEST of the leave-one-out
   tests, so one strongly declining property cannot make a neighbourhood.
3. Significance: an in-space permutation test. Positions are shuffled between
   properties (the null: location does not matter) and the whole scan is repeated;
   the maximum over groups AND aspects is compared, which controls the family-wise
   error across both.

Numpy/pandas only. Deterministic for a given ``seed``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .benchmark import (
    CHANGEPOINT_MIN_MONTHS,
    CHANGEPOINT_MIN_UNITS,
    MARKET_MIN_EFFECT,
    review_units,
)
from .changepoint import find_changepoint
from .locations import distance_matrix, haversine_km

NEIGHBOURHOOD_RADIUS_KM = 1.0  # a property's neighbours lie within this distance
NEIGHBOURHOOD_MIN_PROPERTIES = 3  # a neighbourhood has at least this many properties
NEIGHBOURHOOD_MAX_SHARE = 0.5  # ... and at most this share of the cluster
NEIGHBOURHOOD_MAX_P = 0.05  # family-wise over groups and aspects
NEIGHBOURHOOD_PERMUTATIONS = 499
NEIGHBOURHOOD_SEED = 0

NEIGHBOURHOOD_COLUMNS = [
    "aspect", "change_month", "delta", "n_members", "members", "radius_km",
    "centre_lat", "centre_lon", "p_value", "gaps",
]


def _aspect_arrays(units: pd.DataFrame, aspect: str, props: list[str], months) -> tuple:
    """(n, c, cc, var) per property x month: unit count, sum and sum of squares of
    values centred on the property's own level, and the pooled within variance."""
    a = units[units["aspect"] == aspect]
    centred = a["value"] - a.groupby("property_id")["value"].transform("mean")
    a = a.assign(c=centred, cc=centred**2, month=a["date"].dt.to_period("M"))
    g = a.groupby(["property_id", "month"])[["c", "cc"]].agg(["size", "sum"])
    idx = pd.MultiIndex.from_product([props, months])
    shape = (len(props), len(months))
    n = g[("c", "size")].reindex(idx, fill_value=0).to_numpy(float).reshape(shape)
    c = g[("c", "sum")].reindex(idx, fill_value=0.0).to_numpy(float).reshape(shape)
    cc = g[("cc", "sum")].reindex(idx, fill_value=0.0).to_numpy(float).reshape(shape)
    return n, c, cc


def _group_test(n, c, cc, mask):
    """Best negative step of the group vs the market outside it, or None.

    Returns (changepoint, kept month indices)."""
    n_in, c_in, cc_in = n[mask].sum(0), c[mask].sum(0), cc[mask].sum(0)
    n_out, c_out, cc_out = n[~mask].sum(0), c[~mask].sum(0), cc[~mask].sum(0)
    keep = np.flatnonzero((n_in > 0) & (n_out > 0))
    if len(keep) < 2 * CHANGEPOINT_MIN_MONTHS:
        return None
    n_in, c_in, cc_in, n_out, c_out, cc_out = (
        x[keep] for x in (n_in, c_in, cc_in, n_out, c_out, cc_out)
    )
    market = c_out / n_out
    dof = n_out.sum() - len(n_out)
    var_out = (cc_out.sum() - (c_out**2 / n_out).sum()) / dof if dof > 0 else 1.0
    cp = find_changepoint(
        n_in, c_in - n_in * market, cc_in - 2 * market * c_in + n_in * market**2,
        market_var=max(var_out, 1e-9) / n_out,
        min_months=CHANGEPOINT_MIN_MONTHS, min_units=CHANGEPOINT_MIN_UNITS,
    )
    return (cp, keep) if cp is not None else None


def _score(cp) -> float:
    return float(-np.log10(max(cp.p_value, 1e-300))) if cp is not None and cp.delta < 0 else 0.0


def _robust(n, c, cc, members: list[int]) -> tuple[float, tuple | None]:
    """Weakest leave-one-out score of a group, and the full group's test."""
    k = n.shape[0]
    mask = np.zeros(k, dtype=bool)
    mask[members] = True
    full = _group_test(n, c, cc, mask)
    if full is None or full[0].delta >= 0:
        return 0.0, None
    worst = np.inf
    for m in members:
        mask[m] = False
        r = _group_test(n, c, cc, mask)
        mask[m] = True
        worst = min(worst, _score(r[0] if r else None))
        if worst == 0.0:
            break
    return worst, full


def _groups(dist: np.ndarray, radius_km: float, max_size: int) -> list[tuple[int, ...]]:
    within = dist <= radius_km
    groups = {tuple(np.flatnonzero(row)) for row in within}
    return sorted(g for g in groups if NEIGHBOURHOOD_MIN_PROPERTIES <= len(g) <= max_size)


def _scan(arrays: dict, groups: list) -> dict[str, tuple[float, tuple | None, tuple | None]]:
    """Per aspect: (best score, its group, its full test)."""
    out = {}
    for aspect, (n, c, cc) in arrays.items():
        best = (0.0, None, None)
        for g in groups:
            s, full = _robust(n, c, cc, list(g))
            if s > best[0]:
                best = (s, g, full)
        out[aspect] = best
    return out


def neighbourhood_findings(
    labelled: pd.DataFrame,
    locations: pd.DataFrame | None,
    *,
    radius_km: float = NEIGHBOURHOOD_RADIUS_KM,
    max_p: float = NEIGHBOURHOOD_MAX_P,
    permutations: int = NEIGHBOURHOOD_PERMUTATIONS,
    seed: int = NEIGHBOURHOOD_SEED,
) -> list[dict]:
    """Significant neighbourhood-wide declines, one dict per aspect.

    Keys: ``aspect``, ``change_month`` (YYYY-MM), ``delta`` (the group's shift
    relative to the market outside it), ``members`` (sorted ids), ``gaps`` (each
    member's own shift at that month vs the outside market), ``centre`` (lat, lon),
    ``radius_km`` (farthest member from the centre), ``p_value`` (permutation,
    family-wise over groups and aspects). Empty without positions, or with too few
    located properties to form a neighbourhood that is not the whole market.
    """
    if locations is None or locations.empty or labelled.empty:
        return []
    present = set(labelled["property_id"].astype(str))
    loc = locations[locations["property_id"].isin(present)].reset_index(drop=True)
    k = len(loc)
    max_size = int(np.floor(k * NEIGHBOURHOOD_MAX_SHARE))
    if max_size < NEIGHBOURHOOD_MIN_PROPERTIES:
        return []
    props = list(loc["property_id"])
    units = review_units(labelled[labelled["property_id"].astype(str).isin(props)])
    units = units.assign(property_id=units["property_id"].astype(str))
    months = pd.period_range(units["date"].min(), units["date"].max(), freq="M")
    arrays = {
        a: _aspect_arrays(units, a, props, months) for a in sorted(units["aspect"].unique())
    }
    dist = distance_matrix(loc)
    observed = _scan(arrays, _groups(dist, radius_km, max_size))
    if not any(s > 0 for s, _, _ in observed.values()):
        return []

    rng = np.random.default_rng(seed)
    maxima = np.empty(permutations)
    for i in range(permutations):
        perm = rng.permutation(k)
        groups = _groups(dist[np.ix_(perm, perm)], radius_km, max_size)
        maxima[i] = max(s for s, _, _ in _scan(arrays, groups).values())

    findings = []
    for aspect, (score, group, full) in observed.items():
        if group is None:
            continue
        p = (1 + int((maxima >= score).sum())) / (1 + permutations)
        if p > max_p:
            continue
        cp, keep = full
        split = keep[cp.index]
        n, c, _ = arrays[aspect]
        gaps = {}
        for m in group:
            mask = np.ones(k, dtype=bool)
            mask[list(group)] = False
            market = c[mask].sum(0) / np.where(n[mask].sum(0) > 0, n[mask].sum(0), np.nan)
            before = slice(0, split)
            after = slice(split, None)
            res = c[m] - n[m] * np.nan_to_num(market)
            nb, na = n[m][before].sum(), n[m][after].sum()
            if nb > 0 and na > 0:
                gaps[props[m]] = round(float(res[after].sum() / na - res[before].sum() / nb), 3)
        members = sorted(p for p, gap in gaps.items() if gap <= -MARKET_MIN_EFFECT)
        if len(members) < NEIGHBOURHOOD_MIN_PROPERTIES:
            continue
        sub = loc[loc["property_id"].isin(members)]
        centre = (float(sub["lat"].mean()), float(sub["lon"].mean()))
        radius = float(haversine_km(centre[0], centre[1], sub["lat"], sub["lon"]).max())
        findings.append(
            {
                "aspect": aspect,
                "change_month": str(months[split]),
                "delta": round(float(cp.delta), 3),
                "members": members,
                "gaps": {p: gaps[p] for p in members},
                "centre": (round(centre[0], 5), round(centre[1], 5)),
                "radius_km": round(radius, 2),
                "p_value": round(p, 4),
            }
        )
    return findings


def detect_neighbourhoods(
    labelled: pd.DataFrame, locations: pd.DataFrame | None, **kwargs
) -> pd.DataFrame:
    """Tabular view of ``neighbourhood_findings`` (``NEIGHBOURHOOD_COLUMNS``)."""
    rows = [
        {
            "aspect": f["aspect"], "change_month": f["change_month"], "delta": f["delta"],
            "n_members": len(f["members"]), "members": ", ".join(f["members"]),
            "radius_km": f["radius_km"], "centre_lat": f["centre"][0], "centre_lon": f["centre"][1],
            "p_value": f["p_value"], "gaps": f["gaps"],
        }
        for f in neighbourhood_findings(labelled, locations, **kwargs)
    ]
    return pd.DataFrame(rows, columns=NEIGHBOURHOOD_COLUMNS)


def describe_neighbourhood(finding: dict) -> str:
    """One line for the market view, e.g. 'decline from 2025-03 at 4 neighbouring
    properties within 0.31 km (average drop 0.69; p = 0.010)'."""
    return (
        f"decline from {finding['change_month']} at {len(finding['members'])} neighbouring "
        f"properties within {finding['radius_km']:.2f} km (average drop {-finding['delta']:.2f}; "
        f"p = {finding['p_value']:.3f})"
    )
