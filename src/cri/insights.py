"""Decision-ready summaries built on the benchmark: what to fix first, and the
destination (tourism-board) view. Rules are documented in docs/methodology.md.
"""

from __future__ import annotations

import pandas as pd

from .benchmark import (
    MIN_PROPERTIES_FOR_SCOPE,
    aspect_scores,
    benchmark_vs_cluster,
    cluster_means,
    detect_changepoints,
    market_wide_summary,
    none_for_missing,
    undetermined_note,
)

PRIORITY_COLUMNS = [
    "aspect", "gap", "volume", "impact_score", "started", "rationale",
    "current_mean", "reference_mean", "basis", "n",
]
DESTINATION_COLUMNS = [
    "aspect", "cluster_mean", "n", "pct_negative", "scope", "pattern", "n_properties_reviewed",
]


def _cluster_mean_since(labelled: pd.DataFrame, aspect: str, since: pd.Timestamp) -> float:
    """Cluster mean for one aspect over [since, end] (unweighted mean of property means)."""
    window = labelled[(labelled["aspect"] == aspect) & (labelled["date"] >= since)]
    return float(window.groupby("property_id")["sentiment"].mean().mean())


def priority_actions(labelled: pd.DataFrame, property_id: str, top_n: int = 5) -> pd.DataFrame:
    """Rank the aspects a property should fix first.

    For each aspect, the *current level* is the property's mean since its latest
    significant decline (or its all-time mean if there is none). It is compared with:

    * ``basis == "cluster"``: the cluster mean over the same months, when enough
      properties review the aspect to form a market;
    * ``basis == "own history"``: the property's own mean before the decline, when
      too few properties review the aspect (e.g. a single-hotel upload).

    ``gap = reference - current`` (positive = worse), ``volume`` = the aspect's share
    of the property's mentions, ``impact_score = gap x volume``. Only aspects that are
    worse AND backed by evidence are listed: a significant decline, or a lag flag
    (FDR-controlled) against the cluster.
    """
    bench = benchmark_vs_cluster(labelled, property_id=property_id)
    if bench.empty:
        return pd.DataFrame(columns=PRIORITY_COLUMNS)
    cps = detect_changepoints(labelled)
    declines = cps[(cps["property_id"] == property_id) & (cps["direction"] == "negative")]
    latest = declines.sort_values("change_month").groupby("aspect").tail(1).set_index("aspect")
    own = labelled[labelled["property_id"] == property_id]
    total = len(own)

    rows: list[dict] = []
    for r in bench.itertuples(index=False):
        started, basis = None, "cluster"
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
            }
        )
    out = pd.DataFrame(rows, columns=PRIORITY_COLUMNS)
    out = out.sort_values(["impact_score", "aspect"], ascending=[False, True])
    out = out.head(top_n).reset_index(drop=True)
    out["started"] = none_for_missing(out["started"])
    return out


def destination_summary(labelled: pd.DataFrame) -> pd.DataFrame:
    """Tourism-board view: one row per aspect across the whole cluster, worst first.

    ``scope`` is ``market-wide`` / ``property-specific`` from the market analysis,
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
    scope = market_wide_summary(labelled).set_index("aspect")
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
