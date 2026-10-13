"""Judge demo facts: every number docs/DEMO.md quotes.

- Part A, the REAL cluster: read from the committed snapshot
  ``web/public/data/cluster.real.json`` (aggregates of the real Kausani reviews, which
  stay local; re-export with ``python web/scripts/export_snapshot.py``).
- Part B, the method demo on the SYNTHETIC timeline: computed live with ``cri.api``.

Run: ``python scripts/demo.py``. ``tests/test_demo.py`` pins the same numbers.
"""

import json
import sys
from pathlib import Path

import pandas as pd

from cri import api

REAL = Path(__file__).resolve().parents[1] / "web/public/data/cluster.real.json"

# Typed live in the explorer's "Try your own review" box (pinned by tests/test_demo.py).
LIVE_EXAMPLES = [
    "Khana accha tha lekin kamra ganda tha.",
    "Khaana bahut swadisht tha but room thanda tha.",
    "कमरा साफ़ था और view zabardast tha.",
    "Heater kaam nahi kar raha tha, raat bhar thand lagi.",
    "Staff bahut helpful tha, paisa vasool.",
    "Khaana accha nahi tha.",
]


def load_real() -> dict:
    return json.loads(REAL.read_text(encoding="utf-8"))


def real_part(snap: dict) -> None:
    meta, prov = snap["meta"], snap["meta"]["provenance"]
    print(f"A. REAL cluster: {prov['town']} ({prov['district']}, {prov['state']}): "
          f"{prov['hotels']} hotels, {meta['n_reviews']:,} reviews, {prov['platform']} "
          f"(inferred); review dates: {'yes' if meta['has_dates'] else 'none in the source'}.")
    print(f"   Scale: {meta['n_reviews']:,} reviews analysed vs a median of "
          f"{prov['median_reviews_per_hotel']:g} per hotel.\n")

    print("A1. Hook - star averages:")
    for prop in ("Property I", "Property Y"):
        p = snap["per_property"][prop]
        print(f"   {prop}: {p['stars']['mean']:.2f} stars ({p['stars']['n_reviews']} reviews)")
    print()
    for prop in ("Property Y", "Property I"):
        print(f"A2. {prop} - fix this first:")
        for r in snap["per_property"][prop]["priority_actions"] or [None]:
            print(f"   {r['aspect']}: {r['gap']:.2f} below the cluster; {r['whose_problem']}"
                  if r else "   (nothing flagged)")
    flagged = [p for p, v in snap["per_property"].items() if v["priority_actions"]]
    print(f"\nA3. Market: shared weak spot = {snap['market_headline']}; "
          f"{len(flagged)} of {len(snap['per_property'])} hotels have a flagged gap.")
    for r in snap["market_scope"]:
        print(f"   {r['aspect']}: {r['scope']} ({r['n_properties']}) - {r['properties']}")
    top = sorted(snap["destination_summary"], key=lambda r: -r["pct_negative"])[:3]
    print("   Most complained about: " + ", ".join(
        f"{r['aspect']} {r['pct_negative']:.0%}" for r in top) + "\n")


def demo_part() -> None:
    d = api.load_cluster()
    print(f"B. Method demo on the SYNTHETIC timeline ({d.source_name}):")
    stars = d.reviews.groupby("property_id")["rating"].mean().round(2)
    print(f"B1. Property F {stars['Property F']:.2f} stars vs Property I {stars['Property I']:.2f}")
    top = api.priority_actions(d, "Property F").iloc[0]
    print(f"B2. Property F: fix {top['aspect']} first since {top['started']}, "
          f"{top['whose_problem']}: {top['whose_detail']}")
    room = api.priority_actions(d, "Property D").set_index("aspect").loc["Room"]
    print(f"    Property D, Room - {room['whose_problem']}: {room['whose_detail']}")
    scope = api.market_scope(d)[["aspect", "scope", "n_properties", "pattern"]]
    print("B3. Market-wide vs property-specific:\n" + scope.to_string(index=False))
    fix = api.intervention_check(d, "Property A", "Room", "2025-12")
    print(f"B4. Did my fix work? Property A, Room, 2025-12: plain before/after "
          f"{fix['naive_delta']:+.2f}, market {fix['market_delta']:+.2f}, relative to the "
          f"market {fix['effect']:+.2f} -> {fix['verdict']}\n")

    print("C. Live examples (explorer 'Try your own review'):")
    for text in LIVE_EXAMPLES:
        found = api.classify_text(text)
        pairs = zip(found["aspect"], found["sentiment"], strict=True)
        print(f"   {text}  ->  " + ", ".join(f"{a} {s:+d}" for a, s in pairs))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Devanagari on a Windows console
    pd.set_option("display.width", 160)
    pd.set_option("display.max_colwidth", 90)
    real_part(load_real())
    demo_part()


if __name__ == "__main__":
    main()
