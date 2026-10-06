"""A deliberately simple single mean-shift changepoint detector.

For an ordered 1-D series it finds the split that maximises the absolute
difference of segment means, subject to a minimum segment length, and reports it
only if the shift clears ``min_delta``. This is enough to recover an injected
step change; a fuller PELT/`ruptures` approach is on the Roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Changepoint:
    index: int  # split position: segments are [:index] and [index:]
    delta: float  # mean(after) - mean(before); negative = decline


def find_changepoint(
    values: list[float] | np.ndarray,
    min_size: int = 4,
    min_delta: float = 0.8,
) -> Changepoint | None:
    """Return the most significant mean shift, or None if below threshold."""
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n < 2 * min_size:
        return None

    best: Changepoint | None = None
    for i in range(min_size, n - min_size + 1):
        delta = float(arr[i:].mean() - arr[:i].mean())
        if best is None or abs(delta) > abs(best.delta):
            best = Changepoint(index=i, delta=delta)

    if best is not None and abs(best.delta) >= min_delta:
        return best
    return None
