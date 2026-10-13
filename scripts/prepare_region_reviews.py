"""Prepare the in-region hotel reviews for sentiment training (output stays local).

Input: the Kaggle dataset "Uttarakhand hotel reviews (India)" downloaded by a team
member into data/raw/external/uttarakhand_hotel_reviews/ (Kaggle needs their own
login; this script never downloads anything). One CSV per hotel, named
``<Hotel>-<Town>_<District>_District_<State>.csv``. Despite the name it also covers
Himachal Pradesh and Ladakh.

What it does (each step is reported):
- reads only ``review`` and ``rating``: the reviewer columns (``name``,
  ``user_profile``, ``userloc``) are never loaded (CLAUDE.md rule 4);
- parses state / district / town from the file name;
- keeps hill districts only: drops Haridwar and Udham Singh Nagar, the two
  Uttarakhand districts that lie in the plains (Dehradun and Nainital are mixed and
  kept), keeps every Himachal district and Ladakh (Leh, Kargil);
- drops empty rows and repeated review texts (after normalisation) *before* any
  split, so a duplicate cannot sit on both sides of train/test;
- replaces hotel names with opaque ids (H0001...), used only for grouping.

    python scripts/prepare_region_reviews.py
    -> data/raw/external/prepared/region_reviews.csv (gitignored)
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

from cri.normalize import normalize

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/external/uttarakhand_hotel_reviews"
OUT = ROOT / "data/raw/external/prepared/region_reviews.csv"

STATES = {"Uttarakhand": "Uttarakhand", "Himachal_Pradesh": "Himachal Pradesh",
          "Ladakh_Jammu_and_Kashmir": "Ladakh", "Jammu_and_Kashmir": "Jammu and Kashmir"}
DISTRICTS = [
    # Uttarakhand
    "Almora", "Bageshwar", "Chamoli", "Champawat", "Dehradun", "Haridwar", "Nainital",
    "Pauri_Garhwal", "Pithoragarh", "Rudraprayag", "Tehri_Garhwal", "Udham_Singh_Nagar",
    "Uttarkashi",
    # Himachal Pradesh
    "Bilaspur", "Chamba", "Hamirpur", "Kangra", "Kinnaur", "Kullu", "Lahaul_and_Spiti",
    "Lahaul_Spiti", "Mandi", "Shimla", "Sirmaur", "Solan", "Una",
    # Ladakh
    "Leh", "Kargil",
]
PLAINS_DISTRICTS = {"Haridwar", "Udham Singh Nagar"}
REVIEWER_COLUMNS = ("name", "user_profile", "userloc")


def parse_name(stem: str) -> dict | None:
    """``Hotel-Town_District_District_State`` -> town, district, state (or None)."""
    _, _, place = stem.rpartition("-")
    if "_District_" not in place:
        return None
    left, _, state = place.partition("_District_")
    # Some exported file names are truncated ("..._Uttarakhan"): match a unique prefix.
    matches = [v for k, v in STATES.items()
               if k == state or (len(state) >= 4 and k.startswith(state))]
    if len(matches) != 1:
        return None
    state_name = matches[0]
    for district in sorted(DISTRICTS, key=len, reverse=True):
        if left == district or left.endswith("_" + district):
            town = left[: -len(district)].rstrip("_") or district
            return {"town": town.replace("_", " "), "district": district.replace("_", " "),
                    "state": state_name}
    return None


def stars(rating: float) -> int | None:
    """The export stores 1-5 stars as 10-50."""
    if pd.isna(rating):
        return None
    s = round(float(rating) / 10)
    return s if 1 <= s <= 5 else None


def prepare(src: Path = SRC) -> tuple[pd.DataFrame, dict]:
    files = sorted(src.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files under {src}; see docs/DATA_SOURCES.md")
    frames, unparsed = [], []
    for f in files:
        meta = parse_name(f.stem)
        if meta is None:
            unparsed.append(f.name)
            continue
        df = pd.read_csv(f, usecols=["review", "rating"])  # reviewer columns never loaded
        if df.empty:
            continue
        hotel = "H" + hashlib.sha256(f.stem.encode()).hexdigest()[:8]
        frames.append(df.assign(hotel=hotel, **meta))
    data = pd.concat(frames, ignore_index=True)
    report = {"files": len(files), "unparsed_files": len(unparsed),
              "unparsed_examples": unparsed[:5], "rows_read": len(data)}

    data = data[~data["district"].isin(PLAINS_DISTRICTS)]
    report["rows_after_hill_filter"] = len(data)
    data = data.assign(stars=data["rating"].map(stars), text=data["review"].astype("string"))
    data = data.dropna(subset=["text", "stars"])
    data = data[data["text"].str.strip().str.len() > 0]
    data["norm"] = data["text"].map(normalize)
    data = data.drop_duplicates("norm")
    report["rows_after_dedup"] = len(data)
    data["label"] = data["stars"].map(lambda s: -1 if s <= 2 else (0 if s == 3 else 1))
    report["stars"] = {int(k): int(v) for k, v in data["stars"].value_counts().sort_index().items()}
    report["by_state"] = data["state"].value_counts().to_dict()
    report["hotels"] = int(data["hotel"].nunique())
    cols = ["text", "stars", "label", "hotel", "town", "district", "state"]
    assert not set(REVIEWER_COLUMNS) & set(cols)
    return data[cols].reset_index(drop=True), report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, default=SRC)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    data, report = prepare(args.src)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.out, index=False)
    for k, v in report.items():
        print(f"{k}: {v}")
    print(f"wrote {args.out} ({len(data)} reviews)", file=sys.stderr)


if __name__ == "__main__":
    main()
