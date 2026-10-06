"""Text normalisation and light language/script detection.

Deliberately simple and transparent (no model downloads). Handles lowercasing,
emoji, a few common Hinglish spelling variants, and sentence splitting so the
rule classifier can assign aspects per sentence.
"""

from __future__ import annotations

import re

# Devanagari Unicode block.
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# A handful of emoji mapped to sentiment tokens; the rest are stripped.
_EMOJI_SENTIMENT = {
    "\U0001f60a": " good ",
    "\U0001f600": " good ",
    "\U0001f44d": " good ",
    "❤": " good ",
    "\U0001f620": " bad ",
    "\U0001f621": " bad ",
    "\U0001f44e": " bad ",
    "\U0001f922": " bad ",
}
_EMOJI_ANY = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]"
)

# Common romanised-Hindi shorthand -> canonical form used in the lexicon.
_SPELLING = {
    "nhi": "nahi",
    "bht": "bahut",
    "bohot": "bahut",
    "gnda": "ganda",
    "acha": "accha",
    "achha": "accha",
    "saaf-safai": "saaf safai",
}

_SENTENCE_SPLIT = re.compile(r"[.!?;\n]+|\bor\b|\baur\b|,")
_WHITESPACE = re.compile(r"\s+")
_WORD = re.compile(r"[a-zऀ-ॿ']+")


def detect_language(text: str) -> str:
    """Very rough script/language hint: 'hi', 'hinglish', or 'en'.

    Not used for classification decisions (the lexicon is multilingual); it only
    populates/validates the ``language_hint`` metadata column.
    """
    if _DEVANAGARI.search(text):
        return "hi"
    lowered = text.lower()
    hinglish_markers = (
        "khaana", "khana", "kamra", "accha", "acha", "bahut", "nahi",
        "saaf", "ganda", "mehenga", "paisa", "badhiya", "thanda",
    )
    if any(m in lowered for m in hinglish_markers):
        return "hinglish"
    return "en"


def normalize(text: str) -> str:
    """Lowercase, map emoji/spelling variants, collapse whitespace."""
    text = text.lower()
    for emoji, token in _EMOJI_SENTIMENT.items():
        text = text.replace(emoji, token)
    text = _EMOJI_ANY.sub(" ", text)
    tokens = (_SPELLING.get(tok, tok) for tok in text.split())
    text = " ".join(tokens)
    return _WHITESPACE.sub(" ", text).strip()


def split_sentences(text: str) -> list[str]:
    """Split a review into clause-like units (reviews mix aspects per clause)."""
    parts = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def tokenize(text: str) -> list[str]:
    """Word tokens over Latin + Devanagari characters."""
    return _WORD.findall(text)
