"""Stable facade over the analytics core - the ONLY ``cri`` module the dashboard imports.

Contract: docs/HACKATHON_PLAN.md section 3.2. Every function there keeps its
signature and documented columns. Additive extensions (Day 0, agreed in the PR):

* ``ClusterData.reviews`` has a ``review_id`` column and ``labelled`` carries it too,
  so every mention links back to its review (used by ``search_reviews``).
* Extra columns: ``property_scorecard`` -> ``n_reviews``; ``changepoints`` ->
  ``raw_delta, market_delta, p_value, q_value``; ``market_scope`` -> ``pattern``;
  ``destination_summary`` -> ``pattern, n_properties``; ``priority_actions`` ->
  ``current_mean, cluster_mean, n``.
* Scope values: ``market_scope`` may return ``undetermined`` (fewer than 3
  properties); ``destination_summary`` also uses ``stable`` (no negative shift).

All functions are pure: they never mutate ``ClusterData``. In Streamlit, cache
``load_cluster`` and the heavier calls with ``st.cache_data``.
Unknown property/aspect names or invalid arguments raise ``ValueError`` naming
the valid options; empty results are empty frames with the documented columns.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import benchmark as _benchmark
from . import insights as _insights
from .classify import get_classifier, load_aspects
from .generate import generate
from .loader import load_dir, load_reviews
from .pipeline import label_reviews
from .schema import validate_reviews

SCORECARD_COLUMNS = [
    "aspect", "mean", "ci_low", "ci_high", "n", "cluster_mean", "diff", "flag", "n_reviews",
]
TREND_COLUMNS = ["month", "mean", "n"]
SEARCH_COLUMNS = [
    "review_id", "property_id", "date", "platform", "rating", "language_hint",
    "aspect", "sentiment", "sentence", "text",
]


@dataclass(frozen=True)
class ClusterData:
    reviews: pd.DataFrame  # schema-validated raw reviews, with a review_id column
    labelled: pd.DataFrame  # review_id, property_id, date, aspect, sentiment, sentence
    is_synthetic: bool
    source_name: str  # shown in the UI banner


# --- Loading ------------------------------------------------------------------------


def _with_review_ids(reviews: pd.DataFrame) -> pd.DataFrame:
    reviews = reviews.reset_index(drop=True)
    if "review_id" not in reviews.columns:
        return reviews.assign(review_id=range(len(reviews)))
    ids = reviews["review_id"]
    if ids.isna().any() or ids.duplicated().any():
        raise ValueError(
            "Column 'review_id' must be unique and non-empty "
            "(duplicates often mean several files reuse the same ids)."
        )
    return reviews


def _mentions_synthetic(*names: str) -> bool:
    # CLAUDE.md rule 2: synthetic data always carries "synthetic" in its filename.
    return any("synthetic" in name.lower() for name in names)


def _files_in(directory: Path) -> list[str]:
    return [p.name for p in directory.iterdir() if p.suffix.lower() in {".csv", ".json", ".jsonl"}]


def load_cluster(path=None, *, synthetic=True, seed=42) -> ClusterData:
    """Load, validate, and label a cluster's reviews.

    * ``path`` given: a CSV/JSON(L) file or a directory of them.
    * no ``path``, ``synthetic=True``: generate the SYNTHETIC sample in memory.
    * no ``path``, ``synthetic=False``: every file in ``$CRI_DATA_RAW_DIR``
      (default ``data/raw``).

    ``is_synthetic`` is True whenever any source filename contains "synthetic", so
    the dashboard banner also appears for ``data/sample/synthetic_reviews.csv``.
    The classifier backend follows ``CRI_MODEL_BACKEND`` (default ``rule``).
    """
    if path is not None:
        p = Path(path)
        if p.is_dir():
            reviews = load_dir(p)
            is_synthetic = _mentions_synthetic(p.name, *_files_in(p))
        else:
            reviews = load_reviews(p)
            is_synthetic = _mentions_synthetic(p.name)
        source = p.name or str(p)
    elif synthetic:
        reviews = validate_reviews(generate(seed=seed))
        is_synthetic, source = True, f"SYNTHETIC sample (seed {seed})"
    else:
        raw = Path(os.environ.get("CRI_DATA_RAW_DIR", "data/raw"))
        reviews = load_dir(raw)
        is_synthetic, source = _mentions_synthetic(raw.name, *_files_in(raw)), str(raw)

    reviews = _with_review_ids(reviews)
    labelled = label_reviews(reviews, classifier=get_classifier())
    return ClusterData(reviews, labelled, is_synthetic, source)


# --- Lookups ------------------------------------------------------------------------


def list_properties(d: ClusterData) -> list[str]:
    return sorted(str(p) for p in d.reviews["property_id"].unique())


def list_aspects() -> list[str]:
    """Aspect names in taxonomy order (``aspects.yaml``)."""
    return list(load_aspects())


def date_range(d: ClusterData) -> tuple[pd.Timestamp, pd.Timestamp]:
    dates = d.reviews["date"]
    return (pd.Timestamp(dates.min()), pd.Timestamp(dates.max()))


def _check_property(d: ClusterData, property_id: str) -> None:
    valid = list_properties(d)
    if property_id not in valid:
        raise ValueError(f"Unknown property_id {property_id!r}. Valid: {valid}")


def _check_aspect(aspect: str) -> None:
    valid = list_aspects()
    if aspect not in valid:
        raise ValueError(f"Unknown aspect {aspect!r}. Valid: {valid}")


def _taxonomy_order(frame: pd.DataFrame) -> pd.DataFrame:
    rank = {a: i for i, a in enumerate(list_aspects())}
    order = frame["aspect"].map(rank).fillna(len(rank))
    return frame.iloc[order.argsort(kind="stable")].reset_index(drop=True)


# --- Analyses -----------------------------------------------------------------------


def property_scorecard(d: ClusterData, property_id: str) -> pd.DataFrame:
    """aspect, mean, ci_low, ci_high, n, cluster_mean, diff, flag (lead|lag|on_par).

    One row per aspect the property is mentioned for, in taxonomy order.
    """
    _check_property(d, property_id)
    bench = _benchmark.benchmark_vs_cluster(d.labelled, property_id=property_id)
    return _taxonomy_order(bench)[SCORECARD_COLUMNS]


def cluster_matrix(d: ClusterData) -> pd.DataFrame:
    """index=property_id, columns=aspect (taxonomy order), values=mean sentiment."""
    scores = _benchmark.aspect_scores(d.labelled)
    matrix = scores.pivot(index="property_id", columns="aspect", values="mean")
    present = [a for a in list_aspects() if a in matrix.columns]
    matrix = matrix.reindex(index=list_properties(d), columns=present)
    matrix.columns.name = "aspect"
    matrix.index.name = "property_id"
    return matrix


def trend(d: ClusterData, property_id: str, aspect: str) -> pd.DataFrame:
    """month, mean, n for one property-aspect (months with at least one mention)."""
    _check_property(d, property_id)
    _check_aspect(aspect)
    lab = d.labelled
    sub = lab[(lab["property_id"] == property_id) & (lab["aspect"] == aspect)]
    if sub.empty:
        return pd.DataFrame(columns=TREND_COLUMNS)
    monthly = sub.set_index("date")["sentiment"].resample("MS").agg(["mean", "count"])
    monthly = monthly[monthly["count"] > 0]
    return pd.DataFrame(
        {
            "month": monthly.index,
            "mean": monthly["mean"].to_numpy(dtype=float),
            "n": monthly["count"].to_numpy(dtype="int64"),
        }
    )


def changepoints(d: ClusterData, property_id=None, aspect=None) -> pd.DataFrame:
    """property_id, aspect, change_month, delta, direction (+ raw/market delta, p, q).

    Significance is always computed over every series, then filtered, so q-values
    do not depend on which property the caller asks about.
    """
    if property_id is not None:
        _check_property(d, property_id)
    if aspect is not None:
        _check_aspect(aspect)
    cps = _benchmark.detect_changepoints(d.labelled)
    if property_id is not None:
        cps = cps[cps["property_id"] == property_id]
    if aspect is not None:
        cps = cps[cps["aspect"] == aspect]
    return cps.reset_index(drop=True)


def market_scope(d: ClusterData) -> pd.DataFrame:
    """aspect, scope (market-wide|property-specific|undetermined), fraction,
    n_properties, properties, pattern. Aspects with no negative shift are omitted."""
    return _benchmark.market_wide_summary(d.labelled)


def destination_summary(d: ClusterData) -> pd.DataFrame:
    """aspect, cluster_mean, n, pct_negative, scope (+ pattern, n_properties)."""
    return _insights.destination_summary(d.labelled)


def priority_actions(d: ClusterData, property_id: str, top_n: int = 5) -> pd.DataFrame:
    """aspect, gap, volume, impact_score, started, rationale -> "fix this first"."""
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError(f"top_n must be a positive integer, got {top_n!r}")
    _check_property(d, property_id)
    return _insights.priority_actions(d.labelled, property_id, top_n=top_n)


def search_reviews(
    d: ClusterData,
    property_id=None,
    aspect=None,
    sentiment=None,
    start=None,
    end=None,
    query: str | None = None,
) -> pd.DataFrame:
    """Filtered reviews for the explorer, one row per (review, matched clause).

    ``aspect``/``sentiment`` filter on the classified clauses; without them, reviews
    with no detected aspect are kept (empty ``aspect``) so misses can be audited.
    ``start``/``end`` are inclusive dates. ``query`` is a literal, case-insensitive
    substring of the review text. Newest first.
    """
    if property_id is not None:
        _check_property(d, property_id)
    if aspect is not None:
        _check_aspect(aspect)
    if sentiment is not None and (isinstance(sentiment, bool) or sentiment not in (-1, 0, 1)):
        raise ValueError(f"sentiment must be -1, 0, or 1, got {sentiment!r}")

    reviews = d.reviews
    if property_id is not None:
        reviews = reviews[reviews["property_id"] == property_id]
    day = reviews["date"].dt.normalize()
    if start is not None:
        reviews = reviews[day >= pd.Timestamp(start).normalize()]
        day = reviews["date"].dt.normalize()
    if end is not None:
        reviews = reviews[day <= pd.Timestamp(end).normalize()]
    if query:
        reviews = reviews[reviews["text"].str.contains(query, case=False, regex=False, na=False)]

    mentions = d.labelled[["review_id", "aspect", "sentiment", "sentence"]]
    if aspect is not None:
        mentions = mentions[mentions["aspect"] == aspect]
    if sentiment is not None:
        mentions = mentions[mentions["sentiment"] == sentiment]
    how = "inner" if aspect is not None or sentiment is not None else "left"
    out = reviews.merge(mentions, on="review_id", how=how)
    out = out.assign(sentiment=out["sentiment"].astype("Int64"))
    out = out.sort_values(["date", "review_id"], ascending=[False, True])
    return out[SEARCH_COLUMNS].reset_index(drop=True)
