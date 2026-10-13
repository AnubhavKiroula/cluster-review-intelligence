"""Export a static JSON snapshot of the SYNTHETIC cluster for the Next.js frontend.

The frontend is a pure static site: it never talks to Python at runtime. All numbers
come from the audited ``cri.api`` core (CLAUDE.md rule 1 — no fabricated values), dumped
once here. Re-run after the analytics change:

    python web/scripts/export_snapshot.py

Writes web/public/data/cluster.synthetic.json, plus fixcheck.synthetic.json: every
"Did my fix work?" result (property x aspect x month), precomputed because the site
has no backend. Only the fix-check page loads that file. ``--skip-fix-check`` skips
it (it takes a couple of minutes).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from cri import api

# CLAUDE.md rule 2: synthetic data carries "synthetic" in its filename.
OUT = Path(__file__).resolve().parents[1] / "public" / "data" / "cluster.synthetic.json"
FIX_OUT = OUT.with_name("fixcheck.synthetic.json")


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records (NaN/NA -> null, Timestamps -> ISO date)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-fix-check", action="store_true",
                        help="do not regenerate fixcheck.synthetic.json")
    args = parser.parse_args(argv)
    d = api.load_cluster(synthetic=True)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    properties = api.list_properties(d)
    aspects = api.list_aspects()
    lo, hi = api.date_range(d)

    matrix = api.cluster_matrix(d)
    cluster_matrix = {
        "properties": list(matrix.index),
        "aspects": list(matrix.columns),
        # NaN -> None so JSON carries null for "no mentions".
        "z": [[None if pd.isna(v) else round(float(v), 4) for v in row] for row in matrix.values],
    }

    all_changepoints = api.changepoints(d)
    destination = api.destination_summary(d)
    # The worst market-wide aspect, computed once here so pages do not re-rank it.
    market_wide = destination[destination["scope"] == "market-wide"].sort_values(
        ["pct_negative", "aspect"], ascending=[False, True]
    )

    per_property: dict[str, dict] = {}
    for prop in properties:
        scorecard = api.property_scorecard(d, prop)
        trends = {}
        for aspect in aspects:
            tr = api.trend(d, prop, aspect)
            if not tr.empty:
                trends[aspect] = records(tr)
        cps = all_changepoints[all_changepoints["property_id"] == prop]
        per_property[prop] = {
            "scorecard": records(scorecard),
            "priority_actions": records(api.priority_actions(d, prop)),
            "trends": trends,
            "changepoints": records(cps),
        }

    # Explorer corpus: raw reviews + classified clauses, filtered client-side.
    reviews = records(d.reviews[api.REVIEW_COLUMNS])
    mentions = records(d.labelled[["review_id", "aspect", "sentiment", "sentence"]])

    snapshot = {
        "meta": {
            "is_synthetic": bool(d.is_synthetic),
            "source_name": d.source_name,
            "generated_at": generated_at,
            "properties": properties,
            "aspects": aspects,
            "date_min": lo.date().isoformat(),
            "date_max": hi.date().isoformat(),
            "n_reviews": int(len(d.reviews)),
        },
        "cluster_matrix": cluster_matrix,
        "market_scope": records(api.market_scope(d)),
        "destination_summary": records(destination),
        "market_headline": records(market_wide.head(1))[0] if len(market_wide) else None,
        "per_property": per_property,
        "reviews": reviews,
        "mentions": mentions,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=0), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({size_kb:.0f} KB): {len(properties)} properties, {len(reviews)} reviews")

    if args.skip_fix_check:
        return
    started = time.perf_counter()
    fix = fix_checks(d, generated_at)
    FIX_OUT.write_text(json.dumps(fix, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
    n = sum(len(m) for a in fix["results"].values() for m in a.values())
    print(f"wrote {FIX_OUT} ({FIX_OUT.stat().st_size / 1024:.0f} KB): {n} fix checks "
          f"in {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    main()
