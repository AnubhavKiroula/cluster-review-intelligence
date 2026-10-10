"""Transformer backend: hybrid logic (always tested, no torch needed) plus a gated
real-model smoke test.

Run the real-model tests with the optional extra installed:
    pip install -e ".[model]"
    CRI_MODEL_TESTS=1 python -m pytest tests/test_transformer_backend.py
"""

import os

import pandas as pd
import pytest

from cri.classify import RuleClassifier, get_classifier
from cri.transformer_backend import LABEL_TO_SENTIMENT, TransformerClassifier


class FakeModel:
    """Stand-in predictor: records calls and returns a fixed polarity per clause."""

    def __init__(self, polarity):
        self.polarity = polarity
        self.calls: list[list[str]] = []

    def __call__(self, clauses):
        self.calls.append(list(clauses))
        return [self.polarity(c) for c in clauses]


def test_aspects_come_from_rules_and_sentiment_from_the_model():
    fake = FakeModel(lambda c: -1 if "nahi" in c else 1)
    clf = TransformerClassifier(sentiment_fn=fake)
    # Rules miss this post-negation ("accha nahi" reads as positive); the model decides.
    res = clf.classify_review("Khaana accha nahi tha.")
    assert [(r.aspect, r.sentiment) for r in res] == [("Food", -1)]
    assert RuleClassifier().classify_review("Khaana accha nahi tha.")[0].sentiment == 1


def test_only_aspect_clauses_are_scored_each_distinct_clause_once():
    fake = FakeModel(lambda c: 1)
    clf = TransformerClassifier(sentiment_fn=fake)
    texts = ["The food was delicious.", "The food was delicious.", "We arrived on Monday."]
    out = clf.classify_reviews(texts)
    assert fake.calls == [["the food was delicious"]]  # one batched call, deduplicated
    assert [len(r) for r in out] == [1, 1, 0]


def test_batch_and_single_paths_agree_and_handle_missing_text():
    clf = TransformerClassifier(sentiment_fn=FakeModel(lambda c: 0))
    texts = ["The staff were rude. The room was clean.", None, ""]
    assert clf.classify_reviews(texts) == [clf.classify_review(t) for t in texts]
    assert clf.classify_reviews([None]) == [[]]


def test_wrong_number_of_scores_is_rejected():
    clf = TransformerClassifier(sentiment_fn=lambda clauses: [1])
    with pytest.raises(ValueError, match="one score per clause"):
        clf.classify_reviews(["The food was good.", "The staff were rude."])


def test_label_mapping_covers_the_model_labels():
    assert LABEL_TO_SENTIMENT == {"positive": 1, "neutral": 0, "negative": -1}


def test_registry_builds_the_backend_lazily(monkeypatch):
    # Building the classifier must not import torch or download anything.
    monkeypatch.setenv("CRI_MODEL_BACKEND", "transformer")
    assert isinstance(get_classifier(), TransformerClassifier)


# --- real model (opt-in) ------------------------------------------------------------

real_model = pytest.mark.skipif(
    os.environ.get("CRI_MODEL_TESTS") != "1",
    reason="set CRI_MODEL_TESTS=1 (and install the 'model' extra) to run the real model",
)


@real_model
def test_real_model_reads_clear_english_sentiment():
    pytest.importorskip("transformers")
    clf = TransformerClassifier()
    good = clf.classify_review("The food was absolutely delicious.")
    bad = clf.classify_review("The food was cold and disgusting.")
    assert good[0].sentiment == 1
    assert bad[0].sentiment == -1


@real_model
def test_real_model_integrates_end_to_end():
    # Integration, not quality: the model must label exactly the clauses the rules
    # find, with valid sentiments. How WELL it scores them is an evaluation result
    # (measured, and weaker than the rules on our Hinglish templates - see
    # docs/TODO_RESULTS.md), so it is not asserted here.
    pytest.importorskip("transformers")
    from cri.generate import generate
    from cri.pipeline import label_reviews

    reviews = generate(seed=42).head(300)
    model = label_reviews(reviews, classifier=TransformerClassifier())
    rules = label_reviews(reviews)
    cols = ["review_id", "aspect", "sentence"]
    pd.testing.assert_frame_equal(model[cols], rules[cols])
    assert set(model["sentiment"]) <= {-1, 0, 1}
