"""Text normalisation and light language/script detection.

Deliberately simple and transparent (no model downloads). Handles lowercasing,
emoji, a few common Hinglish spelling variants, and sentence splitting so the
rule classifier can assign aspects per sentence.
"""

from __future__ import annotations

import re
import unicodedata

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
    "achi": "accha",  # feminine / plural forms of the same adjective
    "achhi": "accha",
    "acchi": "accha",
    "achhe": "accha",
    "acche": "accha",
    "nahin": "nahi",
    "saaf-safai": "saaf safai",
}

# Contrastive conjunctions start a new claim ("the food was good but the room was
# cold"), so they split clauses too; otherwise opposite polarities cancel out and
# every aspect in the sentence scores 0. Not "par"/"पर": it also means "on".
# Matched between non-letters, because Devanagari vowel signs are not \w (\b misfires).
_CONTRAST = (
    "but", "however", "although", "though", "whereas",
    "lekin", "magar", "jabki", "kintu", "parantu",
    "लेकिन", "मगर", "जबकि", "किंतु", "परंतु",
)
_LETTER = "a-zऀ-ॿ'"
_SENTENCE_SPLIT = re.compile(  # the group captures a contrast word (None otherwise)
    r"[.!?;\n]+|\bor\b|\baur\b|,"
    rf"|(?<![{_LETTER}])({'|'.join(_CONTRAST)})(?![{_LETTER}])"
)
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
    # Whole words: as substrings "acha" would match "reachable", "Himachal".
    if set(_WORD.findall(lowered)) & set(hinglish_markers):
        return "hinglish"
    return "en"


def normalize(text: str) -> str:
    """NFC-normalise, lowercase, map emoji/spelling variants, collapse whitespace.

    NFC makes visually identical Devanagari spellings identical code points (e.g. a
    precomposed nukta letter typed by many keyboards vs letter + nukta), so the
    same word always matches the lexicon.
    """
    text = unicodedata.normalize("NFC", text).lower()
    for emoji, token in _EMOJI_SENTIMENT.items():
        text = text.replace(emoji, token)
    text = _EMOJI_ANY.sub(" ", text)
    tokens = (_SPELLING.get(tok, tok) for tok in text.split())
    text = " ".join(tokens)
    return _WHITESPACE.sub(" ", text).strip()


def split_clauses(text: str) -> list[tuple[str, bool]]:
    """Clause-like units, each flagged True if it follows a contrastive conjunction.

    The flag lets the classifier keep "staff was friendly but slow" about Staff.
    """
    parts = _SENTENCE_SPLIT.split(text)  # clause, separator, clause, separator, ...
    clauses, after_contrast = [], False
    for i, part in enumerate(parts):
        if i % 2:
            after_contrast = after_contrast or part is not None
        elif part and part.strip():
            clauses.append((part.strip(), after_contrast))
            after_contrast = False
    return clauses


def split_sentences(text: str) -> list[str]:
    """Split a review into clause-like units (reviews mix aspects per clause)."""
    return [clause for clause, _ in split_clauses(text)]


def tokenize(text: str) -> list[str]:
    """Word tokens over Latin + Devanagari characters."""
    return _WORD.findall(text)
