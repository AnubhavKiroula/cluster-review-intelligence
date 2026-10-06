"""Glue: turn raw reviews into a long table of (property, date, aspect, sentiment).

Each review can contribute several rows (one per aspect clause). Downstream
benchmarking works on this tidy frame.
"""

from __future__ import annotations

import pandas as pd

from .classify import Classifier, RuleClassifier

LABELLED_COLUMNS = ["property_id", "date", "aspect", "sentiment", "sentence"]


def label_reviews(df: pd.DataFrame, classifier: Classifier | None = None) -> pd.DataFrame:
    """Apply a classifier to every review, returning one row per aspect mention."""
    classifier = classifier or RuleClassifier()
    records: list[dict] = []
    for row in df.itertuples(index=False):
        for mention in classifier.classify_review(row.text):
            records.append(
                {
                    "property_id": row.property_id,
                    "date": row.date,
                    "aspect": mention.aspect,
                    "sentiment": mention.sentiment,
                    "sentence": mention.sentence,
                }
            )
    labelled = pd.DataFrame(records, columns=LABELLED_COLUMNS)
    if not labelled.empty:
        labelled["date"] = pd.to_datetime(labelled["date"])
    return labelled
