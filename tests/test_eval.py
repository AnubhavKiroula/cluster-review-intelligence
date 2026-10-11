"""Focused tests for the evaluation scaffold."""

import pandas as pd
from eval.score import evaluate
from eval.split_labels import split_frame


def _gold() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "review_id": "1", "text": "food nice", "gold_aspects": "Food",
                "gold_sentiment_per_aspect": "Food=1",
            },
            {
                "review_id": "2", "text": "food bad room cold", "notes": "mixed aspects",
                "gold_aspects": "Food;Room", "gold_sentiment_per_aspect": "Food=-1;Room=-1",
            },
            {
                "review_id": "3", "text": "bad", "notes": "sarcasm", "gold_aspects": "Food",
                "gold_sentiment_per_aspect": "Food=0",
            },
        ]
    )


def test_evaluate_reports_macro_per_aspect_and_confusion_matrix():
    predictions = pd.DataFrame(
        [
            {"review_id": "1", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=1"},
            {"review_id": "2", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=1"},
            {"review_id": "3", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=-1"},
        ]
    )
    result = evaluate(_gold(), predictions)
    assert set(result["aspect"]) == {"macro", "per_aspect"}
    assert set(result["aspect"]["per_aspect"]) == {"Food", "Room"}
    assert result["aspect"]["per_aspect"]["Room"]["recall"] == 0.0
    assert result["sentiment"]["confusion_matrix"]["-1"]["1"] == 1
    assert result["sentiment"]["confusion_matrix"]["0"]["-1"] == 1


def test_error_analysis_categories_are_explicit_and_no_predictions_are_fabricated():
    result = evaluate(
        _gold(), pd.DataFrame(columns=["review_id", "pred_aspects", "pred_sentiment_per_aspect"])
    )
    assert result["n_reviews"] == 3
    assert result["error_analysis"]["mixed_aspects"] == {"reviews": 1, "errors": 1}
    assert result["error_analysis"]["sarcasm"] == {"reviews": 1, "errors": 1}
    assert result["error_analysis"]["very_short"] == {"reviews": 1, "errors": 1}


def test_invalid_sentiment_is_rejected():
    frame = _gold().assign(gold_sentiment_per_aspect="Food=2")
    try:
        evaluate(frame)
    except ValueError as error:
        assert "-1, 0, or 1" in str(error)
    else:
        raise AssertionError("invalid sentiment should fail loudly")


def test_split_is_deterministic_and_disjoint():
    frame = pd.DataFrame({"review_id": ["1", "2", "3", "4", "5"]})
    first = split_frame(frame, ["A", "P", "R"])
    second = split_frame(frame, ["A", "P", "R"])
    first_counts = [len(first[key]) for key in ("A", "P", "R")]
    second_counts = [len(second[key]) for key in ("A", "P", "R")]
    assert first_counts == second_counts
    assigned = pd.concat(first.values())
    assert sorted(assigned["review_id"].tolist()) == ["1", "2", "3", "4", "5"]
    assert assigned["review_id"].is_unique
