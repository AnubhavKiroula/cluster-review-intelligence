"""Load team-provided review files (CSV/JSON) into a validated DataFrame.

No scraping, no network access: this reads files the team places in data/raw/
(gitignored). Reviewer identity is dropped before anything else happens.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from .schema import REQUIRED_COLUMNS, SchemaError, drop_identity_columns, validate_reviews


def read_frame(path: str | Path) -> pd.DataFrame:
    """Read one CSV or JSON file as-is (no validation).

    JSON may be a list of records or a newline-delimited (``.jsonl``) file.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Review file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".json", ".jsonl"}:
        # Leave dates raw: the schema owns date parsing (epochs, offsets, local time).
        return pd.read_json(
            path, lines=(suffix == ".jsonl"), convert_dates=False, keep_default_dates=False
        )
    raise SchemaError(f"Unsupported file type '{suffix}'. Use .csv, .json, or .jsonl.")


def load_reviews(path: str | Path) -> pd.DataFrame:
    """Load one CSV or JSON file of reviews, drop PII, and validate."""
    return validate_reviews(drop_identity_columns(read_frame(path)))


def _drop_repeats_across_files(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Drop rows that already appeared in an earlier file (overlapping exports).

    Identical rows *within* one file are kept: two guests can post the same short
    review on the same day, and both are real. Rows are compared after
    concatenation, so one file storing ratings as 4 and another as 4.0 still match.
    """
    combined = pd.concat(frames, keys=range(len(frames)), names=["_file", None])
    combined = combined.reset_index(level="_file").reset_index(drop=True)
    key = [c for c in [*REQUIRED_COLUMNS, "review_id"] if c in combined.columns]
    hashes = pd.util.hash_pandas_object(combined[key], index=False).to_numpy()
    first_file = combined["_file"].groupby(hashes).transform("min")
    repeat = (combined["_file"] > first_file).to_numpy()
    if repeat.any():
        warnings.warn(
            f"Dropped {int(repeat.sum())} review(s) repeated across files "
            "(overlapping exports).",
            stacklevel=3,
        )
    return combined.loc[~repeat].drop(columns="_file").reset_index(drop=True)


def load_dir(directory: str | Path) -> pd.DataFrame:
    """Load and concatenate every CSV/JSON file in a directory.

    A review repeated in a later file is dropped with a warning (see
    ``_drop_repeats_across_files``).
    """
    directory = Path(directory)
    files = sorted(
        p for p in directory.iterdir()
        if p.suffix.lower() in {".csv", ".json", ".jsonl"}
    )
    if not files:
        raise FileNotFoundError(f"No CSV/JSON review files in {directory}")
    return _drop_repeats_across_files([load_reviews(p) for p in files])
