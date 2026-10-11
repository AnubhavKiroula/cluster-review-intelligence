"""Focused tests for the evaluation scaffold."""

import pandas as pd
import pytest
from eval.predict import predict
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


# --- hand-computed metrics -----------------------------------------------------------

def _labelled_and_predicted():
    gold = pd.DataFrame(
        [
            {"review_id": 1, "text": "food nice", "gold_aspects": "Food",
             "gold_sentiment_per_aspect": "Food=1"},
            {"review_id": 2, "text": "food bad room cold", "gold_aspects": "food;room",
             "gold_sentiment_per_aspect": "Food=-1;Room=-1"},
            {"review_id": 3, "text": "the food was okay", "gold_aspects": "Food",
             "gold_sentiment_per_aspect": "Food=0"},
            {"review_id": 4, "text": "we stayed two nights", "gold_aspects": "none",
             "gold_sentiment_per_aspect": ""},
            {"review_id": None, "text": None, "gold_aspects": None,
             "gold_sentiment_per_aspect": None},
        ]
    )
    gold.loc[4, "review_id"] = 5  # the column is float (1.0, 2.0...) as read from a CSV
    pred = pd.DataFrame(
        [
            {"review_id": "1", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=1"},
            {"review_id": "2", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=1"},
            {"review_id": "3", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=-1"},
            {"review_id": "4", "pred_aspects": "Room", "pred_sentiment_per_aspect": "Room=-1"},
            {"review_id": "5", "pred_aspects": "Food", "pred_sentiment_per_aspect": "Food=1"},
        ]
    )
    return gold, pred


def test_metrics_match_a_hand_computed_example():
    result = evaluate(*_labelled_and_predicted())
    # Rows 1-4 are labelled; row 5 has blank gold cells (not labelled yet).
    assert (result["n_reviews"], result["n_unlabelled_skipped"]) == (4, 1)
    assert result["n_predictions_without_gold"] == 1
    food, room = (result["aspect"]["per_aspect"][a] for a in ("Food", "Room"))
    assert food == {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    assert room == {"precision": 0.0, "recall": 0.0, "f1": 0.0}  # missed in 2, invented in 4
    assert result["aspect"]["macro"]["f1"] == pytest.approx(0.5)
    sentiment = result["sentiment"]
    # Matched Food pairs (gold, pred): (1, 1), (-1, 1), (0, -1).
    assert sentiment["n_matched_aspects"] == 3
    assert sentiment["accuracy"] == pytest.approx(1 / 3)
    assert sentiment["per_class"]["1"]["f1"] == pytest.approx(2 / 3)  # P 1/2, R 1
    assert sentiment["macro_f1"] == pytest.approx((2 / 3 + 0 + 0) / 3)


def test_integer_ids_read_as_floats_still_match():
    gold, pred = _labelled_and_predicted()
    as_floats = gold.assign(review_id=gold["review_id"].astype(float))
    assert evaluate(as_floats, pred)["n_missing_predictions"] == 0


def test_duplicate_review_ids_are_rejected():
    gold, pred = _labelled_and_predicted()
    with pytest.raises(ValueError, match="Duplicate review_id"):
        evaluate(pd.concat([gold, gold.head(1)]), pred)


def test_unknown_aspects_are_rejected_with_the_valid_options():
    gold, pred = _labelled_and_predicted()
    with pytest.raises(ValueError, match="Unknown aspect 'Wifi'.*Food"):
        evaluate(gold.assign(gold_aspects="Wifi"), pred)


def test_blank_text_is_not_a_very_short_review():
    gold, pred = _labelled_and_predicted()
    result = evaluate(gold.assign(text=None, notes=None), pred)
    assert "very_short" not in result["error_analysis"]


def test_the_labelling_template_scores_only_its_labelled_row():
    template = pd.read_csv("docs/labelling_template.csv")
    result = evaluate(template, predict(template))
    assert (result["n_reviews"], result["n_unlabelled_skipped"]) == (1, 1)


def test_predict_writes_one_row_per_review_in_taxonomy_order():
    frame = pd.DataFrame({
        "review_id": ["a", "b", "c"],
        "text": ["The room was dirty. The food was delicious.", "We stayed two nights.", None],
    })
    out = predict(frame)
    assert list(out.columns) == ["review_id", "pred_aspects", "pred_sentiment_per_aspect"]
    assert out.loc[0, "pred_aspects"].split(";")[:2] == ["Food", "Room"]
    assert "Food=1" in out.loc[0, "pred_sentiment_per_aspect"]
    assert (out.loc[1:, "pred_aspects"] == "").all()


def test_predict_uses_the_sign_of_the_mean_clause_sentiment():
    mixed = pd.DataFrame({"review_id": [1], "text": ["Staff were rude. Staff were helpful."]})
    out = predict(mixed)
    assert out.loc[0, "pred_sentiment_per_aspect"] == "Staff=0"


def test_score_cli_prints_json(tmp_path, capsys):
    import json

    from eval.score import main

    gold, pred = _labelled_and_predicted()
    gold.to_csv(tmp_path / "gold.csv", index=False)
    pred.to_csv(tmp_path / "pred.csv", index=False)
    assert main([str(tmp_path / "gold.csv"), "--predictions", str(tmp_path / "pred.csv")]) == 0
    assert json.loads(capsys.readouterr().out)["n_reviews"] == 4
