"""Create deterministic, disjoint labelling slices from a supplied CSV."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


def split_frame(frame: pd.DataFrame, annotators: list[str]) -> dict[str, pd.DataFrame]:
    """Assign each review to exactly one annotator using a stable hash."""
    if not annotators:
        raise ValueError("At least one annotator is required")
    if "review_id" not in frame.columns:
        raise ValueError("Input must contain review_id")
    if frame["review_id"].isna().any() or frame["review_id"].duplicated().any():
        raise ValueError("review_id must be non-empty and unique")
    buckets = [
        int(hashlib.sha256(str(review_id).encode("utf-8")).hexdigest(), 16) % len(annotators)
        for review_id in frame["review_id"]
    ]
    return {
        annotator: frame.loc[[bucket == index for bucket in buckets]].reset_index(drop=True)
        for index, annotator in enumerate(annotators)
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Split reviews into disjoint labelling slices")
    parser.add_argument("input", type=Path, help="CSV containing review_id and review fields")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--annotators", nargs="+", default=["A", "P", "R"])
    args = parser.parse_args(argv)
    slices = split_frame(pd.read_csv(args.input), args.annotators)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for annotator, frame in slices.items():
        frame.to_csv(args.output_dir / f"slice_{annotator}.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
