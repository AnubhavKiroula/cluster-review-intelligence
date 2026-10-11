"""Judge demo facts: every number docs/DEMO.md quotes, printed from the SYNTHETIC sample.

Run: ``python scripts/demo.py`` (same data as the dashboard's default source).
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
        print(actions[["aspect", "gap", "started", "rationale"]].to_string(index=False)
              if not actions.empty else "   (nothing flagged)", "\n")

    print("3. Market-wide vs property-specific:")
    scope = api.market_scope(d)[["aspect", "scope", "n_properties", "pattern"]]
    print(scope.to_string(index=False), "\n")

    print("4. Live Hinglish/Devanagari examples (explorer 'Try your own review'):")
    for text in LIVE_EXAMPLES:
        found = api.classify_text(text)
        pairs = zip(found["aspect"], found["sentiment"], strict=True)
        print(f"   {text}  ->  " + ", ".join(f"{a} {s:+d}" for a, s in pairs))
    print()

    print("5. Destination view (tourism board):")
    dest = api.destination_summary(d)[["aspect", "cluster_mean", "pct_negative", "scope"]]
    print(dest.to_string(index=False))


if __name__ == "__main__":
    main()
