"""Write the shipped classifier's predictions in the format ``eval/score.py`` reads.

    python eval/predict.py eval/labelled/gold.csv --out eval/labelled/predictions.csv
    python eval/score.py eval/labelled/gold.csv --predictions eval/labelled/predictions.csv

The backend follows ``CRI_MODEL_BACKEND`` (default ``rule``). Per review and aspect
the sentiment is the sign of the mean of that aspect's clause sentiments - the same
(review, aspect) unit the analytics use (``cri.benchmark.review_units``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from cri.classify import Classifier, get_classifier, load_aspects

PREDICTION_COLUMNS = ["review_id", "pred_aspects", "pred_sentiment_per_aspect"]


def predict(frame: pd.DataFrame, classifier: Classifier | None = None) -> pd.DataFrame:
    """One prediction row per input review (blank cells = no aspect detected)."""
    missing = {"review_id", "text"} - set(frame.columns)
    if missing:
        raise ValueError(f"Input needs column(s) {sorted(missing)}")
    classifier = classifier or get_classifier()
    texts = ["" if pd.isna(t) else str(t) for t in frame["text"]]
    order = list(load_aspects())
    rows = []
    for review_id, mentions in zip(frame["review_id"], classifier.classify_reviews(texts),
                                   strict=True):
        by_aspect: dict[str, list[int]] = {}
        for mention in mentions:
            by_aspect.setdefault(mention.aspect, []).append(mention.sentiment)
        aspects = sorted(by_aspect, key=order.index)
        sentiment = {a: int(np.sign(np.mean(by_aspect[a]))) for a in aspects}
        rows.append({
            "review_id": review_id,
            "pred_aspects": ";".join(aspects),
            "pred_sentiment_per_aspect": ";".join(f"{a}={s}" for a, s in sentiment.items()),
        })
    return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Predict aspects/sentiment for scoring.")
    parser.add_argument("reviews", type=Path, help="CSV with review_id and text columns")
    parser.add_argument("--out", type=Path, required=True, help="predictions CSV to write")
    args = parser.parse_args(argv)
    predictions = predict(pd.read_csv(args.reviews))
    predictions.to_csv(args.out, index=False)
    print(f"Wrote {len(predictions)} prediction(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
