"""Optional multilingual transformer sentiment backend (``CRI_MODEL_BACKEND=transformer``).

Hybrid by design: aspects still come from the transparent cue terms in
``aspects.yaml`` (via :class:`~cri.classify.RuleClassifier`); the model replaces
only the *clause sentiment*, the part rules handle worst (post-negation such as
"accha nahi tha", implicit sentiment). Only aspect-bearing clauses are scored, each
distinct clause once, in batches.

Needs the optional extra: ``pip install -e ".[model]"`` (torch + transformers).
The model is downloaded once to the Hugging Face cache (~541 MB):
``lxyuan/distilbert-base-multilingual-cased-sentiments-student`` (Apache-2.0),
pinned to a fixed revision and loaded from safetensors (no pickled code runs).
Real-data accuracy vs the rule baseline is TBD (see docs/TODO_RESULTS.md).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .classify import AspectSentiment, Classifier, RuleClassifier

MODEL_ID = "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
MODEL_REVISION = "cf991100d706c13c0a080c097134c05b7f436c45"  # pinned for reproducibility
LABEL_TO_SENTIMENT = {"positive": 1, "neutral": 0, "negative": -1}

SentimentFn = Callable[[list[str]], list[int]]


def load_model_sentiment_fn(batch_size: int = 32, max_length: int = 128) -> SentimentFn:
    """Build ``clauses -> [-1|0|+1]`` from the pinned Hugging Face model (CPU)."""
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "The transformer backend needs the optional 'model' extra: "
            'pip install -e ".[model]"'
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, use_safetensors=True
    )
    model.eval()
    labels = {int(i): str(name).lower() for i, name in model.config.id2label.items()}
    if set(labels.values()) != set(LABEL_TO_SENTIMENT):
        raise ValueError(f"Unexpected model labels {sorted(labels.values())}")

    def predict(clauses: list[str]) -> list[int]:
        out: list[int] = []
        for start in range(0, len(clauses), batch_size):
            batch = clauses[start:start + batch_size]
            enc = tokenizer(batch, padding=True, truncation=True, max_length=max_length,
                            return_tensors="pt")
            with torch.no_grad():
                best = model(**enc).logits.argmax(dim=-1).tolist()
            out.extend(LABEL_TO_SENTIMENT[labels[i]] for i in best)
        return out

    return predict


class TransformerClassifier(Classifier):
    """Rule-based aspects + model-based clause sentiment."""

    def __init__(
        self,
        sentiment_fn: SentimentFn | None = None,
        *,
        rules: RuleClassifier | None = None,
        batch_size: int = 32,
    ) -> None:
        # ``sentiment_fn`` is injectable so the hybrid logic is testable without torch.
        self._sentiment_fn = sentiment_fn
        self._rules = rules or RuleClassifier()
        self._batch_size = batch_size

    def _score(self, clauses: list[str]) -> list[int]:
        if self._sentiment_fn is None:
            self._sentiment_fn = load_model_sentiment_fn(self._batch_size)
        scores = self._sentiment_fn(clauses)
        if len(scores) != len(clauses):
            raise ValueError("sentiment_fn must return one score per clause")
        return scores

    def classify_reviews(self, texts: Iterable[str]) -> list[list[AspectSentiment]]:
        per_review = [self._rules.aspect_clauses(text) for text in texts]
        distinct = list(dict.fromkeys(c for clauses in per_review for c, _ in clauses))
        scores = dict(zip(distinct, self._score(distinct), strict=True)) if distinct else {}
        return [
            [AspectSentiment(aspect, scores[clause], clause)
             for clause, aspects in clauses for aspect in aspects]
            for clauses in per_review
        ]

    def classify_review(self, text: str) -> list[AspectSentiment]:
        return self.classify_reviews([text])[0]
