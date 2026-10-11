"""Adapters for mapping team-provided exports onto the CRI review schema.

This module deliberately handles files, not websites. A source-specific export can
be mapped with a small configuration dictionary and then goes through the same PII
dropping and validation path as the standard loader.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loader import load_reviews
from .schema import REQUIRED_COLUMNS, SchemaError, drop_identity_columns, validate_reviews

DEFAULT_ALIASES: dict[str, tuple[str, ...]] = {
    "property_id": ("property_id", "property", "hotel_id", "hotel", "listing_id"),
    "platform": ("platform", "source", "channel", "site"),
    "date": ("date", "review_date", "created_at", "published_at"),
    "rating": ("rating", "stars", "score", "review_rating"),
    "text": ("text", "review_text", "review", "comment", "content"),
    "language_hint": ("language_hint", "language", "lang"),
}


def _normalise_name(name: object) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def map_columns(
    frame: pd.DataFrame,
    mapping: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return a schema-shaped frame from an arbitrary export.

    ``mapping`` uses canonical CRI names as keys and source column names as values,
    for example ``{"text": "review_body", "property_id": "hotel_code"}``.
    Without a mapping, conservative aliases are used. Ambiguous aliases are
    rejected instead of silently selecting a column.
    """
    source_by_normalised = {_normalise_name(column): column for column in frame.columns}
    explicit = dict(mapping or {})
    selected: dict[str, str] = {}
    missing: list[str] = []

    for canonical in REQUIRED_COLUMNS:
        if canonical in explicit:
            source = explicit[canonical]
            if source not in frame.columns:
                raise SchemaError(
                    f"Mapping for '{canonical}' refers to missing source column {source!r}."
                )
            selected[canonical] = source
            continue

        candidates = [
            source_by_normalised[_normalise_name(alias)]
            for alias in DEFAULT_ALIASES[canonical]
            if _normalise_name(alias) in source_by_normalised
        ]
        if len(candidates) > 1:
            raise SchemaError(
                f"Ambiguous source columns for '{canonical}': {candidates}. "
                "Provide an explicit mapping."
            )
        if not candidates:
            missing.append(canonical)
        else:
            selected[canonical] = candidates[0]

    if missing:
        raise SchemaError(
            f"Could not map required column(s): {missing}. "
            "Provide mapping={canonical_name: source_column}."
        )

    out = frame[[selected[column] for column in REQUIRED_COLUMNS]].copy()
    out.columns = REQUIRED_COLUMNS
    return out


def adapt_frame(
    frame: pd.DataFrame,
    mapping: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Map, drop identity columns, and validate one source export."""
    # Drop before renaming so a malicious or mistaken mapping cannot turn a PII
    # header into a harmless-looking canonical name.
    clean = drop_identity_columns(frame)
    return validate_reviews(map_columns(clean, mapping))


def load_source(
    path: str | Path,
    mapping: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Load a mapped CSV/JSON source using the standard loader checks.

    The fast path preserves the standard loader's JSONL support; mapping is
    applied to the loaded raw frame before schema validation.
    """
    if mapping is None:
        return load_reviews(path)

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix in {".json", ".jsonl"}:
        frame = pd.read_json(path, lines=suffix == ".jsonl")
    else:
        raise SchemaError(f"Unsupported file type '{suffix}'. Use .csv, .json, or .jsonl.")
    return adapt_frame(frame, mapping)
