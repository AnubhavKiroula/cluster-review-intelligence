"""10-line judge demo: load SYNTHETIC reviews and print the headline findings.

Run: ``python scripts/demo.py``
"""

from cri.benchmark import detect_changepoints, market_wide_summary
from cri.loader import load_reviews
from cri.pipeline import label_reviews

df = load_reviews("data/sample/synthetic_reviews.csv")
print(f"Loaded {len(df)} SYNTHETIC reviews across {df['property_id'].nunique()} properties.\n")

labelled = label_reviews(df)

print("Market-wide vs property-specific issues:")
print(market_wide_summary(labelled).to_string(index=False), "\n")

print("Detected changepoints (property x aspect):")
print(detect_changepoints(labelled).to_string(index=False))
