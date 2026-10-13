"""Build one REAL cluster (a hill town's hotels) in the review schema (output stays local).

Input: the Kaggle hill-hotel reviews prepared by ``scripts/prepare_region_reviews.py``
(same filters: hill districts, de-duplicated text, reviewer columns never loaded).

Output, schema-conforming and **without a ``date`` column** (the source has no review
dates; none are invented):

- ``property_id``: an anonymised, stable id (``Property A``...), assigned in the order
  of an opaque hash of the hotel's file name. CLAUDE.md rule 4: real properties are
  anonymised in anything public;
- ``platform``: ``tripadvisor``, *inferred* (the corpus is TripAdvisor-derived, see
  docs/DATA_SOURCES.md; the source does not state it per review);
- ``rating``: 1-5 stars (the export stores 10-50);
- ``text``: the review; ``language_hint``: detected by ``cri.normalize``.

A hotel joins the cluster with at least ``--min-reviews`` reviews (default
2 x ``MIN_REVIEWS_FOR_FLAG`` = 20): the cluster average weighs every property equally,
so a hotel with a handful of reviews would add noise without ever being testable.

Also writes a LOCAL-ONLY map (``Property A`` -> hotel name) so the team can answer
"which hotel is B?". Both files live under the gitignored ``data/raw/external/``;
never commit them.

    python scripts/prepare_real_cluster.py --town Kausani
"""

from __future__ import annotations

import argparse
import hashlib
import string
import sys
from itertools import count, islice, product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cri.benchmark import MIN_REVIEWS_FOR_FLAG  # noqa: E402
from cri.normalize import detect_language  # noqa: E402
from prepare_region_reviews import SRC, parse_name, prepare  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "data/raw/external/prepared"


def _letters(n: int) -> list[str]:
    """A..Z, then AA, AB, ... so any cluster size gets stable short ids."""
    ids = ("".join(p) for k in count(1) for p in product(string.ascii_uppercase, repeat=k))
    return list(islice(ids, n))


def hotel_names(src: Path, town: str) -> dict[str, str]:
    """Opaque hotel id (as in prepare_region_reviews) -> hotel name, for one town."""
    names = {}
    for f in sorted(src.rglob("*.csv")):
        meta = parse_name(f.stem)
        if meta and meta["town"] == town:
            names["H" + hashlib.sha256(f.stem.encode()).hexdigest()[:8]] = \
                f.stem.rpartition("-")[0].replace("_", " ")
    return names


def build(town: str, min_reviews: int, src: Path = SRC) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    data, _ = prepare(src)
    data = data[data["town"] == town]
    if data.empty:
        raise SystemExit(f"No reviews for town {town!r}.")
    per_hotel = data.groupby("hotel").size()
    kept = sorted(per_hotel[per_hotel >= min_reviews].index)  # opaque-hash order
    ids = dict(zip(kept, (f"Property {s}" for s in _letters(len(kept))), strict=True))
    data = data[data["hotel"].isin(kept)]
    reviews = pd.DataFrame({
        "property_id": data["hotel"].map(ids),
        "platform": "tripadvisor",
        "rating": data["stars"].astype(int),
        "text": data["text"],
        "language_hint": data["text"].map(detect_language),
    }).reset_index(drop=True)
    names = hotel_names(src, town)
    mapping = pd.DataFrame({"property_id": list(ids.values()),
                            "hotel": [names.get(h, "?") for h in ids],
                            "reviews": [int(per_hotel[h]) for h in ids]})
    report = {
        "town": town, "district": data["district"].iloc[0], "state": data["state"].iloc[0],
        "hotels_in_town": int(per_hotel.size), "reviews_in_town": int(per_hotel.sum()),
        "min_reviews": min_reviews, "hotels_kept": len(kept), "reviews_kept": len(reviews),
        "language_hint": reviews["language_hint"].value_counts().to_dict(),
    }
    return reviews, mapping, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--town", default="Kausani")
    parser.add_argument("--min-reviews", type=int, default=2 * MIN_REVIEWS_FOR_FLAG)
    parser.add_argument("--src", type=Path, default=SRC)
    args = parser.parse_args()
    reviews, mapping, report = build(args.town, args.min_reviews, args.src)
    slug = args.town.lower().replace(" ", "_")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out, map_out = OUT_DIR / f"real_cluster_{slug}.csv", OUT_DIR / f"real_cluster_{slug}_MAP.csv"
    assert "date" not in reviews.columns and not {"name", "user_profile", "userloc"} & set(
        reviews.columns)
    reviews.to_csv(out, index=False)
    mapping.to_csv(map_out, index=False)
    for k, v in report.items():
        print(f"{k}: {v}")
    print(f"wrote {out} and the local-only map {map_out.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
