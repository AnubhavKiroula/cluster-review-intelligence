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
)

PRIORITY_COLUMNS = [
    "aspect", "gap", "volume", "impact_score", "started", "rationale",
    "current_mean", "cluster_mean", "n",
]
DESTINATION_COLUMNS = [
    "aspect", "cluster_mean", "n", "pct_negative", "scope", "pattern", "n_properties",
]


def _cluster_mean_since(labelled: pd.DataFrame, aspect: str, since: pd.Timestamp) -> float:
    """Cluster mean for one aspect over [since, end] (unweighted mean of property means)."""
    window = labelled[(labelled["aspect"] == aspect) & (labelled["date"] >= since)]
    return float(window.groupby("property_id")["sentiment"].mean().mean())


def priority_actions(labelled: pd.DataFrame, property_id: str, top_n: int = 5) -> pd.DataFrame:
    """Rank the aspects a property should fix first.

    For each aspect, the *current level* is the property's mean since its latest
    significant decline relative to the market (or its all-time mean if there is
    none), and the *reference* is the cluster mean over the same months.
    ``gap = reference - current`` (positive = behind), ``volume`` = the aspect's share
    of the property's mentions, and ``impact_score = gap x volume``. An aspect is only
    listed when it is behind the cluster AND the evidence supports it: a
    statistically supported lag (bootstrap CI) or a significant decline.
    """
    bench = benchmark_vs_cluster(labelled, property_id=property_id)
    if bench.empty:
        return pd.DataFrame(columns=PRIORITY_COLUMNS)
    cps = detect_changepoints(labelled)
    declines = cps[(cps["property_id"] == property_id) & (cps["direction"] == "negative")]
    latest = declines.groupby("aspect")["change_month"].max().to_dict()
    own = labelled[labelled["property_id"] == property_id]
    total = len(own)

    rows: list[dict] = []
    for r in bench.itertuples(index=False):
        started = latest.get(r.aspect)
        if started is not None:
            since = pd.Timestamp(f"{started}-01")
            recent = own[(own["aspect"] == r.aspect) & (own["date"] >= since)]["sentiment"]
            current = float(recent.mean())
            reference = _cluster_mean_since(labelled, r.aspect, since)
        else:
            current, reference = float(r.mean), float(r.cluster_mean)
        gap = reference - current
        if not (gap > 0 and (r.flag == "lag" or started is not None)):
            continue
        volume = r.n / total
        when = f"since {started}" if started else "overall"
        evidence = (
            "a significant decline relative to the market"
            if started
            else f"your 95% CI {r.ci_low:+.2f} to {r.ci_high:+.2f} lies below the cluster"
        )
        rows.append(
            {
                "aspect": r.aspect,
                "gap": round(gap, 3),
                "volume": round(volume, 3),
                "impact_score": round(gap * volume, 4),
                "started": started,
                "rationale": (
                    f"{r.aspect} is {gap:.2f} below the cluster {when} "
                    f"(you {current:+.2f} vs cluster {reference:+.2f}; {evidence}). "
                    f"It appears in {volume:.0%} of your aspect mentions."
                ),
                "current_mean": round(current, 3),
                "cluster_mean": round(reference, 3),
                "n": int(r.n),
            }
        )
    out = pd.DataFrame(rows, columns=PRIORITY_COLUMNS)
    out = out.sort_values(["impact_score", "aspect"], ascending=[False, True])
    return out.head(top_n).reset_index(drop=True)


def destination_summary(labelled: pd.DataFrame) -> pd.DataFrame:
    """Tourism-board view: one row per aspect across the whole cluster, worst first.

    ``scope`` is ``market-wide`` / ``property-specific`` from the market analysis,
    ``stable`` when no significant negative shift was found, and ``undetermined``
    when the cluster is too small to separate the market from one property.
    """
    if labelled.empty:
        return pd.DataFrame(columns=DESTINATION_COLUMNS)
    cmeans = cluster_means(aspect_scores(labelled))
    stats = labelled.groupby("aspect").agg(
        n=("sentiment", "size"),
        pct_negative=("sentiment", lambda s: float((s < 0).mean())),
        n_properties=("property_id", "nunique"),
    )
    scope = market_wide_summary(labelled).set_index("aspect")
    too_small = labelled["property_id"].nunique() < MIN_PROPERTIES_FOR_SCOPE
    rows = []
    for aspect in stats.index:
        if too_small:
            label, pattern = "undetermined", "too few properties to separate market from property"
        elif aspect in scope.index:
            label, pattern = scope.at[aspect, "scope"], scope.at[aspect, "pattern"]
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
                "n_properties": int(stats.at[aspect, "n_properties"]),
            }
        )
    out = pd.DataFrame(rows, columns=DESTINATION_COLUMNS)
    return out.sort_values(["cluster_mean", "aspect"]).reset_index(drop=True)
