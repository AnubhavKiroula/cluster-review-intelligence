"""Score human labels against model predictions.

The evaluator intentionally uses only the Python standard library and pandas,
which are already project dependencies.  Inputs follow ``docs/labelling_template.csv``
and may contain either ``pred_*`` columns or a separate predictions file with the
same ``review_id`` values.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

SENTIMENTS = (-1, 0, 1)
_MISSING = {"", "nan", "none", "null"}


def _parts(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def _sentiments(value: object) -> dict[str, int]:
    """Parse ``Aspect=sentiment;Other=-1`` without silently accepting bad labels."""
    result: dict[str, int] = {}
    for item in _parts(value):
        if "=" not in item:
            raise ValueError(f"Invalid sentiment label {item!r}; expected Aspect=-1|0|1")
        aspect, raw = (piece.strip() for piece in item.split("=", 1))
        try:
            sentiment = int(raw)
        except ValueError as exc:
            raise ValueError(f"Invalid sentiment for {aspect!r}: {raw!r}") from exc
        if sentiment not in SENTIMENTS:
            raise ValueError(f"Sentiment for {aspect!r} must be -1, 0, or 1")
        result[aspect] = sentiment
    return result


def _column(frame: pd.DataFrame, *names: str) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def _records(frame: pd.DataFrame, *, prediction: bool = False) -> dict[str, dict[str, Any]]:
    id_col = _column(frame, "review_id")
    if id_col is None:
        raise ValueError("Annotations require a 'review_id' column")
    aspects_col = _column(
        frame,
        "pred_aspects" if prediction else "gold_aspects",
        "predicted_aspects" if prediction else "aspects",
    )
    sentiment_col = _column(
        frame,
        "pred_sentiment_per_aspect" if prediction else "gold_sentiment_per_aspect",
        "predicted_sentiment_per_aspect" if prediction else "sentiment_per_aspect",
    )
    if aspects_col is None and sentiment_col is None:
        raise ValueError("Annotations require aspect and/or sentiment columns")
    records: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        review_id = str(row[id_col])
        if review_id.lower() in _MISSING:
            raise ValueError("review_id must be non-empty")
        sentiments = _sentiments(row[sentiment_col]) if sentiment_col else {}
        aspects = set(_parts(row[aspects_col])) if aspects_col else set()
        aspects.update(sentiments)
        records[review_id] = {
            "aspects": aspects,
            "sentiments": sentiments,
            "text": str(row.get("text", "") or ""),
            "notes": str(row.get("notes", "") or ""),
        }
    return records


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _category(record: dict[str, Any]) -> str | None:
    notes = record["notes"].lower()
    if re.search(r"sarcas|ironi", notes):
        return "sarcasm"
    if len(record["aspects"]) > 1 or re.search(r"mixed", notes):
        return "mixed_aspects"
    if len(record["text"].split()) <= 3 or re.search(r"very short|short review", notes):
        return "very_short"
    return None


def evaluate(gold: pd.DataFrame, predicted: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return honest evaluation metrics for supplied gold and predicted labels.

    Aspect metrics are one-vs-rest over the union of observed aspects. Sentiment
    metrics are calculated only for aspects present in the gold or prediction;
    absent sides are represented as ``None`` in error analysis, not as neutral.
    """
    gold_rows = _records(gold)
    if predicted is None:
        combined_prediction_columns = {"pred_aspects", "pred_sentiment_per_aspect"}
        if not combined_prediction_columns & set(gold.columns):
            raise ValueError("Provide a predictions frame or pred_* columns in the gold frame")
        pred_input, has_separate_predictions = gold, True
    else:
        pred_input, has_separate_predictions = predicted, True
    pred_rows = _records(pred_input, prediction=has_separate_predictions)
    ids = sorted(set(gold_rows) | set(pred_rows))
    aspects = sorted(set().union(*(gold_rows.get(i, {}).get("aspects", set()) for i in ids)) |
                    set().union(*(pred_rows.get(i, {}).get("aspects", set()) for i in ids)))
    per_aspect: dict[str, dict[str, float]] = {}
    for aspect in aspects:
        tp = fp = fn = 0
        for review_id in ids:
            expected = aspect in gold_rows.get(review_id, {}).get("aspects", set())
            actual = aspect in pred_rows.get(review_id, {}).get("aspects", set())
            tp += expected and actual
            fp += not expected and actual
            fn += expected and not actual
        per_aspect[aspect] = _prf(tp, fp, fn)
    macro = {key: sum(item[key] for item in per_aspect.values()) / len(per_aspect)
             if per_aspect else 0.0 for key in ("precision", "recall", "f1")}

    confusion = {str(gold_sentiment): {str(pred_sentiment): 0 for pred_sentiment in SENTIMENTS}
                 for gold_sentiment in SENTIMENTS}
    sentiment_pairs = 0
    for review_id in ids:
        gold_sent = gold_rows.get(review_id, {}).get("sentiments", {})
        pred_sent = pred_rows.get(review_id, {}).get("sentiments", {})
        for aspect in set(gold_sent) & set(pred_sent):
            confusion[str(gold_sent[aspect])][str(pred_sent[aspect])] += 1
            sentiment_pairs += 1

    categories: dict[str, dict[str, int]] = defaultdict(lambda: {"reviews": 0, "errors": 0})
    for review_id in ids:
        record = gold_rows.get(review_id, pred_rows.get(review_id, {}))
        category = _category(record)
        if category:
            expected = record.get("aspects", set())
            actual = pred_rows.get(review_id, {}).get("aspects", set())
            categories[category]["reviews"] += 1
            categories[category]["errors"] += int(expected != actual)
    return {
        "n_reviews": len(ids),
        "aspects": sorted(aspects),
        "aspect": {"macro": macro, "per_aspect": per_aspect},
        "sentiment": {"n_matched_aspects": sentiment_pairs, "confusion_matrix": confusion},
        "error_analysis": dict(categories),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score labelled review annotations.")
    parser.add_argument("gold", type=Path, help="CSV containing gold_* columns")
    parser.add_argument("--predictions", type=Path, help="CSV containing pred_* columns")
    args = parser.parse_args(argv)
    predictions = pd.read_csv(args.predictions) if args.predictions else None
    result = evaluate(pd.read_csv(args.gold), predictions)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
