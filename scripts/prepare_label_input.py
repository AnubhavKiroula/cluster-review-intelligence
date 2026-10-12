"""Create a PII-free annotation frame from a team-provided review export."""

from __future__ import annotations

import argparse
from pathlib import Path

from cri.sources import load_source


def prepare_input(
    source: str | Path,
    output: str | Path,
    *,
    mapping_file: str | Path | None = None,
) -> None:
    """Validate a source export and write the blank human-label template."""
    reviews = load_source(source, mapping_file=mapping_file)
    labels = reviews.assign(
        review_id=range(len(reviews)),
        gold_aspects="",
        gold_sentiment_per_aspect="",
        notes="",
    )[
        [
            "review_id",
            "property_id",
            "date",
            "text",
            "language_hint",
            "gold_aspects",
            "gold_sentiment_per_aspect",
            "notes",
        ]
    ]
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(destination, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a validated, PII-free CSV for human labelling."
    )
    parser.add_argument("source", type=Path, help="Team-provided CSV/JSON export")
    parser.add_argument("output", type=Path, help="Output CSV for the annotation workflow")
    parser.add_argument("--mapping-file", type=Path, help="Optional canonical-to-source YAML map")
    args = parser.parse_args(argv)
    prepare_input(args.source, args.output, mapping_file=args.mapping_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
