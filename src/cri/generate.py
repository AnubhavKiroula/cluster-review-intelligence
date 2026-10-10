"""Seeded SYNTHETIC review generator.

Produces reviews for a fictional cluster of 12 hill-town properties, mixing
English, romanised Hinglish, and Devanagari. Two patterns are injected into the
review *text* (not metadata), so the end-to-end pipeline genuinely has to recover
them:

  1. ``Property F`` food quality collapses from 2025-06 onward (property-specific
     step change).
  2. Every December, heating/room complaints spike across ALL properties
     (market-wide seasonal dip).

The injected ground truth is exported as ``INJECTED_PATTERNS`` for tests.
Everything here is SYNTHETIC — see the filename and README captions.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CLUSTER_NAME = "SYNTHETIC hill-town cluster"
PROPERTIES = [f"Property {c}" for c in "ABCDEFGHIJKL"]
PLATFORMS = ["GoogleMaps", "Booking", "TripAdvisor", "MakeMyTrip"]

ASPECTS = [
    "Food", "Room", "Housekeeping", "Staff",
    "Location", "Value for Money", "Cleanliness", "Booking Experience",
]
# Relative frequency with which each aspect is mentioned.
ASPECT_WEIGHTS = np.array([3.0, 3.0, 1.5, 2.0, 1.5, 1.5, 2.0, 1.0])

DEFAULT_START = "2024-01"
DEFAULT_END = "2025-12"

# --- Injected ground truth (used by tests) --------------------------------------

FOOD_DECLINE_PROPERTY = "Property F"
FOOD_DECLINE_MONTH = pd.Timestamp("2025-06-01")

INJECTED_PATTERNS = {
    "food_decline": {
        "property": FOOD_DECLINE_PROPERTY,
        "aspect": "Food",
        "change_month": FOOD_DECLINE_MONTH.strftime("%Y-%m"),
        "direction": "negative",
        "scope": "property-specific",
    },
    "december_heating": {
        "property": "ALL",
        "aspect": "Room",
        "season": "December",
        "direction": "negative",
        "scope": "market-wide",
    },
}

# --- Review text templates: (aspect, polarity) -> list of (lang, text) ----------
# Each template embeds the aspect cue term(s) and clear sentiment words so the
# rule classifier recovers them. Keep cues distinct per aspect.

TEMPLATES: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("Food", "pos"): [
        ("en", "The food was delicious and the breakfast was fresh"),
        ("hinglish", "Khaana badhiya tha aur nashta bhi tasty"),
        ("hi", "खाना बहुत बढ़िया था"),
    ],
    ("Food", "neg"): [
        ("en", "The food was stale and cold, really disappointing"),
        ("hinglish", "Khaana bekaar aur thanda tha"),
        ("hi", "खाना बेकार और ठंडा था"),
    ],
    ("Room", "pos"): [
        ("en", "The room was spacious and comfortable with a warm heater"),
        ("hinglish", "Kamra badhiya aur comfortable tha"),
    ],
    ("Room", "neg"): [
        ("en", "The room heater was not working and it was freezing cold at night"),
        ("hinglish", "Kamre ka heater band tha, bahut thanda kamra"),
        ("hi", "कमरे का हीटर खराब था"),
    ],
    ("Housekeeping", "pos"): [
        ("en", "Housekeeping was prompt and the towels were fresh"),
        ("hinglish", "Room service accha tha, towels clean the"),
    ],
    ("Housekeeping", "neg"): [
        ("en", "Housekeeping never changed the towels, poor service"),
        ("hinglish", "Towels ganda the, room service bekaar"),
    ],
    ("Staff", "pos"): [
        ("en", "The staff were friendly and the reception was helpful"),
        ("hinglish", "Staff ka vyavhaar accha tha, reception helpful"),
    ],
    ("Staff", "neg"): [
        ("en", "The staff were rude and the manager was unhelpful"),
        ("hinglish", "Reception staff ka vyavhaar bekaar tha"),
    ],
    ("Location", "pos"): [
        ("en", "The location was great with a beautiful mountain view"),
        ("hinglish", "Mountain ka nazara shandar, location badhiya"),
    ],
    ("Location", "neg"): [
        ("en", "The location was poor and far from the market"),
        ("hinglish", "Location bekaar thi, market se door"),
    ],
    ("Value for Money", "pos"): [
        ("en", "Great value for money and worth the price"),
        ("hinglish", "Sasta aur accha, paisa vasool stay"),
    ],
    ("Value for Money", "neg"): [
        ("en", "Overpriced and too expensive for what you get"),
        ("hinglish", "Bahut mehenga tha, bilkul value nahi"),
    ],
    ("Cleanliness", "pos"): [
        ("en", "Very clean and hygienic bathroom"),
        ("hinglish", "Bathroom ekdum saaf, safai badhiya"),
    ],
    ("Cleanliness", "neg"): [
        ("en", "The bathroom was dirty and smelly, poor hygiene"),
        ("hinglish", "Bathroom ganda tha, gandagi thi"),
        ("hi", "बाथरूम गंदा था"),
    ],
    ("Booking Experience", "pos"): [
        ("en", "The check-in was quick and the booking was smooth, really good"),
        ("hinglish", "Check-in fast tha, booking process accha"),
    ],
    ("Booking Experience", "neg"): [
        ("en", "The check-in was slow and the booking was a problem"),
        ("hinglish", "Booking me check-in slow tha, bekaar process"),
    ],
}


def _baseline_matrix(rng: np.random.Generator) -> dict[str, dict[str, float]]:
    """P(positive) per (property, aspect); gives properties distinct profiles."""
    baseline: dict[str, dict[str, float]] = {}
    for prop in PROPERTIES:
        quality = rng.uniform(0.45, 0.80)
        baseline[prop] = {
            a: float(np.clip(quality + rng.uniform(-0.20, 0.20), 0.15, 0.90))
            for a in ASPECTS
        }
    return baseline


def _p_positive(prop: str, aspect: str, month: pd.Timestamp, base: float) -> float:
    """Apply injected patterns on top of the baseline probability."""
    if (
        prop == FOOD_DECLINE_PROPERTY
        and aspect == "Food"
        and month >= FOOD_DECLINE_MONTH
    ):
        return 0.10  # food complaints rise sharply
    if aspect == "Room" and month.month == 12:
        return 0.15  # market-wide December heating complaints
    return base


def _pick_sentence(
    rng: np.random.Generator, aspect: str, polarity: str
) -> tuple[str, str, int]:
    """Return (text, language, sentiment) for one aspect clause."""
    options = TEMPLATES[(aspect, polarity)]
    lang, text = options[rng.integers(len(options))]
    return text, lang, (1 if polarity == "pos" else -1)


def generate(
    seed: int = 42,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    inject_patterns: bool = True,
) -> pd.DataFrame:
    """Generate the synthetic reviews DataFrame (schema-compliant).

    ``inject_patterns=False`` produces the same mechanics with NO injected patterns
    (a "null" dataset): every detection on it is a false positive by construction,
    which is how ``cri.calibration`` measures false-alarm rates.
    ``start``/``end`` accept ``YYYY-MM`` or full ``YYYY-MM-DD`` dates (inclusive months).
    """
    rng = np.random.default_rng(seed)
    baseline = _baseline_matrix(rng)
    months = pd.period_range(start=start, end=end, freq="M").to_timestamp()
    weights = ASPECT_WEIGHTS / ASPECT_WEIGHTS.sum()

    rows: list[dict] = []
    for prop in PROPERTIES:
        for month in months:
            n_reviews = int(rng.integers(14, 22))
            # Extra heating complaints every December (market-wide burst).
            n_dec_extra = 5 if inject_patterns and month.month == 12 else 0

            for _ in range(n_reviews):
                k = int(rng.integers(1, 3))  # 1 or 2 aspects per review
                chosen = rng.choice(ASPECTS, size=k, replace=False, p=weights)
                sentences, langs, sentiments = [], [], []
                for aspect in chosen:
                    base = baseline[prop][aspect]
                    p_pos = _p_positive(prop, aspect, month, base) if inject_patterns else base
                    polarity = "pos" if rng.random() < p_pos else "neg"
                    text, lang, sent = _pick_sentence(rng, aspect, polarity)
                    sentences.append(text)
                    langs.append(lang)
                    sentiments.append(sent)
                rows.append(_make_row(rng, prop, month, sentences, langs, sentiments))

            for _ in range(n_dec_extra):
                text, lang, sent = _pick_sentence(rng, "Room", "neg")
                rows.append(_make_row(rng, prop, month, [text], [lang], [sent]))

    df = pd.DataFrame(rows)
    return df.sort_values(["date", "property_id"]).reset_index(drop=True)


def _make_row(
    rng: np.random.Generator,
    prop: str,
    month: pd.Timestamp,
    sentences: list[str],
    langs: list[str],
    sentiments: list[int],
) -> dict:
    day = int(rng.integers(1, 28))
    date = month.replace(day=day)
    mean_pol = float(np.mean(sentiments))
    jitter = int(rng.choice([-1, 0, 0, 1]))
    rating = int(np.clip(round(3 + 1.5 * mean_pol) + jitter, 1, 5))
    if "hi" in langs:
        hint = "hi"
    elif "hinglish" in langs:
        hint = "hinglish"
    else:
        hint = "en"
    return {
        "property_id": prop,
        "platform": PLATFORMS[int(rng.integers(len(PLATFORMS)))],
        "date": date.strftime("%Y-%m-%d"),
        "rating": rating,
        "text": ". ".join(sentences) + ".",
        "language_hint": hint,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate SYNTHETIC reviews.")
    parser.add_argument(
        "--out", default="data/sample/synthetic_reviews.csv", type=Path
    )
    parser.add_argument("--seed", default=42, type=int)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument(
        "--no-patterns",
        action="store_true",
        help="generate a null dataset with no injected patterns (for calibration)",
    )
    args = parser.parse_args(argv)
    if "synthetic" not in args.out.name.lower():
        # CLAUDE.md rule 2: synthetic data must say so in its filename; the loader
        # relies on this to show the SYNTHETIC banner.
        parser.error(f"--out filename must contain 'synthetic' (got {args.out.name!r})")

    df = generate(
        seed=args.seed, start=args.start, end=args.end, inject_patterns=not args.no_patterns
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(
        f"Wrote {len(df)} SYNTHETIC reviews for {df['property_id'].nunique()} "
        f"properties to {args.out}"
    )


if __name__ == "__main__":
    main()
