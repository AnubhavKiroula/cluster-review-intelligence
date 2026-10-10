"""Benchmarking, trends, and market-wide vs property-specific logic.

Operates on the long frame produced by :func:`cri.pipeline.label_reviews`
(columns: review_id, property_id, date, aspect, sentiment, sentence).

Two questions, each tested at the level it is about (rules in docs/methodology.md):

* "Is it me?"  -> a property's sentiment *relative to the rest of the market* is
  tested for a step change. The market reference removes each other property's
  own level first, so it does not move when properties enter, leave, or change
  review volume.
* "Is it the market?" -> properties are the independent replicates; a seasonal dip
  or a step change counts as market-wide only when it holds across properties.

Mentions from the same review are correlated, so every significance test and the
bootstrap use one unit per (review, aspect) rather than one per mention.
"""

from __future__ import annotations

import calendar
import math
import zlib

import numpy as np
import pandas as pd

from .changepoint import bh_qvalues, find_changepoint, t_sf

# --- Thresholds (all documented in docs/methodology.md) -------------------------

BENCHMARK_MARGIN = 0.05  # minimum |property - cluster| gap to call lead/lag
MIN_REVIEWS_FOR_FLAG = 10  # fewer reviews: no CI shown and no lead/lag flag
BOOTSTRAP_SAMPLES = 2000
CI_LEVEL = 0.95
FDR_Q = 0.05  # Benjamini-Hochberg false-discovery rate for every test family
CHANGEPOINT_MIN_EFFECT = 0.4  # |shift vs market| >= 0.4 ~ 20% of reviews flipping polarity
CHANGEPOINT_MIN_MONTHS = 4  # months on each side of a split
CHANGEPOINT_MIN_UNITS = 10  # reviews on each side of a split
MARKET_WIDE_FRACTION = 0.6  # share of properties that must share a market pattern
MARKET_MIN_EFFECT = 0.3  # a property "participates" if its drop is >= 0.3 (~15% flipping)
MIN_PROPERTIES_FOR_SCOPE = 3  # with fewer properties "me vs market" is undetermined
SEASONAL_MIN_YEARS = 2  # a dip must be seen in >= 2 years to be called seasonal
SEASONAL_MIN_MONTH_UNITS = 2  # reviews in the calendar month, per property and year
SEASONAL_MIN_REST_UNITS = 5  # reviews in the rest of that year, per property
STEP_MIN_SIDE_UNITS = 5  # reviews per property on each side of a market step split

BENCHMARK_COLUMNS = [
    "property_id", "aspect", "mean", "n", "n_reviews", "ci_low", "ci_high",
    "cluster_mean", "diff", "p_value", "q_value", "flag",
]
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


def undetermined_note(n_properties: int) -> str:
    """Single source for the 'too few properties' explanation shown to users."""
    noun = "property" if n_properties == 1 else "properties"
    return f"only {n_properties} {noun} with reviews: cannot separate market from property"


def none_for_missing(values: pd.Series) -> pd.Series:
    """Optional text column with real ``None`` for missing values (pandas 3 would
    otherwise store NaN in a string column, and NaN is truthy)."""
    return values.astype(object).where(values.notna(), None)


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
    mentions from one review are not independent (a cluster bootstrap). Fewer than
    two reviews give no interval (NaN), never a misleading zero-width one.
    """
    sums = np.asarray(sums, dtype=float)
    counts = np.asarray(counts, dtype=float)
    r = len(sums)
    if r < 2:
        return (float("nan"), float("nan"))
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
    """Mean sentiment (mention-level) and mention count per (property, aspect)."""
    grouped = labelled.groupby(["property_id", "aspect"])["sentiment"]
    return grouped.agg(mean="mean", n="count").reset_index()


def cluster_means(scores: pd.DataFrame) -> pd.Series:
    """Cluster mean per aspect = unweighted mean of per-property means."""
    return scores.groupby("aspect")["mean"].mean()


def _two_sided_p(diff: np.ndarray, se: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.abs(diff) / se
    p = np.array([math.erfc(v / math.sqrt(2.0)) if np.isfinite(v) else 0.0 for v in z])
    p[(se == 0) & (diff == 0)] = 1.0
    p[np.isnan(se)] = np.nan
    return p


def benchmark_vs_cluster(labelled: pd.DataFrame, property_id: str | None = None) -> pd.DataFrame:
    """Flag each property-aspect as lead / lag / on_par vs the cluster.

    * ``ci_low``/``ci_high``: review-level bootstrap 95% CI (NaN below
      ``MIN_REVIEWS_FOR_FLAG`` reviews).
    * ``p_value``: two-sided test of mean = cluster mean using the review-level
      (cluster-robust) standard error; ``q_value``: Benjamini-Hochberg over every
      eligible property-aspect pair in the cluster, so flags are not one 5% test
      each across ~100 pairs.
    * A flag needs >= ``MIN_REVIEWS_FOR_FLAG`` reviews, a gap above
      ``BENCHMARK_MARGIN``, ``q_value <= FDR_Q``, and a CI that excludes the cluster
      mean (so a flag never contradicts the interval shown next to it).

    Pass ``property_id`` to bootstrap only that property; results are identical to
    the full run because each group has its own seed and q-values span the cluster.
    """
    scores = aspect_scores(labelled)
    scores = scores.assign(cluster_mean=scores["aspect"].map(cluster_means(scores)))
    units = review_units(labelled).merge(scores[["property_id", "aspect", "mean"]])
    units = units.assign(dev2=(units["total"] - units["mean"] * units["mentions"]) ** 2)
    robust = units.groupby(["property_id", "aspect"], as_index=False).agg(
        n_reviews=("total", "size"), dev2=("dev2", "sum"), mentions=("mentions", "sum")
    )
    out = scores.merge(robust, on=["property_id", "aspect"], how="left")
    r = out["n_reviews"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        se = np.where(r >= 2, np.sqrt(r / (r - 1) * out["dev2"]) / out["mentions"], np.nan)
    diff = (out["mean"] - out["cluster_mean"]).to_numpy(dtype=float)
    eligible = r >= MIN_REVIEWS_FOR_FLAG
    p = _two_sided_p(diff, se)
    q = np.full(len(out), np.nan)
    if eligible.any():
        q[eligible] = bh_qvalues(p[eligible])
    out = out.assign(diff=diff, p_value=np.where(eligible, p, np.nan), q_value=q)
    out["n_reviews"] = out["n_reviews"].astype("int64")

    if property_id is not None:
        out = out[out["property_id"] == property_id]
        units = units[units["property_id"] == property_id]
    by_group = {
        key: (g["total"].to_numpy(dtype=float), g["mentions"].to_numpy(dtype=float))
        for key, g in units.groupby(["property_id", "aspect"])
    }
    lows, highs = [], []
    for prop, aspect, n_rev in zip(out["property_id"], out["aspect"], out["n_reviews"],
                                   strict=True):
        if n_rev < MIN_REVIEWS_FOR_FLAG:
            lows.append(float("nan"))
            highs.append(float("nan"))
            continue
        lo, hi = bootstrap_mean_ci(*by_group[(prop, aspect)], seed=_group_seed(prop, aspect))
        lows.append(lo)
        highs.append(hi)
    out = out.assign(ci_low=lows, ci_high=highs)

    significant = (out["q_value"] <= FDR_Q).to_numpy()
    lead = significant & (out["diff"] > BENCHMARK_MARGIN) & (out["ci_low"] > out["cluster_mean"])
    lag = significant & (out["diff"] < -BENCHMARK_MARGIN) & (out["ci_high"] < out["cluster_mean"])
    out["flag"] = np.select([lead, lag], ["lead", "lag"], default="on_par")
    return out[BENCHMARK_COLUMNS].reset_index(drop=True)


# --- Monthly trends -----------------------------------------------------------------


def monthly_stats(labelled: pd.DataFrame, property_id: str, aspect: str) -> pd.DataFrame:
    """month, mean, n for one property-aspect (months with at least one mention)."""
    mask = (labelled["property_id"] == property_id) & (labelled["aspect"] == aspect)
    sub = labelled.loc[mask]
    if sub.empty:
        return pd.DataFrame(
            {
                "month": pd.Series(dtype="datetime64[ns]"),
                "mean": pd.Series(dtype=float),
                "n": pd.Series(dtype="int64"),
            }
        )
    monthly = sub.set_index("date")["sentiment"].resample("MS").agg(["mean", "count"])
    monthly = monthly[monthly["count"] > 0]
    return pd.DataFrame(
        {
            "month": monthly.index,
            "mean": monthly["mean"].to_numpy(dtype=float),
            "n": monthly["count"].to_numpy(dtype="int64"),
        }
    )


def monthly_series(labelled: pd.DataFrame, property_id: str, aspect: str) -> pd.Series:
    """Monthly mean sentiment for one property-aspect (month start index)."""
    stats = monthly_stats(labelled, property_id, aspect)
    return pd.Series(stats["mean"].to_numpy(), index=pd.DatetimeIndex(stats["month"]))


# --- "Is it me?": property-vs-market changepoints -----------------------------------


def _changepoints_from_units(units: pd.DataFrame, min_effect: float, q: float) -> pd.DataFrame:
    if units.empty:
        return pd.DataFrame(columns=CHANGEPOINT_COLUMNS)
    # Each property's own level and within-property variance, per aspect.
    pa = units.groupby(["property_id", "aspect"])["value"].agg(
        alpha="mean", n_pa="size", var="var"
    )
    pa["ssw"] = pa["var"].fillna(0.0) * (pa["n_pa"] - 1)
    pa["dfw"] = pa["n_pa"] - 1
    asp_ssw = pa.groupby(level="aspect")["ssw"].transform("sum")
    asp_dfw = pa.groupby(level="aspect")["dfw"].transform("sum")
    # Pooled variance of the OTHER properties (the data the market is estimated from).
    with np.errstate(divide="ignore", invalid="ignore"):
        pa["v_loo"] = ((asp_ssw - pa["ssw"]) / (asp_dfw - pa["dfw"])).where(
            asp_dfw - pa["dfw"] > 0
        )
    pa["v_loo"] = pa["v_loo"].fillna(1.0)  # values lie in [-1, 1]: 1 is the max variance

    u = units.join(pa[["alpha", "v_loo"]], on=["property_id", "aspect"])
    u = u.assign(
        month=u["date"].dt.to_period("M"),
        sq=u["value"] ** 2,
        centred=u["value"] - u["alpha"],
    )
    g = u.groupby(["property_id", "aspect", "month"], as_index=False, sort=True).agg(
        n=("value", "size"), s=("value", "sum"), ss=("sq", "sum"),
        c=("centred", "sum"), v_loo=("v_loo", "first"),
    )
    # Per aspect: is there a market to compare with?
    residual = (
        g.groupby("aspect")["property_id"].transform("nunique") >= MIN_PROPERTIES_FOR_SCOPE
    )
    totals = g.groupby(["aspect", "month"])[["n", "c"]].transform("sum")
    loo_n, loo_c = totals["n"] - g["n"], totals["c"] - g["c"]
    # Residual aspects: drop months where no other property has reviews.
    g = g.assign(residual=residual, loo_n=loo_n, loo_c=loo_c)
    g = g[~g["residual"] | (g["loo_n"] > 0)]

    n = g["n"].to_numpy(dtype=float)
    s = g["s"].to_numpy(dtype=float)
    ss = g["ss"].to_numpy(dtype=float)
    is_res = g["residual"].to_numpy(dtype=bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        # Market = mean deviation of the other properties from their OWN levels, so
        # it does not move when a strong or weak property enters or leaves the data.
        market = np.where(is_res, g["loo_c"].to_numpy(dtype=float) / g["loo_n"].to_numpy(), 0.0)
        mvar = np.where(is_res, g["v_loo"].to_numpy(dtype=float) / g["loo_n"].to_numpy(), 0.0)
    rs = s - n * market  # exact sums of (value - market) and (value - market)^2
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
            n[a:z], rs[a:z], rss[a:z], s[a:z], market_var=mvar[a:z],
            min_months=CHANGEPOINT_MIN_MONTHS, min_units=CHANGEPOINT_MIN_UNITS,
        )
        if cp is None:
            continue
        rows.append(
            {
                "property_id": props[a],
                "aspect": aspects[a],
                "change_month": months[a + cp.index],
                "delta": cp.delta,
                "direction": "negative" if cp.delta < 0 else "positive",
                "raw_delta": cp.raw_delta,
                # No market comparison was possible: the raw series was tested.
                "market_delta": cp.raw_delta - cp.delta if is_res[a] else float("nan"),
                "p_value": cp.p_value,
            }
        )
    if not rows:
        return pd.DataFrame(columns=CHANGEPOINT_COLUMNS)
    out = pd.DataFrame(rows)
    out["q_value"] = bh_qvalues(out["p_value"].to_numpy(dtype=float))
    # Decide on unrounded values; round only what is displayed.
    keep = (out["q_value"] <= q) & (out["delta"].abs() >= min_effect)
    out = out.loc[keep, CHANGEPOINT_COLUMNS].reset_index(drop=True)
    return out.round({"delta": 3, "raw_delta": 3, "market_delta": 3})


def detect_changepoints(
    labelled: pd.DataFrame,
    min_effect: float = CHANGEPOINT_MIN_EFFECT,
    q: float = FDR_Q,
) -> pd.DataFrame:
    """Significant step changes in a property's sentiment *relative to the market*.

    Each review unit is compared with the market for the same aspect and month: the
    average deviation of the OTHER properties from their own levels. One
    pooled-variance t test per series (best split, Bonferroni over splits, plus the
    variance of the market estimate), then Benjamini-Hochberg across all series,
    then an effect floor. ``delta`` is the shift relative to the market;
    ``raw_delta`` is the property's own shift and ``market_delta`` the part the
    market shared. Aspects reviewed at fewer than ``MIN_PROPERTIES_FOR_SCOPE``
    properties have no market reference: their raw series is tested and
    ``market_delta`` is NaN.
    """
    return _changepoints_from_units(review_units(labelled), min_effect, q)


# --- "Is it the market?": patterns shared across properties -------------------------


def _upper_t_p(mean: float, sd: float, k: int) -> float:
    """One-sided one-sample t-test p-value for H1: population mean > 0."""
    if not sd > 0:
        return 0.0 if mean > 0 else 1.0
    return t_sf(mean / (sd / np.sqrt(k)), k - 1)


def _seasonal_tests(units: pd.DataFrame, min_effect: float) -> tuple[pd.DataFrame, dict]:
    """Per (aspect, calendar month): is the month below the rest of the SAME year,
    across properties, in EVERY observed year?

    Comparing within a year means a one-off step (e.g. a decline from July) is not
    mistaken for seasonality; requiring every year (an intersection-union test: the
    p-value is the largest per-year p-value) means the dip must recur.
    """
    per_month = units.groupby(["aspect", "property_id", "year", "cal"], as_index=False).agg(
        n=("value", "size"), s=("value", "sum")
    )
    per_year = units.groupby(["aspect", "property_id", "year"], as_index=False).agg(
        n_y=("value", "size"), s_y=("value", "sum")
    )
    m = per_month.merge(per_year, on=["aspect", "property_id", "year"])
    rest_n = m["n_y"] - m["n"]
    m = m[(m["n"] >= SEASONAL_MIN_MONTH_UNITS) & (rest_n >= SEASONAL_MIN_REST_UNITS)]
    m = m.assign(gap=(m["s_y"] - m["s"]) / (m["n_y"] - m["n"]) - m["s"] / m["n"])

    by_year = m.groupby(["aspect", "cal", "year"], as_index=False).agg(
        k=("gap", "size"), mean=("gap", "mean"), sd=("gap", "std")
    )
    by_year = by_year[by_year["k"] >= MIN_PROPERTIES_FOR_SCOPE]
    by_year["p"] = [
        _upper_t_p(float(a), float(b), int(c))
        for a, b, c in zip(by_year["mean"], by_year["sd"].fillna(0.0), by_year["k"], strict=True)
    ]
    tests = by_year.groupby(["aspect", "cal"], as_index=False).agg(
        years=("year", "size"), p_value=("p", "max")
    )
    tests = tests[tests["years"] >= SEASONAL_MIN_YEARS]

    per_prop = m.groupby(["aspect", "cal", "property_id"], as_index=False).agg(
        years=("gap", "size"), gap=("gap", "mean"), worst=("gap", "min")
    )
    per_prop = per_prop[per_prop["years"] >= SEASONAL_MIN_YEARS]
    joins = per_prop[(per_prop["gap"] >= min_effect) & (per_prop["worst"] > 0)]
    drop = per_prop.groupby(["aspect", "cal"])["gap"].agg(["mean", "size"])
    gaps = {
        (aspect, int(cal)): dict(zip(sub["property_id"], sub["gap"].astype(float), strict=True))
        for (aspect, cal), sub in joins.groupby(["aspect", "cal"])
    }
    rows = [
        {
            "aspect": t.aspect,
            "calendar_month": int(t.cal),
            "drop": float(drop.at[(t.aspect, t.cal), "mean"]),
            "n_tested": int(drop.at[(t.aspect, t.cal), "size"]),
            "n_participating": len(gaps.get((t.aspect, int(t.cal)), {})),
            "p_value": float(t.p_value),
        }
        for t in tests.itertuples()
        if (t.aspect, t.cal) in drop.index
    ]
    return pd.DataFrame(rows), gaps


def _step_tests(
    units: pd.DataFrame, grids: dict[str, pd.PeriodIndex], min_effect: float
) -> tuple[pd.DataFrame, dict]:
    """Per aspect: did most properties decline after the same month? Each property
    contributes its own before/after shift at every candidate split; the split with
    the largest average decline is tested across properties (Bonferroni over splits).

    ``grids`` holds every month the aspect was observed in, so removing months that
    a seasonal pattern explains does not shift where a split can fall.
    """
    rows, gaps = [], {}
    for aspect, sa in units.groupby("aspect", sort=True):
        grid = grids[aspect]
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
                "change_month": grid[splits[best]].strftime("%Y-%m"),
                "drop": float(-mean[best]),
                "n_tested": k,
                "n_participating": int(joins.sum()),
                "p_value": min(1.0, len(splits) * p_best),
            }
        )
    return pd.DataFrame(rows), gaps


def _keep(tests: pd.DataFrame, coverage: pd.Series, q: float, min_fraction: float) -> pd.DataFrame:
    """Benjamini-Hochberg within a test family, then require that at least
    ``min_fraction`` of the properties reviewing the aspect participate."""
    if tests.empty:
        return tests
    tests = tests.assign(q_value=bh_qvalues(tests["p_value"].to_numpy(dtype=float)))
    share = tests["n_participating"] / tests["aspect"].map(coverage)
    return tests[(tests["q_value"] <= q) & (share >= min_fraction)]


def _findings_from_units(
    units: pd.DataFrame,
    min_fraction: float = MARKET_WIDE_FRACTION,
    min_effect: float = MARKET_MIN_EFFECT,
    q: float = FDR_Q,
) -> list[dict]:
    """All significant market-level patterns as dicts, seasonal first, then steps."""
    if units.empty:
        return []
    coverage = units.groupby("aspect")["property_id"].nunique()
    units = units[units["aspect"].map(coverage) >= MIN_PROPERTIES_FOR_SCOPE]
    if units.empty:
        return []
    units = units.assign(
        cal=units["date"].dt.month,
        year=units["date"].dt.year,
        month=units["date"].dt.to_period("M"),
    )
    grids = {
        aspect: pd.PeriodIndex(sa["month"].unique(), freq="M").sort_values()
        for aspect, sa in units.groupby("aspect")
    }
    s_tests, s_gaps = _seasonal_tests(units, min_effect)
    findings = [
        {
            "aspect": r.aspect, "kind": "seasonal", "calendar_month": int(r.calendar_month),
            "change_month": None, "drop": round(float(r.drop), 3), "n_tested": int(r.n_tested),
            "coverage": int(coverage[r.aspect]),
            "gaps": s_gaps.get((r.aspect, int(r.calendar_month)), {}),
            "p_value": float(r.p_value), "q_value": float(r.q_value),
        }
        for r in _keep(s_tests, coverage, q, min_fraction).itertuples()
    ]
    # A recurring seasonal dip is not a step: mask those aspect-months (the month grid
    # itself is kept, so a step's location is unaffected).
    explained = {f"{f['aspect']}|{f['calendar_month']}" for f in findings}
    if explained:
        key = units["aspect"].astype(str) + "|" + units["cal"].astype(str)
        units = units[~key.isin(explained)]
    t_tests, t_gaps = _step_tests(units, grids, min_effect)
    findings += [
        {
            "aspect": r.aspect, "kind": "step", "calendar_month": None,
            "change_month": r.change_month, "drop": round(float(r.drop), 3),
            "n_tested": int(r.n_tested), "coverage": int(coverage[r.aspect]),
            "gaps": t_gaps.get(r.aspect, {}),
            "p_value": float(r.p_value), "q_value": float(r.q_value),
        }
        for r in _keep(t_tests, coverage, q, min_fraction).itertuples()
    ]
    return findings


def _market_findings(labelled: pd.DataFrame, **kwargs) -> list[dict]:
    return _findings_from_units(review_units(labelled), **kwargs)


def detect_market_patterns(
    labelled: pd.DataFrame,
    min_fraction: float = MARKET_WIDE_FRACTION,
    min_effect: float = MARKET_MIN_EFFECT,
    q: float = FDR_Q,
) -> pd.DataFrame:
    """Market-wide patterns: recurring seasonal dips (any calendar month) and step
    declines.

    Properties are the replicates: a one-sample t test on the per-property drops,
    Benjamini-Hochberg within each family, and at least ``min_fraction`` of the
    properties reviewing the aspect must drop by ``min_effect`` or more. Aspects
    reviewed at fewer than ``MIN_PROPERTIES_FOR_SCOPE`` properties are not tested.
    ``change_month`` is None for seasonal rows; ``calendar_month`` is <NA> for steps.
    """
    findings = _market_findings(labelled, min_fraction=min_fraction, min_effect=min_effect, q=q)
    rows = [
        {
            **{k: f[k] for k in ("aspect", "kind", "calendar_month", "change_month", "drop",
                                 "n_tested", "p_value", "q_value")},
            "n_participating": len(f["gaps"]),
            "share": round(len(f["gaps"]) / f["coverage"], 3),
            "properties": ", ".join(sorted(map(str, f["gaps"]))),
        }
        for f in findings
    ]
    out = pd.DataFrame(rows, columns=MARKET_PATTERN_COLUMNS)
    out["calendar_month"] = out["calendar_month"].astype("Int64")
    out["change_month"] = none_for_missing(out["change_month"])
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


def _describe(finding: dict) -> str:
    k = len(finding["gaps"])
    if finding["kind"] == "seasonal":
        when = f"seasonal dip in {calendar.month_name[finding['calendar_month']]}"
    else:
        when = f"decline from {finding['change_month']}"
    return (
        f"{when} ({k}/{finding['coverage']} properties, average drop {finding['drop']:.2f})"
    )


def market_wide_summary(
    labelled: pd.DataFrame, min_fraction: float = MARKET_WIDE_FRACTION
) -> pd.DataFrame:
    """Classify each aspect's negative shifts as market-wide or property-specific.

    * ``market-wide``: a significant pattern shared by >= ``min_fraction`` of the
      properties reviewing the aspect (seasonal dip or step decline).
    * ``property-specific``: no market pattern, but one or more properties declined
      significantly *relative to the market*.
    * ``undetermined``: fewer than ``MIN_PROPERTIES_FOR_SCOPE`` properties review the
      aspect, so the market cannot be separated from a single property.

    ``fraction`` is relative to the properties reviewing the aspect. Aspects with no
    negative shift are omitted.
    """
    units = review_units(labelled)
    coverage = units.groupby("aspect")["property_id"].nunique()
    cps = _changepoints_from_units(units, CHANGEPOINT_MIN_EFFECT, FDR_Q)
    declines = cps[cps["direction"] == "negative"]
    findings = _findings_from_units(units, min_fraction=min_fraction)

    rows: list[dict] = []
    for aspect in sorted(set(declines["aspect"]) | {f["aspect"] for f in findings}):
        k = int(coverage.get(aspect, 0))
        own = declines[declines["aspect"] == aspect]
        relative = "below the market" if k >= MIN_PROPERTIES_FOR_SCOPE else "declined"
        own_text = "; ".join(
            f"{r.property_id} {relative} from {r.change_month} ({r.delta:+.2f})"
            for r in own.itertuples()
        )
        market = [f for f in findings if f["aspect"] == aspect]
        if k < MIN_PROPERTIES_FOR_SCOPE:
            scope, props = "undetermined", set(own["property_id"])
            pattern = undetermined_note(k) + (f"; {own_text}" if own_text else "")
        elif market:
            scope = "market-wide"
            props = set().union(*(f["gaps"] for f in market))
            pattern = "; ".join(_describe(f) for f in market)
            if own_text:
                pattern += f"; also {own_text}"
        else:
            scope, props, pattern = "property-specific", set(own["property_id"]), own_text
        rows.append(
            {
                "aspect": aspect,
                "n_properties": len(props),
                "fraction": round(len(props) / k, 3) if k else 0.0,
                "scope": scope,
                "properties": ", ".join(sorted(map(str, props))),
                "pattern": pattern,
            }
        )
    return pd.DataFrame(rows, columns=SCOPE_COLUMNS)
