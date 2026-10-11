"""Export a static JSON snapshot of the SYNTHETIC cluster for the Next.js frontend.

The frontend is a pure static site: it never talks to Python at runtime. All numbers
come from the audited ``cri.api`` core (CLAUDE.md rule 1 — no fabricated values), dumped
once here. Re-run after the analytics change:

    python web/scripts/export_snapshot.py

Writes web/public/data/cluster.synthetic.json.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from cri import api

# CLAUDE.md rule 2: synthetic data carries "synthetic" in its filename.
OUT = Path(__file__).resolve().parents[1] / "public" / "data" / "cluster.synthetic.json"


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records (NaN/NA -> null, Timestamps -> ISO date)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def main() -> None:
    d = api.load_cluster(synthetic=True)
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
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "properties": properties,
            "aspects": aspects,
            "date_min": lo.date().isoformat(),
            "date_max": hi.date().isoformat(),
            "n_reviews": int(len(d.reviews)),
        },
        "cluster_matrix": cluster_matrix,
        "market_scope": records(api.market_scope(d)),
        "destination_summary": records(api.destination_summary(d)),
        "per_property": per_property,
        "reviews": reviews,
        "mentions": mentions,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=0), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({size_kb:.0f} KB): {len(properties)} properties, {len(reviews)} reviews")


if __name__ == "__main__":
    main()
