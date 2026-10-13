"""Export static JSON snapshots for the Next.js frontend.

The frontend is a pure static site: it never talks to Python at runtime. All numbers
come from the audited ``cri.api`` core (CLAUDE.md rule 1 — no fabricated values), dumped
once here. Re-run after the analytics change:

    python web/scripts/export_snapshot.py

Writes, in web/public/data/:

- ``cluster.real.json``: the REAL cluster (one hill town, built locally by
  ``scripts/prepare_real_cluster.py``). **Aggregates only**: the source is
  TripAdvisor-derived and we never redistribute review text, so no review or clause
  text goes in. Skipped, keeping the committed file, when the local input is absent
  (teammates and CI do not have it).
- ``cluster.synthetic.json``: the SYNTHETIC cluster (the simulated timeline for the
  method demo, plus the illustrative review texts the explorer shows).
- ``fixcheck.synthetic.json``: every "Did my fix work?" result (property x aspect x
  month) on the SYNTHETIC cluster. ``--skip-fix-check`` skips it (a couple of minutes).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from cri import api

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web" / "public" / "data"
# CLAUDE.md rule 2: synthetic data carries "synthetic" in its filename.
OUT = DATA / "cluster.synthetic.json"
FIX_OUT = DATA / "fixcheck.synthetic.json"
REAL_OUT = DATA / "cluster.real.json"
REAL_IN = ROOT / "data/raw/external/prepared/real_cluster_kausani.csv"  # local only


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records (NaN/NA -> null, Timestamps -> ISO date)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def snapshot(d: api.ClusterData, generated_at: str, *, with_text: bool) -> dict:
    """Every number the pages show, from cri.api. ``with_text`` adds the explorer's
    review and clause text (SYNTHETIC only: real text is never published)."""
    properties, aspects = api.list_properties(d), api.list_aspects()
    lo, hi = api.date_range(d)
    all_changepoints = api.changepoints(d)
    destination = api.destination_summary(d)
    # The worst market-wide aspect, computed once here so pages do not re-rank it.
    market_wide = destination[destination["scope"] == "market-wide"].sort_values(
        ["pct_negative", "aspect"], ascending=[False, True]
    )
    stars = d.reviews.groupby("property_id")["rating"].agg(["mean", "size"])

    per_property: dict[str, dict] = {}
    for prop in properties:
        trends = {}
        for aspect in aspects:
            tr = api.trend(d, prop, aspect)
            if not tr.empty:
                trends[aspect] = records(tr)
        cps = all_changepoints[all_changepoints["property_id"] == prop]
        per_property[prop] = {
            "stars": {"mean": round(float(stars.at[prop, "mean"]), 2),
                      "n_reviews": int(stars.at[prop, "size"])},
            "scorecard": records(api.property_scorecard(d, prop)),
            "priority_actions": records(api.priority_actions(d, prop)),
            "trends": trends,
            "changepoints": records(cps),
        }

    out = {
        "meta": {
            "is_synthetic": bool(d.is_synthetic),
            "has_dates": bool(d.has_dates),
            "source_name": d.source_name,
            "generated_at": generated_at,
            "properties": properties,
            "aspects": aspects,
            "date_min": None if pd.isna(lo) else lo.date().isoformat(),
            "date_max": None if pd.isna(hi) else hi.date().isoformat(),
            "n_reviews": int(len(d.reviews)),
        },
        "market_scope": records(api.market_scope(d)),
        "destination_summary": records(destination),
        "market_headline": records(market_wide.head(1))[0] if len(market_wide) else None,
        "per_property": per_property,
    }
    if with_text:  # explorer corpus: raw reviews + classified clauses
        out["reviews"] = records(d.reviews[api.REVIEW_COLUMNS])
        out["mentions"] = records(d.labelled[["review_id", "aspect", "sentiment", "sentence"]])
    return out


def real_snapshot(path: Path, generated_at: str) -> dict:
    """The real cluster: aggregates only, with provenance from the prep sidecar."""
    info = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    d = api.load_cluster(path)
    assert not d.is_synthetic and not d.has_dates
    snap = snapshot(d, generated_at, with_text=False)
    snap["meta"]["source_name"] = (
        f"{info['town']} ({info['district']}, {info['state']}): real hotel reviews"
    )
    snap["meta"]["provenance"] = {
        "town": info["town"], "district": info["district"], "state": info["state"],
        "hotels": info["hotels_kept"], "hotels_in_town": info["hotels_in_town"],
        "reviews_in_town": info["reviews_in_town"], "min_reviews": info["min_reviews"],
        "median_reviews_per_hotel": info["median_reviews_per_hotel"],
        "platform": "TripAdvisor", "platform_inferred": True,
        "dataset": "Kaggle orionpax00/uttarakhand-hotel-reviews-india",
    }
    return snap


def fix_checks(d: api.ClusterData, generated_at: str) -> dict:
    """Every intervention_check result: results[property][aspect][month]."""
    lo, hi = api.date_range(d)
    # A change in the first month has no "before": start from the second month.
    months = [p.strftime("%Y-%m") for p in pd.period_range(lo, hi, freq="M")][1:]
    results: dict[str, dict] = {}
    for prop in api.list_properties(d):
        results[prop] = {
            aspect: {m: api.intervention_check(d, prop, aspect, m) for m in months}
            for aspect in api.list_aspects()
        }
    return {
        "meta": {
            "is_synthetic": bool(d.is_synthetic),
            "source_name": d.source_name,
            "generated_at": generated_at,
            "months": months,
        },
        "results": results,
    }


def _write(path: Path, data: dict, **dump) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, **dump), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-fix-check", action="store_true",
                        help="do not regenerate fixcheck.synthetic.json")
    parser.add_argument("--real", type=Path, default=REAL_IN,
                        help="local real-cluster CSV from scripts/prepare_real_cluster.py")
    args = parser.parse_args(argv)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")

    if args.real.is_file():
        _write(REAL_OUT, real_snapshot(args.real, generated_at), indent=0)
    else:
        print(f"{args.real} not found: keeping the committed {REAL_OUT.name}")

    d = api.load_cluster(synthetic=True)
    _write(OUT, snapshot(d, generated_at, with_text=True), indent=0)
    if args.skip_fix_check:
        return
    started = time.perf_counter()
    fix = fix_checks(d, generated_at)
    _write(FIX_OUT, fix, separators=(",", ":"))
    print(f"{sum(len(m) for a in fix['results'].values() for m in a.values())} fix checks "
          f"in {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    main()
