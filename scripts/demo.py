"""Judge demo facts: every number docs/DEMO.md quotes, printed from the SYNTHETIC sample.

Run: ``python scripts/demo.py`` (the same data as the web app's snapshot).
"""

import sys

import pandas as pd

from cri import api

# Typed live in the explorer's "Try your own review" box (pinned by tests/test_demo.py).
LIVE_EXAMPLES = [
    "Khana accha tha lekin kamra ganda tha.",
    "Khaana bahut swadisht tha but room thanda tha.",
    "कमरा साफ़ था और view zabardast tha.",
    "Heater kaam nahi kar raha tha, raat bhar thand lagi.",
    "Staff bahut helpful tha, paisa vasool.",
    "Khaana accha nahi tha.",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Devanagari on a Windows console
    pd.set_option("display.width", 160)
    pd.set_option("display.max_colwidth", 90)

    d = api.load_cluster()
    print(f"Loaded {len(d.reviews)} SYNTHETIC reviews across {len(api.list_properties(d))} "
          f"properties ({d.source_name}).\n")

    print("1. Hook - star averages (two near-identical averages, one hides a problem):")
    stars = d.reviews.groupby("property_id")["rating"].agg(stars="mean", reviews="size")
    print(stars.round(2).loc[api.list_properties(d)].to_string(), "\n")

    for prop in ("Property F", "Property I"):
        actions = api.priority_actions(d, prop)
        print(f"2. {prop} - fix this first:")
        cols = ["aspect", "gap", "started", "whose_problem", "whose_detail"]
        print(actions[cols].to_string(index=False)
              if not actions.empty else "   (nothing flagged)", "\n")
    room = api.priority_actions(d, "Property D").set_index("aspect").loc["Room"]
    print(f"2b. Property D, Room - {room['whose_problem']}: {room['whose_detail']}\n")

    print("3. Market-wide vs property-specific:")
    scope = api.market_scope(d)[["aspect", "scope", "n_properties", "pattern"]]
    print(scope.to_string(index=False), "\n")

    print("4. Did my fix work? Property A, Room, 2025-12 (a December renovation):")
    fix = api.intervention_check(d, "Property A", "Room", "2025-12")
    print(f"   plain before/after {fix['naive_delta']:+.2f}, market {fix['market_delta']:+.2f}, "
          f"relative to the market {fix['effect']:+.2f} -> {fix['verdict']}\n")

    print("5. Live Hinglish/Devanagari examples (explorer 'Try your own review'):")
    for text in LIVE_EXAMPLES:
        found = api.classify_text(text)
        pairs = zip(found["aspect"], found["sentiment"], strict=True)
        print(f"   {text}  ->  " + ", ".join(f"{a} {s:+d}" for a, s in pairs))


if __name__ == "__main__":
    main()
