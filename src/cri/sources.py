"""Adapters for mapping team-provided exports onto the CRI review schema.

This module deliberately handles files, not websites. A source-specific export can
be mapped with a small configuration dictionary and then goes through the same PII
dropping and validation path as the standard loader.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from .loader import read_frame
from .schema import REQUIRED_COLUMNS, SchemaError, drop_identity_columns, validate_reviews

DEFAULT_ALIASES: dict[str, tuple[str, ...]] = {
    "property_id": ("property_id", "property", "hotel_id", "hotel", "listing_id"),
    "platform": ("platform", "source", "channel", "site"),
    "date": ("date", "review_date", "created_at", "published_at"),
    "rating": ("rating", "stars", "score", "review_rating"),
    "text": ("text", "review_text", "review", "comment", "content"),
    "language_hint": ("language_hint", "language", "lang"),
}
# Optional column carried through when present (eval labels join on it).
OPTIONAL_COLUMNS = ["review_id"]


def _normalise_name(name: object) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def check_mapping(mapping: object) -> dict[str, str]:
    """Validate a canonical-to-source column mapping (dict or YAML ``columns``)."""
    if not isinstance(mapping, dict):
        raise SchemaError("A column mapping must be a {canonical_name: source_column} dict.")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise SchemaError("Column mapping keys and values must all be strings.")
    unknown = sorted(set(mapping) - set(REQUIRED_COLUMNS) - set(OPTIONAL_COLUMNS))
    if unknown:
        raise SchemaError(f"Mapping contains unknown canonical column(s): {unknown}.")
    reused = sorted({v for v in mapping.values() if list(mapping.values()).count(v) > 1})
    if reused:
        raise SchemaError(f"Source column(s) {reused} are mapped to more than one field.")
    return dict(mapping)


def map_columns(
    frame: pd.DataFrame,
    mapping: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return a schema-shaped frame from an arbitrary export.

    ``mapping`` uses canonical CRI names as keys and source column names as values,
    for example ``{"text": "review_body", "property_id": "hotel_code"}``. Every other
    field resolves, in order, to: the canonical header itself (any case/spacing),
    then a conservative alias. A source column is used at most once, and two
    candidates for one field are rejected instead of silently picking one. A
    ``review_id`` column is carried through when present.
    """
    explicit = check_mapping(mapping or {})
    missing_source = [v for v in explicit.values() if v not in frame.columns]
    if missing_source:
        raise SchemaError(f"Mapping refers to missing source column(s) {missing_source}.")
    used = set(explicit.values())
    by_normalised: dict[str, list[str]] = {}
    for column in frame.columns:
        by_normalised.setdefault(_normalise_name(column), []).append(column)

    def free(names) -> list[str]:
        found = [c for n in names for c in by_normalised.get(_normalise_name(n), [])]
        return [c for c in dict.fromkeys(found) if c not in used]

    selected: dict[str, str] = {}
    missing: list[str] = []
    for canonical in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
        if canonical in explicit:
            selected[canonical] = explicit[canonical]
            continue
        candidates = free([canonical])
        if not candidates and canonical in DEFAULT_ALIASES:
            candidates = free(DEFAULT_ALIASES[canonical])
        if len(candidates) > 1:
            raise SchemaError(
                f"Ambiguous source columns for '{canonical}': {candidates}. "
                "Provide an explicit mapping."
            )
        if candidates:
            selected[canonical] = candidates[0]
            used.add(candidates[0])
        elif canonical in REQUIRED_COLUMNS:
            missing.append(canonical)

    if missing:
        raise SchemaError(
            f"Could not map required column(s): {missing}. "
            "Provide mapping={canonical_name: source_column}."
        )

    out = frame[list(selected.values())].copy()
    out.columns = list(selected)
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
    mapping_file: str | Path | None = None,
) -> pd.DataFrame:
    """Load a CSV/JSON(L) export, map its columns, drop PII, and validate.

    Without ``mapping``/``mapping_file`` the documented aliases are used (a file
    already in the standard schema loads unchanged).
    """
    if mapping is not None and mapping_file is not None:
        raise ValueError("Pass either mapping or mapping_file, not both.")
    if mapping_file is not None:
        mapping = load_mapping(mapping_file)
    return adapt_frame(read_frame(path), mapping)


def load_mapping(path: str | Path) -> dict[str, str]:
    """Load a canonical-to-source column mapping from a small YAML config."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Mapping file not found: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("columns"), dict):
        raise SchemaError("Mapping YAML must contain a 'columns' mapping.")
    return check_mapping(raw["columns"])
