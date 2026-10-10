"""Aspect + sentiment classification.

Defines a small ``Classifier`` interface so a stronger backend (multilingual
transformer or LLM API) can be dropped in without changing callers, plus a
transparent rule/lexicon baseline (``RuleClassifier``) that needs no downloads.

Both word lists are config, not code: the aspect taxonomy lives in
``resources/aspects.yaml`` and the sentiment lexicon in ``resources/lexicon.yaml``.
Pick a backend with :func:`get_classifier` (``CRI_MODEL_BACKEND`` env var).
"""

from __future__ import annotations

import importlib.resources
import os
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

from .normalize import normalize, split_sentences, tokenize

BACKENDS = ("rule", "transformer")


# --- Config loading + validation ------------------------------------------------


def _read_resource(name: str) -> str:
    return importlib.resources.files("cri.resources").joinpath(name).read_text(encoding="utf-8")


def _check_terms(source: str, key: str, value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source}: '{key}' must be a non-empty list of strings.")
    for term in value:
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"{source}: '{key}' contains an empty or non-string entry: {term!r}")
        if term != term.strip().lower():
            raise ValueError(
                f"{source}: '{key}' entry {term!r} must be lowercase with no surrounding "
                "spaces (review text is lowercased before matching)."
            )
    return value


def parse_lexicon(data: object, source: str = "lexicon.yaml") -> dict[str, list[str]]:
    """Validate a lexicon mapping; raise ValueError naming the exact problem."""
    keys = ("positive", "negative", "positive_phrases", "negative_phrases", "negation")
    if not isinstance(data, dict):
        raise ValueError(f"{source}: expected a mapping with keys {list(keys)}.")
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"{source}: missing key(s) {missing}.")
    lex = {k: _check_terms(source, k, data[k]) for k in keys}
    pairs = (("positive", "negative"), ("positive_phrases", "negative_phrases"),
             ("negation", "positive"), ("negation", "negative"))
    for a, b in pairs:
        both = sorted(set(lex[a]) & set(lex[b]))
        if both:
            raise ValueError(f"{source}: {both} appear in both '{a}' and '{b}'.")
    return lex


def load_aspects() -> dict[str, list[str]]:
    """Aspect taxonomy (ordered). ``CRI_ASPECTS_PATH`` overrides the bundled file."""
    override = os.environ.get("CRI_ASPECTS_PATH")
    if override:
        source, text = override, Path(override).read_text(encoding="utf-8")
    else:
        source, text = "aspects.yaml", _read_resource("aspects.yaml")
    data = yaml.safe_load(text)
    aspects = data.get("aspects") if isinstance(data, dict) else None
    if not isinstance(aspects, dict) or not aspects:
        raise ValueError(f"{source}: expected a non-empty 'aspects' mapping.")
    return {str(name): _check_terms(source, str(name), cues) for name, cues in aspects.items()}


_LEXICON = parse_lexicon(yaml.safe_load(_read_resource("lexicon.yaml")))

# Module-level names kept for backward compatibility; contents come from lexicon.yaml.
POSITIVE = frozenset(_LEXICON["positive"])
NEGATIVE = frozenset(_LEXICON["negative"])
POSITIVE_PHRASES = tuple(_LEXICON["positive_phrases"])
NEGATIVE_PHRASES = tuple(_LEXICON["negative_phrases"])
NEGATION = frozenset(_LEXICON["negation"])


# --- Interface ------------------------------------------------------------------


@dataclass(frozen=True)
class AspectSentiment:
    """One aspect mention found in a review clause."""

    aspect: str
    sentiment: int  # -1, 0, or +1
    sentence: str


class Classifier(ABC):
    """Interface: map raw review text to a list of (aspect, sentiment) mentions."""

    @abstractmethod
    def classify_review(self, text: str) -> list[AspectSentiment]:
        ...

    def classify_reviews(self, texts: Iterable[str]) -> list[list[AspectSentiment]]:
        """Classify many reviews. Backends that batch (e.g. a model) override this."""
        return [self.classify_review(text) for text in texts]


# --- Rule / lexicon baseline ----------------------------------------------------


class RuleClassifier(Classifier):
    """Lexicon + cue-term baseline. Deterministic and inspectable."""

    def __init__(self, aspects: dict[str, list[str]] | None = None) -> None:
        self.aspects = aspects if aspects is not None else load_aspects()
        # Pre-split cue terms into single-token vs multiword for matching.
        self._single: dict[str, set[str]] = {}
        self._multi: dict[str, list[str]] = {}
        for aspect, cues in self.aspects.items():
            singles, multis = set(), []
            for cue in cues:
                cue = cue.lower()
                if " " in cue or "-" in cue or any(ord(c) > 0x7F for c in cue):
                    multis.append(cue)
                else:
                    singles.add(cue)
            self._single[aspect] = singles
            self._multi[aspect] = multis

    # -- sentiment --------------------------------------------------------------

    @staticmethod
    def sentence_sentiment(sentence: str) -> int:
        score = 0
        for phrase in POSITIVE_PHRASES:
            if phrase in sentence:
                score += 1
        for phrase in NEGATIVE_PHRASES:
            if phrase in sentence:
                score -= 1
        negate = 0
        for tok in tokenize(sentence):
            if tok in NEGATION:
                negate = 3  # flip the next few sentiment tokens
                continue
            delta = 0
            if tok in POSITIVE:
                delta = 1
            elif tok in NEGATIVE:
                delta = -1
            if delta and negate > 0:
                delta = -delta
            score += delta
            if negate > 0:
                negate -= 1
        if score > 0:
            return 1
        if score < 0:
            return -1
        return 0

    # -- aspects ----------------------------------------------------------------

    def sentence_aspects(self, sentence: str) -> list[str]:
        token_set = set(tokenize(sentence))
        found = []
        for aspect in self.aspects:
            if token_set & self._single[aspect] or any(
                m in sentence for m in self._multi[aspect]
            ):
                found.append(aspect)
        return found

    def aspect_clauses(self, text: str) -> list[tuple[str, list[str]]]:
        """(clause, aspects) for every normalised clause that mentions an aspect."""
        if not isinstance(text, str):
            return []
        out = []
        for sentence in split_sentences(normalize(text)):
            aspects = self.sentence_aspects(sentence)
            if aspects:
                out.append((sentence, aspects))
        return out

    # -- public API -------------------------------------------------------------

    def classify_review(self, text: str) -> list[AspectSentiment]:
        return [
            AspectSentiment(aspect, self.sentence_sentiment(sentence), sentence)
            for sentence, aspects in self.aspect_clauses(text)
            for aspect in aspects
        ]


def get_classifier(name: str | None = None) -> Classifier:
    """Build a backend by name, or from ``CRI_MODEL_BACKEND`` (default ``rule``)."""
    choice = (name or os.environ.get("CRI_MODEL_BACKEND") or "rule").strip().lower()
    if choice == "rule":
        return RuleClassifier()
    if choice == "transformer":
        # Imported lazily so the default install never needs torch/transformers.
        from .transformer_backend import TransformerClassifier

        return TransformerClassifier()
    raise ValueError(f"Unknown classifier backend {choice!r}; available: {', '.join(BACKENDS)}.")
