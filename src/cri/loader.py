"""Load team-provided review files (CSV/JSON) into a validated DataFrame.

No scraping, no network access: this reads files the team places in data/raw/
(gitignored). Reviewer identity is dropped before anything else happens.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import SchemaError, drop_identity_columns, validate_reviews


def load_reviews(path: str | Path) -> pd.DataFrame:
    """Load one CSV or JSON file of reviews, drop PII, and validate.

    JSON may be a list of records or a newline-delimited (``.jsonl``) file.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Review file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".json", ".jsonl"}:
        df = pd.read_json(path, lines=(suffix == ".jsonl"))
    else:
        raise SchemaError(f"Unsupported file type '{suffix}'. Use .csv, .json, or .jsonl.")

    df = drop_identity_columns(df)
    return validate_reviews(df)


def load_dir(directory: str | Path) -> pd.DataFrame:
    """Load and concatenate every CSV/JSON file in a directory."""
    directory = Path(directory)
    files = sorted(
        p for p in directory.iterdir()
        if p.suffix.lower() in {".csv", ".json", ".jsonl"}
    )
    if not files:
        raise FileNotFoundError(f"No CSV/JSON review files in {directory}")
    frames = [load_reviews(p) for p in files]
    return pd.concat(frames, ignore_index=True)
