"""Score human labels against model predictions.

Inputs follow ``docs/labelling_template.csv``; predictions are either ``pred_*``
columns in the same file or a separate CSV with the same ``review_id`` values (write
one for the shipped classifier with ``eval/predict.py``).

Only reviews a human has labelled are scored. A row with blank ``gold_*`` cells is
"not labelled yet" and is skipped (and counted); a labelled review that mentions no
aspect has ``gold_aspects = none``. Aspect names are matched case-insensitively and
must belong to the taxonomy in ``src/cri/resources/aspects.yaml``.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from cri.classify import load_aspects

SENTIMENTS = (-1, 0, 1)
NO_ASPECT = "none"  # an explicit "labelled, no aspect mentioned"
TAXONOMY = {name.lower(): name for name in load_aspects()}


def _parts(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def _aspect(name: str) -> str:
    try:
        return TAXONOMY[name.strip().lower()]
    except KeyError:
        valid = sorted(TAXONOMY.values())
        raise ValueError(f"Unknown aspect {name!r}; use one of {valid} or {NO_ASPECT!r}") from None


def _review_id(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip()
    return re.sub(r"^(\d+)\.0+$", r"\1", text)  # ids read as floats: "1.0" == "1"


def _text(value: object) -> str:
    return "" if value is None or pd.isna(value) else str(value)


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
        result[_aspect(aspect)] = sentiment
    return result


def _column(frame: pd.DataFrame, *names: str) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def _records(
    frame: pd.DataFrame, *, prediction: bool = False
) -> tuple[dict[str, dict[str, Any]], int]:
    """Parse rows into records keyed by review_id; also return the unlabelled count."""
    if "review_id" not in frame.columns:
        raise ValueError("Annotations require a 'review_id' column")
    prefix = "pred" if prediction else "gold"
    aspects_col = _column(frame, f"{prefix}_aspects")
    sentiment_col = _column(frame, f"{prefix}_sentiment_per_aspect")
    if aspects_col is None and sentiment_col is None:
        raise ValueError(f"Annotations require {prefix}_aspects and/or "
                         f"{prefix}_sentiment_per_aspect columns")
    ids = frame["review_id"].map(_review_id)
    if (ids == "").any():
        raise ValueError("review_id must be non-empty")
    duplicated = sorted(set(ids[ids.duplicated()]))
    if duplicated:
        raise ValueError(f"Duplicate review_id value(s): {duplicated[:5]}")

    records: dict[str, dict[str, Any]] = {}
    unlabelled = 0
    for review_id, (_, row) in zip(ids, frame.iterrows(), strict=True):
        raw_aspects = _parts(row[aspects_col]) if aspects_col else []
        raw_sentiments = row[sentiment_col] if sentiment_col else None
        if not prediction and not raw_aspects and not _parts(raw_sentiments):
            unlabelled += 1  # blank gold cells: a human has not labelled this row yet
            continue
        sentiments = _sentiments(raw_sentiments)
        aspects = {_aspect(a) for a in raw_aspects if a.lower() != NO_ASPECT}
        aspects.update(sentiments)
        records[review_id] = {
            "aspects": aspects,
            "sentiments": sentiments,
            "text": _text(row.get("text")),
            "notes": _text(row.get("notes")),
        }
    return records, unlabelled


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _category(record: dict[str, Any]) -> str | None:
    notes = record["notes"].lower()
    if re.search(r"sarcas|ironi", notes):
        return "sarcasm"
    if len(record["aspects"]) > 1 or re.search(r"mixed", notes):
        return "mixed_aspects"
    words = len(record["text"].split())
    if 0 < words <= 3 or re.search(r"very short|short review", notes):
        return "very_short"
    return None


def evaluate(gold: pd.DataFrame, predicted: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return evaluation metrics for the human-labelled reviews in ``gold``.

    Aspect metrics are one-vs-rest per aspect (macro = unweighted mean). A labelled
    review with no prediction counts as "predicted nothing", never as neutral.
    Sentiment metrics (accuracy, per-class and macro F1 over -1/0/1) are computed on
    aspects that both the human and the model found. Undefined metrics are ``None``.
    """
    gold_rows, unlabelled = _records(gold)
    if predicted is None:
        if not {"pred_aspects", "pred_sentiment_per_aspect"} & set(gold.columns):
            raise ValueError("Provide a predictions frame or pred_* columns in the gold frame")
        predicted = gold
    pred_rows, _ = _records(predicted, prediction=True)

    ids = sorted(gold_rows)
    nothing: dict[str, Any] = {"aspects": set(), "sentiments": {}}
    preds = {review_id: pred_rows.get(review_id, nothing) for review_id in ids}
    aspects = sorted(
        set().union(*(gold_rows[i]["aspects"] | preds[i]["aspects"] for i in ids))
    )
    per_aspect: dict[str, dict[str, float]] = {}
    for aspect in aspects:
        tp = fp = fn = 0
        for review_id in ids:
            expected = aspect in gold_rows[review_id]["aspects"]
            actual = aspect in preds[review_id]["aspects"]
            tp += expected and actual
            fp += not expected and actual
            fn += expected and not actual
        per_aspect[aspect] = _prf(tp, fp, fn)
    macro = {key: _mean([item[key] for item in per_aspect.values()])
             for key in ("precision", "recall", "f1")}

    confusion = {str(g): {str(p): 0 for p in SENTIMENTS} for g in SENTIMENTS}
    for review_id in ids:
        gold_sent, pred_sent = gold_rows[review_id]["sentiments"], preds[review_id]["sentiments"]
        for aspect in set(gold_sent) & set(pred_sent):
            confusion[str(gold_sent[aspect])][str(pred_sent[aspect])] += 1
    pairs = sum(sum(row.values()) for row in confusion.values())
    per_class = {}
    for label in map(str, SENTIMENTS):
        tp = confusion[label][label]
        fp = sum(confusion[g][label] for g in confusion if g != label)
        fn = sum(n for p, n in confusion[label].items() if p != label)
        if tp + fp + fn:
            per_class[label] = _prf(tp, fp, fn)

    categories: dict[str, dict[str, int]] = defaultdict(lambda: {"reviews": 0, "errors": 0})
    for review_id in ids:
        category = _category(gold_rows[review_id])
        if category:
            categories[category]["reviews"] += 1
            errors = gold_rows[review_id]["aspects"] != preds[review_id]["aspects"]
            categories[category]["errors"] += int(errors)
    return {
        "n_reviews": len(ids),
        "n_unlabelled_skipped": unlabelled,
        "n_missing_predictions": sum(i not in pred_rows for i in ids),
        "n_predictions_without_gold": len(set(pred_rows) - set(gold_rows)),
        "aspects": aspects,
        "aspect": {"macro": macro, "per_aspect": per_aspect},
        "sentiment": {
            "n_matched_aspects": pairs,
            "accuracy": sum(confusion[s][s] for s in confusion) / pairs if pairs else None,
            "macro_f1": _mean([item["f1"] for item in per_class.values()]),
            "per_class": per_class,
            "confusion_matrix": confusion,
        },
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
