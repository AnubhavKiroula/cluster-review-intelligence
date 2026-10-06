"""Aspect + sentiment classification.

Defines a small ``Classifier`` interface so a stronger backend (multilingual
transformer or LLM API) can be dropped in later without changing callers, plus a
transparent rule/lexicon baseline (``RuleClassifier``) that needs no downloads.
"""

from __future__ import annotations

import importlib.resources
from abc import ABC, abstractmethod
from dataclasses import dataclass

import yaml

from .normalize import normalize, split_sentences, tokenize

# --- Sentiment lexicon (English + romanised Hindi) ------------------------------

POSITIVE = {
    "good", "great", "nice", "best", "amazing", "excellent", "lovely",
    "delicious", "tasty", "clean", "helpful", "friendly", "polite",
    "comfortable", "cozy", "beautiful", "wonderful", "awesome", "perfect",
    "spacious", "warm", "fresh", "accha", "badhiya", "mast", "shandar",
    "saaf", "sasta", "khush",
    # Devanagari
    "बढ़िया", "अच्छा", "साफ", "शानदार", "सुंदर",
}
NEGATIVE = {
    "bad", "worst", "poor", "terrible", "awful", "dirty", "cold", "rude",
    "slow", "broken", "expensive", "overpriced", "disappointing",
    "disappointed", "smelly", "noisy", "unhelpful", "pathetic", "stale",
    "leaking", "ganda", "gandagi", "bekaar", "kharaab", "kharab", "thanda",
    "mehenga", "mehnga", "problem",
    # Devanagari
    "बेकार", "ठंडा", "खराब", "गंदा", "गंदगी", "महंगा",
}
# Multiword expressions matched as substrings (order-sensitive negations etc.).
POSITIVE_PHRASES = ("paisa vasool", "value for money", "well maintained")
NEGATIVE_PHRASES = (
    "not working", "did not work", "didn't work", "no hot water",
    "not clean", "kaam nahi", "nahi chal", "band tha", "kaam nahi kar",
)
NEGATION = {"not", "no", "nahi", "never", "without", "bina"}


@dataclass(frozen=True)
class AspectSentiment:
    """One aspect mention found in a review clause."""

    aspect: str
    sentiment: int  # -1, 0, or +1
    sentence: str


def _load_aspects() -> dict[str, list[str]]:
    resource = importlib.resources.files("cri.resources").joinpath("aspects.yaml")
    data = yaml.safe_load(resource.read_text(encoding="utf-8"))
    return data["aspects"]


class Classifier(ABC):
    """Interface: map raw review text to a list of (aspect, sentiment) mentions."""

    @abstractmethod
    def classify_review(self, text: str) -> list[AspectSentiment]:
        ...


class RuleClassifier(Classifier):
    """Lexicon + cue-term baseline. Deterministic and inspectable."""

    def __init__(self, aspects: dict[str, list[str]] | None = None) -> None:
        self.aspects = aspects if aspects is not None else _load_aspects()
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

    # -- public API -------------------------------------------------------------

    def classify_review(self, text: str) -> list[AspectSentiment]:
        results: list[AspectSentiment] = []
        norm = normalize(text)
        for sentence in split_sentences(norm):
            aspects = self.sentence_aspects(sentence)
            if not aspects:
                continue
            sentiment = self.sentence_sentiment(sentence)
            for aspect in aspects:
                results.append(AspectSentiment(aspect, sentiment, sentence))
        return results
