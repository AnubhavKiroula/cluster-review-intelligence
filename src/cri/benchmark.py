"""Benchmarking, trends, and market-wide vs property-specific logic.

Operates on the long frame produced by :func:`cri.pipeline.label_reviews`
(columns: property_id, date, aspect, sentiment). The exact statistical rules are
documented in docs/methodology.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .changepoint import find_changepoint

# Flag thresholds (documented in methodology.md).
BENCHMARK_MARGIN = 0.05  # minimum |property - cluster| gap to call lead/lag
MARKET_WIDE_FRACTION = 0.6  # share of properties that must share a shift
SEASONAL_MIN_GAP = 0.5  # minimum sentiment gap for a seasonal dip
CHANGEPOINT_MIN_DELTA = 0.8


# --- Per property-aspect scores + cluster benchmark -----------------------------


def aspect_scores(labelled: pd.DataFrame) -> pd.DataFrame:
    """Mean sentiment, count, and standard error per (property, aspect)."""
    grouped = labelled.groupby(["property_id", "aspect"])["sentiment"]
    scores = grouped.agg(mean="mean", n="count", std="std").reset_index()
    scores["std"] = scores["std"].fillna(0.0)
    scores["se"] = scores["std"] / np.sqrt(scores["n"].clip(lower=1))
    return scores


def cluster_means(scores: pd.DataFrame) -> pd.Series:
    """Cluster mean per aspect = unweighted mean of per-property means."""
    return scores.groupby("aspect")["mean"].mean()


def benchmark_vs_cluster(labelled: pd.DataFrame) -> pd.DataFrame:
    """Flag each property-aspect as lead / lag / on_par vs the cluster.

    A normal-approximation 95% interval (mean ± 1.96*se) that excludes the cluster
    mean, together with a minimum gap, triggers lead/lag. Bootstrap CIs are on the
    Roadmap; this keeps the MVP transparent.
    """
    scores = aspect_scores(labelled)
    cmeans = cluster_means(scores)
    scores = scores.copy()
    scores["cluster_mean"] = scores["aspect"].map(cmeans)
    scores["diff"] = scores["mean"] - scores["cluster_mean"]
    lo = scores["mean"] - 1.96 * scores["se"]
    hi = scores["mean"] + 1.96 * scores["se"]

    def flag(row_lo: float, row_hi: float, diff: float, cmean: float) -> str:
        if diff > BENCHMARK_MARGIN and row_lo > cmean:
            return "lead"
        if diff < -BENCHMARK_MARGIN and row_hi < cmean:
            return "lag"
        return "on_par"

    scores["flag"] = [
        flag(lo.iloc[i], hi.iloc[i], scores["diff"].iloc[i], scores["cluster_mean"].iloc[i])
        for i in range(len(scores))
    ]
    return scores


# --- Monthly trends -------------------------------------------------------------


def monthly_series(labelled: pd.DataFrame, property_id: str, aspect: str) -> pd.Series:
    """Monthly mean sentiment for one property-aspect (month start index)."""
    mask = (labelled["property_id"] == property_id) & (labelled["aspect"] == aspect)
    sub = labelled.loc[mask]
    if sub.empty:
        return pd.Series(dtype=float)
    monthly = (
        sub.set_index("date")["sentiment"].resample("MS").mean().dropna()
    )
    return monthly


def detect_changepoints(
    labelled: pd.DataFrame, min_delta: float = CHANGEPOINT_MIN_DELTA
) -> pd.DataFrame:
    """Run the step-change detector for every property-aspect with enough data."""
    rows: list[dict] = []
    for (prop, aspect), _ in labelled.groupby(["property_id", "aspect"]):
        series = monthly_series(labelled, prop, aspect)
        cp = find_changepoint(series.to_numpy(), min_delta=min_delta)
        if cp is None:
            continue
        rows.append(
            {
                "property_id": prop,
                "aspect": aspect,
                "change_month": series.index[cp.index].strftime("%Y-%m"),
                "delta": round(cp.delta, 3),
                "direction": "negative" if cp.delta < 0 else "positive",
            }
        )
    return pd.DataFrame(
        rows,
        columns=["property_id", "aspect", "change_month", "delta", "direction"],
    )


def detect_seasonal_dips(
    labelled: pd.DataFrame, month: int = 12, min_gap: float = SEASONAL_MIN_GAP
) -> pd.DataFrame:
    """Flag property-aspects whose target-month sentiment is well below the rest."""
    df = labelled.copy()
    df["month"] = df["date"].dt.month
    rows: list[dict] = []
    for (prop, aspect), sub in df.groupby(["property_id", "aspect"]):
        target = sub.loc[sub["month"] == month, "sentiment"]
        other = sub.loc[sub["month"] != month, "sentiment"]
        if len(target) < 3 or len(other) < 3:
            continue
        gap = float(other.mean() - target.mean())
        if gap >= min_gap:
            rows.append(
                {
                    "property_id": prop,
                    "aspect": aspect,
                    "target_month": month,
                    "gap": round(gap, 3),
                }
            )
    return pd.DataFrame(rows, columns=["property_id", "aspect", "target_month", "gap"])


# --- Market-wide vs property-specific ------------------------------------------


def market_wide_summary(
    labelled: pd.DataFrame, min_fraction: float = MARKET_WIDE_FRACTION
) -> pd.DataFrame:
    """Classify each aspect's negative shifts as market-wide or property-specific.

    A property-aspect counts as having a negative shift if it shows either a
    negative step change or a December seasonal dip. An aspect is market-wide when
    at least ``min_fraction`` of properties share that shift.
    """
    n_props = labelled["property_id"].nunique()
    cps = detect_changepoints(labelled)
    neg_cps = cps[cps["direction"] == "negative"]
    dips = detect_seasonal_dips(labelled)

    shifted: dict[str, set[str]] = {}
    for _, r in neg_cps.iterrows():
        shifted.setdefault(r["aspect"], set()).add(r["property_id"])
    for _, r in dips.iterrows():
        shifted.setdefault(r["aspect"], set()).add(r["property_id"])

    rows: list[dict] = []
    for aspect, props in sorted(shifted.items()):
        fraction = len(props) / n_props
        scope = "market-wide" if fraction >= min_fraction else "property-specific"
        rows.append(
            {
                "aspect": aspect,
                "n_properties": len(props),
                "fraction": round(fraction, 3),
                "scope": scope,
                "properties": ", ".join(sorted(props)),
            }
        )
    return pd.DataFrame(
        rows, columns=["aspect", "n_properties", "fraction", "scope", "properties"]
    )
