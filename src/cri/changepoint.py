"""Significance-tested single changepoint detection, plus the small statistics
toolkit the benchmark needs (Student-t tail, Benjamini-Hochberg q-values).

numpy/stdlib only: no scipy dependency. Rules and their justification are in
docs/methodology.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# --- Student-t tail via the regularised incomplete beta function -------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        for aa in (
            m * (b - m) * x / ((qam + m2) * (a + m2)),
            -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2)),
        ):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + aa / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _betacf(a, b, x) / a
    return 1.0 - math.exp(log_front) * _betacf(b, a, 1.0 - x) / b


def t_sf(t: float, df: float) -> float:
    """Upper tail P(T > t) of Student's t with ``df`` degrees of freedom."""
    if math.isnan(t) or df <= 0:
        return math.nan
    if math.isinf(t):
        return 0.0 if t > 0 else 1.0
    tail = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return tail if t > 0 else 1.0 - tail


def bh_qvalues(p_values: list[float] | np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (q-values), in the input order."""
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        return p
    order = np.argsort(p, kind="stable")
    ranked = p[order] * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adjusted, 1.0)
    return out


# --- Single changepoint on monthly aggregates --------------------------------------


@dataclass(frozen=True)
class Changepoint:
    index: int  # first month of the "after" segment (segments are [:index], [index:])
    delta: float  # mean(after) - mean(before) of the tested values; negative = decline
    raw_delta: float  # the same shift on the untransformed values
    p_value: float  # two-sided, Bonferroni-adjusted over the candidate splits


def find_changepoint(
    n: np.ndarray,
    s: np.ndarray,
    ss: np.ndarray,
    raw_s: np.ndarray | None = None,
    *,
    market_weight: np.ndarray | None = None,
    min_months: int = 4,
    min_units: int = 10,
) -> Changepoint | None:
    """Most significant single mean shift in a monthly-aggregated series.

    Per month (in time order, months with data only): ``n`` = number of units,
    ``s`` = sum and ``ss`` = sum of squares of the tested values, ``raw_s`` = sum of
    the untransformed values (defaults to ``s``). Every month boundary leaving
    ``min_months`` months and ``min_units`` units on each side is a candidate; each
    gets a pooled-variance two-sample t statistic. The best split's two-sided p-value
    is Bonferroni-adjusted for the number of candidates. Returns None when no split
    is admissible. The caller applies cross-series FDR control and an effect floor.

    ``market_weight`` (per month, ``1 / L`` where L units estimated a market mean
    that was subtracted from that month's values) adds the variance of that shared
    estimate: every unit in a month carries the same market error, so a segment mean
    has extra variance ``sigma^2 * sum_t (n_t / n_segment)^2 / L_t``. Ignoring it makes
    the test anti-conservative.
    """
    n = np.asarray(n, dtype=float)
    s = np.asarray(s, dtype=float)
    ss = np.asarray(ss, dtype=float)
    raw_s = s if raw_s is None else np.asarray(raw_s, dtype=float)
    weight = np.zeros_like(n) if market_weight is None else np.asarray(market_weight, float)
    months = len(n)
    if months < 2 * min_months:
        return None

    cn, cs, css, craw = np.cumsum(n), np.cumsum(s), np.cumsum(ss), np.cumsum(raw_s)
    cmk = np.cumsum(n * n * weight)
    total_n = cn[-1]
    k = np.arange(min_months, months - min_months + 1)
    n1 = cn[k - 1]
    k = k[(n1 >= min_units) & (total_n - n1 >= min_units)]
    if len(k) == 0 or total_n < 3:
        return None

    n1, n2 = cn[k - 1], total_n - cn[k - 1]
    s1 = cs[k - 1]
    m1, m2 = s1 / n1, (cs[-1] - s1) / n2
    within = np.maximum(css[k - 1] - n1 * m1 * m1, 0.0) + np.maximum(
        (css[-1] - css[k - 1]) - n2 * m2 * m2, 0.0
    )
    dof = total_n - 2
    market_1 = cmk[k - 1] / (n1 * n1)
    market_2 = (cmk[-1] - cmk[k - 1]) / (n2 * n2)
    se = np.sqrt(within / dof * (1.0 / n1 + 1.0 / n2 + market_1 + market_2))
    diff = m2 - m1
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, diff / se, np.where(diff != 0, np.inf * np.sign(diff), 0.0))

    best = int(np.argmax(np.abs(t)))
    split = int(k[best])
    p_one_split = 2.0 * t_sf(float(abs(t[best])), float(dof))
    raw_before = craw[split - 1] / n1[best]
    raw_after = (craw[-1] - craw[split - 1]) / n2[best]
    return Changepoint(
        index=split,
        delta=float(diff[best]),
        raw_delta=float(raw_after - raw_before),
        p_value=float(min(1.0, len(k) * p_one_split)),
    )
