"""Glue: turn raw reviews into a long table of aspect mentions.

Each review can contribute several rows (one per aspect clause). Downstream
benchmarking works on this tidy frame; ``review_id`` links every mention back to
its review, so statistics can treat the review (not the mention) as the unit.
"""

from __future__ import annotations

import pandas as pd

from .classify import Classifier, RuleClassifier

LABELLED_COLUMNS = ["review_id", "property_id", "date", "aspect", "sentiment", "sentence"]


def label_reviews(df: pd.DataFrame, classifier: Classifier | None = None) -> pd.DataFrame:
    """Apply a classifier to every review, returning one row per aspect mention.

    ``review_id`` comes from the input's ``review_id`` column when present (so labels
    can be joined to gold annotations), otherwise from the frame's index. Reviews
    with missing text simply produce no mentions.
    """
    classifier = classifier or RuleClassifier()
    ids = df["review_id"].tolist() if "review_id" in df.columns else df.index.tolist()
    texts = [t if isinstance(t, str) else "" for t in df["text"].tolist()]
    mentions = classifier.classify_reviews(texts)

    records = [
        {
            "review_id": rid,
            "property_id": prop,
            "date": date,
            "aspect": m.aspect,
            "sentiment": m.sentiment,
            "sentence": m.sentence,
        }
        for rid, prop, date, found in zip(
            ids, df["property_id"].tolist(), df["date"].tolist(), mentions, strict=True
        )
        for m in found
    ]
    labelled = pd.DataFrame(records, columns=LABELLED_COLUMNS)
    # Always coerce, so an empty result still has datetime/int dtypes downstream.
    labelled["date"] = pd.to_datetime(labelled["date"])
    labelled["sentiment"] = labelled["sentiment"].astype("int64")
    return labelled
