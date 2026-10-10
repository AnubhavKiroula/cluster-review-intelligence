"""Benchmarking, trends, and market-wide vs property-specific logic.

Operates on the long frame produced by :func:`cri.pipeline.label_reviews`
(columns: review_id, property_id, date, aspect, sentiment, sentence).

Two questions, each tested at the level it is about (rules in docs/methodology.md):

* "Is it me?"  -> a property's sentiment *relative to the rest of the market*
  (leave-one-out cluster mean) is tested for a step change.
* "Is it the market?" -> properties are the independent replicates; a seasonal dip
  or a step change counts as market-wide only when it holds across properties.

Mentions from the same review are correlated, so every significance test and the
bootstrap use one unit per (review, aspect) rather than one per mention.
"""

from __future__ import annotations

import calendar
import zlib

import numpy as np
import pandas as pd

from .changepoint import bh_qvalues, find_changepoint, t_sf

# --- Thresholds (all documented in docs/methodology.md) -------------------------

BENCHMARK_MARGIN = 0.05  # minimum |property - cluster| gap to call lead/lag
MIN_REVIEWS_FOR_FLAG = 10  # below this a CI is too unstable to flag lead/lag
BOOTSTRAP_SAMPLES = 2000
CI_LEVEL = 0.95
FDR_Q = 0.05  # Benjamini-Hochberg false-discovery rate for every test family
CHANGEPOINT_MIN_EFFECT = 0.4  # |shift vs market| >= 0.4 ~ 20% of reviews flipping polarity
CHANGEPOINT_MIN_MONTHS = 4  # months on each side of a split
CHANGEPOINT_MIN_UNITS = 10  # reviews on each side of a split
MARKET_WIDE_FRACTION = 0.6  # share of properties that must share a market pattern
MARKET_MIN_EFFECT = 0.3  # a property "participates" if its drop is >= 0.3 (~15% flipping)
MIN_PROPERTIES_FOR_SCOPE = 3  # with fewer properties "me vs market" is undetermined
SEASONAL_MIN_MONTH_UNITS = 3  # reviews in the calendar month, per property
SEASONAL_MIN_REST_UNITS = 10  # reviews in the rest of the year, per property
STEP_MIN_SIDE_UNITS = 5  # reviews per property on each side of a market step split

CHANGEPOINT_COLUMNS = [
    "property_id", "aspect", "change_month", "delta", "direction",
    "raw_delta", "market_delta", "p_value", "q_value",
]
MARKET_PATTERN_COLUMNS = [
    "aspect", "kind", "calendar_month", "change_month", "drop",
    "n_tested", "n_participating", "share", "properties", "p_value", "q_value",
]
SEASONAL_COLUMNS = ["property_id", "aspect", "target_month", "gap", "q_value"]
SCOPE_COLUMNS = ["aspect", "n_properties", "fraction", "scope", "properties", "pattern"]


# --- Units --------------------------------------------------------------------------


def review_units(labelled: pd.DataFrame) -> pd.DataFrame:
    """One row per (review, aspect): ``value`` = mean sentiment of its clauses.

    Frames without ``review_id`` (older callers) fall back to one unit per
    (property, date, aspect), which merges same-day reviews and is conservative.
    """
    if "review_id" in labelled.columns:
        grouped = labelled.groupby(["review_id", "property_id", "aspect"], sort=False)
        units = grouped.agg(
            date=("date", "first"), total=("sentiment", "sum"), mentions=("sentiment", "size")
        ).reset_index()
    else:
        grouped = labelled.groupby(["property_id", "date", "aspect"], sort=False)
        units = grouped.agg(
            total=("sentiment", "sum"), mentions=("sentiment", "size")
        ).reset_index()
    return units.assign(value=units["total"] / units["mentions"])


def _group_seed(property_id: str, aspect: str) -> int:
    """Stable per-group seed (Python's hash() is salted per process)."""
    return zlib.crc32(f"{property_id}|{aspect}".encode())


def bootstrap_mean_ci(
    sums: np.ndarray,
    counts: np.ndarray,
    *,
    n_boot: int = BOOTSTRAP_SAMPLES,
    level: float = CI_LEVEL,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile CI for a mention-level mean, resampling whole reviews.

    ``sums``/``counts`` are each review's sentiment total and mention count, so the
    point estimate equals the plain mention mean while the interval reflects that
    mentions from one review are not independent (a cluster bootstrap).
    """
    sums = np.asarray(sums, dtype=float)
    counts = np.asarray(counts, dtype=float)
    r = len(sums)
    if r == 0:
        return (float("nan"), float("nan"))
    if r == 1:
        point = float(sums[0] / counts[0])
        return (point, point)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    chunk = max(1, min(n_boot, 2_000_000 // r))  # bound memory on large real groups
    for start in range(0, n_boot, chunk):
        idx = rng.integers(0, r, size=(min(chunk, n_boot - start), r), dtype=np.int64)
        means[start:start + len(idx)] = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    tail = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [tail, 1.0 - tail], method="linear")
    return (float(lo), float(hi))


# --- Per property-aspect scores + cluster benchmark ---------------------------------


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


def benchmark_vs_cluster(labelled: pd.DataFrame, property_id: str | None = None) -> pd.DataFrame:
    """Flag each property-aspect as lead / lag / on_par vs the cluster.

    Adds a review-level bootstrap CI (``ci_low``/``ci_high``). A flag needs at least
    ``MIN_REVIEWS_FOR_FLAG`` reviews, a gap above ``BENCHMARK_MARGIN``, and a CI that
    excludes the cluster mean. Pass ``property_id`` to bootstrap only that property;
    results are identical to the full run because each group has its own seed.
    """
    scores = aspect_scores(labelled)
    cmeans = cluster_means(scores)
    units = review_units(labelled)
    if property_id is not None:
        scores = scores[scores["property_id"] == property_id]
        units = units[units["property_id"] == property_id]
    by_group = {
        key: (g["total"].to_numpy(dtype=float), g["mentions"].to_numpy(dtype=float))
        for key, g in units.groupby(["property_id", "aspect"])
    }
    empty = np.empty(0)
    lows, highs, n_reviews = [], [], []
    for prop, aspect in zip(scores["property_id"], scores["aspect"], strict=True):
        sums, counts = by_group.get((prop, aspect), (empty, empty))
        lo, hi = bootstrap_mean_ci(sums, counts, seed=_group_seed(prop, aspect))
        lows.append(lo)
        highs.append(hi)
        n_reviews.append(len(sums))

    out = scores.assign(
        n_reviews=np.asarray(n_reviews, dtype="int64"),
        ci_low=lows,
        ci_high=highs,
        cluster_mean=scores["aspect"].map(cmeans),
    )
    out["diff"] = out["mean"] - out["cluster_mean"]
    enough = out["n_reviews"] >= MIN_REVIEWS_FOR_FLAG
    lead = enough & (out["diff"] > BENCHMARK_MARGIN) & (out["ci_low"] > out["cluster_mean"])
    lag = enough & (out["diff"] < -BENCHMARK_MARGIN) & (out["ci_high"] < out["cluster_mean"])
    out["flag"] = np.select([lead, lag], ["lead", "lag"], default="on_par")
    return out.reset_index(drop=True)


# --- Monthly trends -----------------------------------------------------------------


def monthly_series(labelled: pd.DataFrame, property_id: str, aspect: str) -> pd.Series:
    """Monthly mean sentiment for one property-aspect (month start index)."""
    mask = (labelled["property_id"] == property_id) & (labelled["aspect"] == aspect)
    sub = labelled.loc[mask]
    if sub.empty:
        return pd.Series(dtype=float)
    return sub.set_index("date")["sentiment"].resample("MS").mean().dropna()




# --- "Is it me?": property-vs-market changepoints -----------------------------------


def _changepoints_from_units(units: pd.DataFrame, min_effect: float, q: float) -> pd.DataFrame:
    if units.empty:
        return pd.DataFrame(columns=CHANGEPOINT_COLUMNS)
    u = units.assign(month=units["date"].dt.to_period("M"), sq=units["value"] ** 2)
    g = u.groupby(["property_id", "aspect", "month"], as_index=False, sort=True).agg(
        n=("value", "size"), s=("value", "sum"), ss=("sq", "sum")
    )
    if units["property_id"].nunique() >= MIN_PROPERTIES_FOR_SCOPE:
        totals = g.groupby(["aspect", "month"])[["n", "s"]].transform("sum")
        loo_n, loo_s = totals["n"] - g["n"], totals["s"] - g["s"]
        has_market = (loo_n > 0).to_numpy()
        g = g[has_market]
        market = (loo_s[has_market] / loo_n[has_market]).to_numpy(dtype=float)
        market_weight = 1.0 / loo_n[has_market].to_numpy(dtype=float)
    else:
        # Too few properties for a meaningful market reference: test the raw series,
        # so a single hotel still sees its own changes (market_delta is undefined).
        market = market_weight = None
    n = g["n"].to_numpy(dtype=float)
    s = g["s"].to_numpy(dtype=float)
    ss = g["ss"].to_numpy(dtype=float)
    if market is None:
        rs, rss = s, ss
    else:
        # Exact algebra for sums of (value - market) and (value - market)^2 per month.
        rs = s - n * market
        rss = ss - 2 * market * s + n * market * market
    months = g["month"].dt.strftime("%Y-%m").to_numpy()
    codes = g.groupby(["property_id", "aspect"], sort=False).ngroup().to_numpy()
    if len(codes) == 0:
        return pd.DataFrame(columns=CHANGEPOINT_COLUMNS)
    starts = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]])
    ends = np.r_[starts[1:], len(codes)]
    props, aspects = g["property_id"].to_numpy(), g["aspect"].to_numpy()

    rows: list[dict] = []
    for a, z in zip(starts, ends, strict=True):
        cp = find_changepoint(
            n[a:z], rs[a:z], rss[a:z], s[a:z],
            market_weight=None if market_weight is None else market_weight[a:z],
            min_months=CHANGEPOINT_MIN_MONTHS, min_units=CHANGEPOINT_MIN_UNITS,
        )
        if cp is None:
            continue
        rows.append(
            {
                "property_id": props[a],
                "aspect": aspects[a],
                "change_month": months[a + cp.index],
                "delta": round(cp.delta, 3),
                "direction": "negative" if cp.delta < 0 else "positive",
                "raw_delta": round(cp.raw_delta, 3),
                "market_delta": (
                    float("nan") if market is None else round(cp.raw_delta - cp.delta, 3)
                ),
                "p_value": cp.p_value,
            }
        )
    if not rows:
        return pd.DataFrame(columns=CHANGEPOINT_COLUMNS)
    out = pd.DataFrame(rows)
    out["q_value"] = bh_qvalues(out["p_value"].to_numpy(dtype=float))
    keep = (out["q_value"] <= q) & (out["delta"].abs() >= min_effect)
    return out.loc[keep, CHANGEPOINT_COLUMNS].reset_index(drop=True)


def detect_changepoints(
    labelled: pd.DataFrame,
    min_effect: float = CHANGEPOINT_MIN_EFFECT,
    q: float = FDR_Q,
) -> pd.DataFrame:
    """Significant step changes in a property's sentiment *relative to the market*.

    Each review unit is residualised against the leave-one-out cluster mean for the
    same aspect and month, so movement shared by the whole market (e.g. a seasonal
    dip) cancels out. One pooled-variance t test per series (best split, Bonferroni
    over splits), then Benjamini-Hochberg across all series, then an effect floor.
    ``delta`` is the shift relative to the market; ``raw_delta`` is the property's
    own shift and ``market_delta`` the part the market shared.
    """
    return _changepoints_from_units(review_units(labelled), min_effect, q)


# --- "Is it the market?": patterns shared across properties -------------------------


def _upper_t_p(mean: float, sd: float, k: int) -> float:
    """One-sided one-sample t-test p-value for H1: population mean > 0."""
    if not sd > 0:
        return 0.0 if mean > 0 else 1.0
    return t_sf(mean / (sd / np.sqrt(k)), k - 1)


def _seasonal_tests(units: pd.DataFrame, min_effect: float) -> tuple[pd.DataFrame, dict]:
    """Per (aspect, calendar month): is the month below the rest of the year across
    properties? Each property contributes one gap (rest-of-year mean - month mean)."""
    per_month = units.groupby(["aspect", "property_id", "cal"], as_index=False).agg(
        n=("value", "size"), s=("value", "sum")
    )
    per_prop = units.groupby(["aspect", "property_id"], as_index=False).agg(
        n_all=("value", "size"), s_all=("value", "sum")
    )
    pm = per_month.merge(per_prop, on=["aspect", "property_id"])
    rest_n = pm["n_all"] - pm["n"]
    pm = pm[(pm["n"] >= SEASONAL_MIN_MONTH_UNITS) & (rest_n >= SEASONAL_MIN_REST_UNITS)]
    pm = pm.assign(
        gap=(pm["s_all"] - pm["s"]) / (pm["n_all"] - pm["n"]) - pm["s"] / pm["n"],
    )
    pm = pm.assign(joins=pm["gap"] >= min_effect)
    stats = pm.groupby(["aspect", "cal"], as_index=False, sort=True).agg(
        n_tested=("gap", "size"), drop=("gap", "mean"), sd=("gap", "std"),
        n_participating=("joins", "sum"),
    )
    stats = stats[stats["n_tested"] >= MIN_PROPERTIES_FOR_SCOPE]
    p = [
        _upper_t_p(float(m), float(sd), int(k))
        for m, sd, k in zip(stats["drop"], stats["sd"].fillna(0.0), stats["n_tested"], strict=True)
    ]
    tests = stats.assign(kind="seasonal", p_value=p).rename(columns={"cal": "calendar_month"})
    members = pm[pm["joins"]]
    gaps = {
        (aspect, int(cal)): dict(zip(sub["property_id"], sub["gap"].astype(float), strict=True))
        for (aspect, cal), sub in members.groupby(["aspect", "cal"])
    }
    return tests, gaps


def _step_tests(units: pd.DataFrame, min_effect: float) -> tuple[pd.DataFrame, dict]:
    """Per aspect: did most properties decline after the same month? Each property
    contributes its own before/after shift at every candidate split; the split with
    the largest average decline is tested across properties (Bonferroni over splits)."""
    rows, gaps = [], {}
    for aspect, sa in units.groupby("aspect", sort=True):
        grid = pd.PeriodIndex(sa["month"].unique(), freq="M").sort_values()
        if len(grid) < 2 * CHANGEPOINT_MIN_MONTHS:
            continue
        splits = np.arange(CHANGEPOINT_MIN_MONTHS, len(grid) - CHANGEPOINT_MIN_MONTHS + 1)
        agg = sa.groupby(["property_id", "month"]).agg(n=("value", "size"), s=("value", "sum"))
        n_mat = agg["n"].unstack("month", fill_value=0).reindex(columns=grid, fill_value=0)
        s_mat = agg["s"].unstack("month", fill_value=0).reindex(columns=grid, fill_value=0)
        cn = np.cumsum(n_mat.to_numpy(dtype=float), axis=1)
        cs = np.cumsum(s_mat.to_numpy(dtype=float), axis=1)
        n1, s1 = cn[:, splits - 1], cs[:, splits - 1]
        n2, s2 = cn[:, -1:] - n1, cs[:, -1:] - s1
        ok = ((n1 >= STEP_MIN_SIDE_UNITS) & (n2 >= STEP_MIN_SIDE_UNITS)).all(axis=1)
        if ok.sum() < MIN_PROPERTIES_FOR_SCOPE:
            continue
        d = (s2[ok] / n2[ok]) - (s1[ok] / n1[ok])  # properties x splits; < 0 = decline
        k = int(ok.sum())
        mean, sd = d.mean(axis=0), d.std(axis=0, ddof=1)
        # Locate the step where the average decline is largest (this peaks at the
        # true change month for a single step; the t statistic is nearly flat across
        # splits because dilution shrinks mean and spread together). Testing at that
        # split with Bonferroni over all splits is at least as conservative as min-p.
        best = int(np.argmax(-mean))
        p_best = _upper_t_p(float(-mean[best]), float(sd[best]), k)
        props = n_mat.index[ok]
        joins = d[:, best] <= -min_effect
        gaps[aspect] = {p: float(-x) for p, x, j in zip(props, d[:, best], joins, strict=True) if j}
        rows.append(
            {
                "aspect": aspect,
                "kind": "step",
                "change_month": grid[splits[best]].strftime("%Y-%m"),
                "drop": float(-mean[best]),
                "n_tested": k,
                "n_participating": int(joins.sum()),
                "p_value": min(1.0, len(splits) * p_best),
            }
        )
    return pd.DataFrame(rows), gaps


def _keep(tests: pd.DataFrame, n_cluster: int, q: float, min_fraction: float) -> pd.DataFrame:
    """Benjamini-Hochberg within a test family, then require enough participants."""
    if tests.empty:
        return tests
    tests = tests.assign(q_value=bh_qvalues(tests["p_value"].to_numpy(dtype=float)))
    share = tests["n_participating"] / n_cluster
    return tests[(tests["q_value"] <= q) & (share >= min_fraction)]


def _findings_from_units(
    units: pd.DataFrame,
    n_cluster: int,
    min_fraction: float = MARKET_WIDE_FRACTION,
    min_effect: float = MARKET_MIN_EFFECT,
    q: float = FDR_Q,
) -> list[dict]:
    """All significant market-level patterns as dicts, seasonal first, then steps."""
    if units.empty or n_cluster < MIN_PROPERTIES_FOR_SCOPE:
        return []
    units = units.assign(cal=units["date"].dt.month, month=units["date"].dt.to_period("M"))
    s_tests, s_gaps = _seasonal_tests(units, min_effect)
    seasonal = _keep(s_tests, n_cluster, q, min_fraction)
    findings = [
        {
            "aspect": r.aspect, "kind": "seasonal", "calendar_month": int(r.calendar_month),
            "change_month": None, "drop": round(float(r.drop), 3), "n_tested": int(r.n_tested),
            "gaps": s_gaps.get((r.aspect, int(r.calendar_month)), {}),
            "p_value": float(r.p_value), "q_value": float(r.q_value),
        }
        for r in seasonal.itertuples()
    ]
    # A recurring seasonal dip is not a step: drop those aspect-months before step tests.
    explained = {f"{f['aspect']}|{f['calendar_month']}" for f in findings}
    if explained:
        key = units["aspect"].astype(str) + "|" + units["cal"].astype(str)
        units = units[~key.isin(explained)]
    t_tests, t_gaps = _step_tests(units, min_effect)
    findings += [
        {
            "aspect": r.aspect, "kind": "step", "calendar_month": None,
            "change_month": r.change_month, "drop": round(float(r.drop), 3),
            "n_tested": int(r.n_tested), "gaps": t_gaps.get(r.aspect, {}),
            "p_value": float(r.p_value), "q_value": float(r.q_value),
        }
        for r in _keep(t_tests, n_cluster, q, min_fraction).itertuples()
    ]
    return findings


def _market_findings(labelled: pd.DataFrame, **kwargs) -> list[dict]:
    return _findings_from_units(
        review_units(labelled), labelled["property_id"].nunique(), **kwargs
    )


def detect_market_patterns(
    labelled: pd.DataFrame,
    min_fraction: float = MARKET_WIDE_FRACTION,
    min_effect: float = MARKET_MIN_EFFECT,
    q: float = FDR_Q,
) -> pd.DataFrame:
    """Market-wide patterns: seasonal dips (any calendar month) and step declines.

    Properties are the replicates: a one-sample t test on the per-property drops,
    Benjamini-Hochberg within each family, and at least ``min_fraction`` of the
    cluster's properties must drop by ``min_effect`` or more.
    """
    n_cluster = labelled["property_id"].nunique()
    findings = _market_findings(labelled, min_fraction=min_fraction, min_effect=min_effect, q=q)
    rows = [
        {
            **{k: f[k] for k in ("aspect", "kind", "calendar_month", "change_month", "drop",
                                 "n_tested", "p_value", "q_value")},
            "n_participating": len(f["gaps"]),
            "share": round(len(f["gaps"]) / n_cluster, 3),
            "properties": ", ".join(sorted(f["gaps"])),
        }
        for f in findings
    ]
    out = pd.DataFrame(rows, columns=MARKET_PATTERN_COLUMNS)
    out["calendar_month"] = out["calendar_month"].astype("Int64")
    return out


def detect_seasonal_dips(labelled: pd.DataFrame, month: int | None = None) -> pd.DataFrame:
    """Properties taking part in a significant market-wide seasonal dip.

    ``month`` (1-12) restricts the result to one calendar month; by default every
    month is tested (seasonality is not assumed to be December).
    """
    rows = [
        {
            "property_id": prop,
            "aspect": f["aspect"],
            "target_month": f["calendar_month"],
            "gap": round(gap, 3),
            "q_value": f["q_value"],
        }
        for f in _market_findings(labelled)
        if f["kind"] == "seasonal" and (month is None or f["calendar_month"] == month)
        for prop, gap in sorted(f["gaps"].items())
    ]
    return pd.DataFrame(rows, columns=SEASONAL_COLUMNS)


# --- Market-wide vs property-specific -----------------------------------------------


def _describe(finding: dict, n_cluster: int) -> str:
    k = len(finding["gaps"])
    if finding["kind"] == "seasonal":
        when = f"seasonal dip in {calendar.month_name[finding['calendar_month']]}"
    else:
        when = f"decline from {finding['change_month']}"
    return f"{when} ({k}/{n_cluster} properties, average drop {finding['drop']:.2f})"


def market_wide_summary(
    labelled: pd.DataFrame, min_fraction: float = MARKET_WIDE_FRACTION
) -> pd.DataFrame:
    """Classify each aspect's negative shifts as market-wide or property-specific.

    * ``market-wide``: a significant pattern shared by >= ``min_fraction`` of
      properties (seasonal dip or step decline).
    * ``property-specific``: no market pattern, but one or more properties declined
      significantly *relative to the market*.
    * ``undetermined``: fewer than ``MIN_PROPERTIES_FOR_SCOPE`` properties, so the
      market cannot be separated from a single property.

    Aspects with no negative shift are omitted.
    """
    n_cluster = labelled["property_id"].nunique()
    units = review_units(labelled)
    cps = _changepoints_from_units(units, CHANGEPOINT_MIN_EFFECT, FDR_Q)
    declines = cps[cps["direction"] == "negative"]
    findings = _findings_from_units(units, n_cluster, min_fraction=min_fraction)

    rows: list[dict] = []
    for aspect in sorted(set(declines["aspect"]) | {f["aspect"] for f in findings}):
        own = declines[declines["aspect"] == aspect]
        own_text = "; ".join(
            f"{r.property_id} below the market from {r.change_month} ({r.delta:+.2f})"
            for r in own.itertuples()
        )
        market = [f for f in findings if f["aspect"] == aspect]
        if n_cluster < MIN_PROPERTIES_FOR_SCOPE:
            scope, props = "undetermined", set(own["property_id"])
            pattern = f"only {n_cluster} properties: cannot separate market from property"
        elif market:
            scope = "market-wide"
            props = set().union(*(f["gaps"] for f in market))
            pattern = "; ".join(_describe(f, n_cluster) for f in market)
            if own_text:
                pattern += f"; also {own_text}"
        else:
            scope, props, pattern = "property-specific", set(own["property_id"]), own_text
        rows.append(
            {
                "aspect": aspect,
                "n_properties": len(props),
                "fraction": round(len(props) / n_cluster, 3),
                "scope": scope,
                "properties": ", ".join(sorted(props)),
                "pattern": pattern,
            }
        )
    return pd.DataFrame(rows, columns=SCOPE_COLUMNS)
