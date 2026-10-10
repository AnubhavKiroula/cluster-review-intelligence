"""Fast synthetic labelled frames for statistical tests (no text, no classifier).

Each simulated review mentions one aspect once with sentiment +1 or -1, so the
review-level unit equals the mention. Everything is seeded and deterministic.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

LABELLED_COLUMNS = ["review_id", "property_id", "date", "aspect", "sentiment", "sentence"]


def simulate(
    spec: dict[str, Callable[[pd.Timestamp], float | None]],
    *,
    start: str = "2024-01",
    end: str = "2025-12",
    aspect: str = "Food",
    per_month: int | dict[str, int] = 15,
    seed: int = 0,
) -> pd.DataFrame:
    """``spec`` maps property_id -> f(month) giving P(positive), or None when the
    property has no reviews that month (e.g. it has not opened yet)."""
    rng = np.random.default_rng(seed)
    months = pd.period_range(start, end, freq="M").to_timestamp()
    frames = []
    for prop, p_of in spec.items():
        volume = per_month[prop] if isinstance(per_month, dict) else per_month
        for month in months:
            p = p_of(month)
            if p is None:
                continue
            days = rng.integers(1, 28, size=volume)
            frames.append(
                pd.DataFrame(
                    {
                        "property_id": prop,
                        "date": [month.replace(day=int(d)) for d in days],
                        "aspect": aspect,
                        "sentiment": np.where(rng.random(volume) < p, 1, -1),
                        "sentence": "",
                    }
                )
            )
    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "review_id", np.arange(len(out)))
    return out[LABELLED_COLUMNS]


def constant(p: float) -> Callable[[pd.Timestamp], float]:
    return lambda month: p


def step(before: float, after: float, at: str) -> Callable[[pd.Timestamp], float]:
    at_ts = pd.Timestamp(at)
    return lambda month: after if month >= at_ts else before


def starting(p: float, at: str) -> Callable[[pd.Timestamp], float | None]:
    at_ts = pd.Timestamp(at)
    return lambda month: p if month >= at_ts else None
