"""Decision-ready summaries built on the benchmark: what to fix first (and whose
problem it is), and the destination view. Rules are documented in
docs/methodology.md.
"""

from __future__ import annotations

import calendar

import pandas as pd

from .benchmark import (
    MIN_PROPERTIES_FOR_SCOPE,
    MIN_REVIEWS_FOR_FLAG,
    aspect_scores,
    benchmark_vs_cluster,
    cluster_means,
    describe_finding,
    detect_changepoints,
    market_findings,
    market_wide_summary,
    none_for_missing,
    undetermined_note,
)

PRIORITY_COLUMNS = [
    "aspect", "gap", "volume", "impact_score", "started", "rationale",
    "current_mean", "reference_mean", "basis", "n", "whose_problem", "whose_detail",
]
DESTINATION_COLUMNS = [
    "aspect", "cluster_mean", "n", "pct_negative", "scope", "pattern", "n_properties_reviewed",
]


def _cluster_mean_since(labelled: pd.DataFrame, aspect: str, since: pd.Timestamp) -> float:
    """Cluster mean for one aspect over [since, end] (unweighted mean of property means)."""
    window = labelled[(labelled["aspect"] == aspect) & (labelled["date"] >= since)]
    return float(window.groupby("property_id")["sentiment"].mean().mean())


def _outside(labelled: pd.DataFrame, finding: dict) -> tuple[pd.DataFrame, str]:
    """The reviews a market-wide pattern does not cover (only its aspect is cut)."""
    if finding["kind"] == "seasonal":
        inside = labelled["date"].dt.month == finding["calendar_month"]
        where = f"outside {calendar.month_name[finding['calendar_month']]}"
    else:
        inside = labelled["date"].dt.to_period("M") >= pd.Period(finding["change_month"], "M")
        where = f"before {finding['change_month']}"
    return labelled[~((labelled["aspect"] == finding["aspect"]) & inside)], where


def _neighbourhood_detail(property_id: str, hood: dict) -> str:
    others = [m for m in hood["members"] if m != property_id]
    return (
        f"{hood['aspect']} fell at you and {len(others)} neighbours within "
        f"{hood['radius_km']:.2f} km ({', '.join(others)}) from {hood['change_month']}: "
        f"you {hood['gaps'][property_id]:+.2f} and the group {hood['delta']:+.2f} relative "
        f"to the rest of the market; a decline this concentrated in one place arises by "
        f"chance with p = {hood['p_value']:.3f}"
    )


def _whose_problem(
    labelled: pd.DataFrame,
    property_id: str,
    aspect: str,
    decline,
    findings: list[dict],
    near: dict[str, dict] | None = None,
) -> tuple[str, str]:
    """``yours alone`` | ``your neighbourhood's`` | ``everyone's`` | ``not tested``
    for one priority row.

    Derived for THIS property, never joined from ``market_scope`` by aspect: a
    property taking part in a significant neighbourhood-wide decline (``near``, by
    aspect) shares it with its neighbours; otherwise a market-adjusted decline is
    the property's own; a lag is re-tested with the market-wide patterns it takes
    part in set aside. It is ``everyone's`` only if the lag disappears without them.
    Below ``MIN_PROPERTIES_FOR_SCOPE`` properties there is no market to separate,
    so nothing is tested.
    """
    k = labelled.loc[labelled["aspect"] == aspect, "property_id"].nunique()
    if k < MIN_PROPERTIES_FOR_SCOPE:
        return "not tested", undetermined_note(int(k))
    shared = [f for f in findings if f["aspect"] == aspect and property_id in f["gaps"]]
    hood = (near or {}).get(aspect)
    # A market-wide pattern takes precedence: a decline the whole market shares is
    # not the neighbourhood's to solve.
    if hood is not None and property_id in hood["members"] and not shared:
        return "your neighbourhood's", _neighbourhood_detail(property_id, hood)
    also = "; ".join(f"the {describe_finding(f)} is everyone's" for f in shared)
    if decline is not None:
        detail = (
            f"you dropped {-decline['delta']:.2f} relative to the market from "
            f"{decline['change_month']}; the market itself moved {decline['market_delta']:+.2f}"
        )
        return "yours alone", detail + (f"; separately, {also}" if also else "")
    if not shared:
        return "yours alone", f"below the market, and no market-wide pattern on {aspect}"
    rest, where = labelled, []
    for f in shared:
        rest, w = _outside(rest, f)
        where.append(w)
    row = benchmark_vs_cluster(rest, property_id=property_id)
    row = row[row["aspect"] == aspect]
    where = " and ".join(where)
    if row.empty or row.iloc[0]["n_reviews"] < MIN_REVIEWS_FOR_FLAG:
        return "not tested", f"too few reviews {where} to separate you from the market"
    if row.iloc[0]["flag"] == "lag":
        gap = row.iloc[0]["cluster_mean"] - row.iloc[0]["mean"]
        return "yours alone", f"still {gap:.2f} below the market {where}; {also}"
    mine = "; ".join(
        f"your drop {f['gaps'][property_id]:.2f} vs {f['drop']:.2f} on average" for f in shared
    )
    patterns = "; ".join(describe_finding(f) for f in shared)
    return "everyone's", f"{patterns}; {where} you are on par with the market ({mine})"


def priority_actions(
    labelled: pd.DataFrame,
    property_id: str,
    top_n: int = 5,
    neighbourhoods: list[dict] | None = None,
) -> pd.DataFrame:
    """Rank the aspects a property should fix first.

    For each aspect, the *current level* is the property's mean since its latest
    significant decline (or its all-time mean if there is none). It is compared with:

    * ``basis == "cluster"``: the cluster mean over the same months, when enough
      properties review the aspect to form a market;
    * ``basis == "own history"``: the property's own mean before the decline, when
      too few properties review the aspect (e.g. a single-hotel upload).

    ``gap = reference - current`` (positive = worse), ``volume`` = the aspect's share
    of the property's mentions, ``impact_score = gap x volume``. Only aspects that are
    worse AND backed by evidence are listed: a significant decline, a lag flag
    (FDR-controlled) against the cluster, or membership of a significant
    neighbourhood-wide decline (``neighbourhoods``; its month is ``started``).

    ``whose_problem`` answers "is it me or the market?" for this property (see
    ``_whose_problem``); ``whose_detail`` says why. With fewer than 3 properties
    reviewing the aspect it is ``not tested``: there is no market to separate.
    """
    bench = benchmark_vs_cluster(labelled, property_id=property_id)
    if bench.empty:
        return pd.DataFrame(columns=PRIORITY_COLUMNS)
    cps = detect_changepoints(labelled)
    declines = cps[(cps["property_id"] == property_id) & (cps["direction"] == "negative")]
    latest = declines.sort_values("change_month").groupby("aspect").tail(1).set_index("aspect")
    own = labelled[labelled["property_id"] == property_id]
    total = len(own)
    findings = market_findings(labelled)
    near = {f["aspect"]: f for f in neighbourhoods or []}

    rows: list[dict] = []
    for r in bench.itertuples(index=False):
        started, basis, cp = None, "cluster", None
        if r.aspect in latest.index:
            cp = latest.loc[r.aspect]
            started = str(cp["change_month"])
            since = pd.Timestamp(f"{started}-01")
            series = own[own["aspect"] == r.aspect]
            current = float(series.loc[series["date"] >= since, "sentiment"].mean())
            if pd.isna(cp["market_delta"]):  # no market to compare with
                basis = "own history"
                reference = float(series.loc[series["date"] < since, "sentiment"].mean())
                evidence = (
                    "a significant decline in your own reviews; too few properties review "
                    f"{r.aspect} to compare with the market"
                )
            else:
                reference = _cluster_mean_since(labelled, r.aspect, since)
                evidence = "a significant decline relative to the market"
        elif r.aspect in near and property_id in near[r.aspect]["members"]:
            started = near[r.aspect]["change_month"]
            since = pd.Timestamp(f"{started}-01")
            series = own[own["aspect"] == r.aspect]
            current = float(series.loc[series["date"] >= since, "sentiment"].mean())
            reference = _cluster_mean_since(labelled, r.aspect, since)
            evidence = "a significant decline shared with your neighbours"
        elif r.flag == "lag":
            current, reference = float(r.mean), float(r.cluster_mean)
            evidence = (
                f"your 95% CI {r.ci_low:+.2f} to {r.ci_high:+.2f} lies below the cluster, "
                "significant after multiple-testing correction"
            )
        else:
            continue
        gap = reference - current
        if not gap > 0:
            continue
        volume = r.n / total
        whose = _whose_problem(labelled, property_id, r.aspect, cp, findings, near)
        compared = "the cluster" if basis == "cluster" else f"your level before {started}"
        when = f" since {started}" if started else ""
        rows.append(
            {
                "aspect": r.aspect,
                "gap": round(gap, 3),
                "volume": round(volume, 3),
                "impact_score": round(gap * volume, 4),
                "started": started,
                "rationale": (
                    f"{r.aspect} is {gap:.2f} below {compared}{when} "
                    f"(now {current:+.2f} vs {reference:+.2f}; {evidence}). "
                    f"It appears in {volume:.0%} of your aspect mentions."
                ),
                "current_mean": round(current, 3),
                "reference_mean": round(reference, 3),
                "basis": basis,
                "n": int(r.n),
                "whose_problem": whose[0],
                "whose_detail": whose[1],
            }
        )
    out = pd.DataFrame(rows, columns=PRIORITY_COLUMNS)
    out = out.sort_values(["impact_score", "aspect"], ascending=[False, True])
    out = out.head(top_n).reset_index(drop=True)
    out["started"] = none_for_missing(out["started"])
    return out


def destination_summary(
    labelled: pd.DataFrame, neighbourhoods: list[dict] | None = None
) -> pd.DataFrame:
    """Tourism-board view: one row per aspect across the whole cluster, worst first.

    ``scope`` is ``market-wide`` / ``neighbourhood-wide`` / ``property-specific``
    from the market analysis (``neighbourhood-wide`` needs ``neighbourhoods``),
    ``stable`` when no significant negative shift was found, and ``undetermined``
    when too few properties review the aspect to separate the market from one
    property. ``n_properties_reviewed`` counts properties with reviews on the aspect
    (unlike ``market_scope``'s ``n_properties``, which counts affected properties).
    """
    if labelled.empty:
        return pd.DataFrame(columns=DESTINATION_COLUMNS)
    cmeans = cluster_means(aspect_scores(labelled))
    stats = labelled.groupby("aspect").agg(
        n=("sentiment", "size"),
        pct_negative=("sentiment", lambda s: float((s < 0).mean())),
        n_properties_reviewed=("property_id", "nunique"),
    )
    scope = market_wide_summary(labelled, neighbourhoods=neighbourhoods).set_index("aspect")
    rows = []
    for aspect in stats.index:
        k = int(stats.at[aspect, "n_properties_reviewed"])
        if aspect in scope.index:
            label, pattern = scope.at[aspect, "scope"], scope.at[aspect, "pattern"]
        elif k < MIN_PROPERTIES_FOR_SCOPE:
            label, pattern = "undetermined", undetermined_note(k)
        else:
            label, pattern = "stable", "no significant negative shift"
        rows.append(
            {
                "aspect": aspect,
                "cluster_mean": round(float(cmeans[aspect]), 3),
                "n": int(stats.at[aspect, "n"]),
                "pct_negative": round(float(stats.at[aspect, "pct_negative"]), 3),
                "scope": label,
                "pattern": pattern,
                "n_properties_reviewed": k,
            }
        )
    out = pd.DataFrame(rows, columns=DESTINATION_COLUMNS)
    return out.sort_values(["cluster_mean", "aspect"]).reset_index(drop=True)
