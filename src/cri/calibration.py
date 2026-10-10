"""Reproducible detector calibration on SYNTHETIC data.

    python -m cri.calibration --seeds 11-20

For every seed it builds two datasets with the same generator mechanics:

* injected - the real generator: Property F's food declines from 2025-06
  (property-specific) and Room dips every December in all properties (market-wide);
* null     - ``inject_patterns=False``: no patterns at all, so any finding on it is a
  false alarm by construction.

These are recovery and false-alarm rates on synthetic data, NOT accuracy on real
reviews (real-data evaluation is tracked as TBD in docs/TODO_RESULTS.md).
"""

from __future__ import annotations

import argparse
import math

import pandas as pd

from .benchmark import detect_changepoints, detect_market_patterns, market_wide_summary
from .classify import Classifier
from .generate import FOOD_DECLINE_MONTH, FOOD_DECLINE_PROPERTY, generate
from .pipeline import label_reviews

TRUE_ASPECT = "Food"
SEASONAL_ASPECT, SEASONAL_MONTH = "Room", 12


def _window(month: pd.Timestamp) -> set[str]:
    """The true change month +/- one month, as 'YYYY-MM' labels."""
    p = month.to_period("M")
    return {(p + k).strftime("%Y-%m") for k in (-1, 0, 1)}


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for a proportion k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def evaluate_seed(seed: int, classifier: Classifier | None = None) -> dict:
    """Recovery and false-alarm counts for one seed."""
    injected = label_reviews(generate(seed=seed), classifier)
    null = label_reviews(generate(seed=seed, inject_patterns=False), classifier)

    cps = detect_changepoints(injected)
    is_true = (cps["property_id"] == FOOD_DECLINE_PROPERTY) & (cps["aspect"] == TRUE_ASPECT)
    hits = cps[is_true & (cps["direction"] == "negative")]
    window = _window(FOOD_DECLINE_MONTH)
    market = detect_market_patterns(injected)
    is_room_dec = (
        (market["aspect"] == SEASONAL_ASPECT)
        & (market["kind"] == "seasonal")
        & (market["calendar_month"] == SEASONAL_MONTH)
    )
    scope = market_wide_summary(injected).set_index("aspect")["scope"]

    return {
        "seed": seed,
        "food_decline_found": bool(hits["change_month"].isin(window).any()),
        "food_decline_exact_month": bool(
            (hits["change_month"] == FOOD_DECLINE_MONTH.strftime("%Y-%m")).any()
        ),
        "food_property_specific": scope.get(TRUE_ASPECT) == "property-specific",
        "room_december_market_wide": bool(is_room_dec.any()),
        "extra_changepoints": int((~is_true).sum()),
        "extra_market_patterns": int((~is_room_dec).sum()),
        "null_changepoints": len(detect_changepoints(null)),
        "null_market_patterns": len(detect_market_patterns(null)),
    }


def calibrate(seeds, classifier: Classifier | None = None) -> tuple[pd.DataFrame, dict]:
    """Per-seed results plus a summary with Wilson intervals for the rates."""
    per_seed = pd.DataFrame([evaluate_seed(s, classifier) for s in seeds])
    n = len(per_seed)
    null_any = (per_seed["null_changepoints"] + per_seed["null_market_patterns"]) > 0

    def rate(col: str) -> dict:
        k = int(per_seed[col].sum())
        lo, hi = wilson_interval(k, n)
        return {"k": k, "n": n, "rate": k / n, "ci95": (round(lo, 2), round(hi, 2))}

    summary = {
        "food_decline_found": rate("food_decline_found"),
        "food_decline_exact_month": rate("food_decline_exact_month"),
        "food_property_specific": rate("food_property_specific"),
        "room_december_market_wide": rate("room_december_market_wide"),
        "extra_changepoints_per_seed": float(per_seed["extra_changepoints"].mean()),
        "extra_market_patterns_per_seed": float(per_seed["extra_market_patterns"].mean()),
        "null_seeds_with_any_false_alarm": {"k": int(null_any.sum()), "n": n},
        "null_false_alarms_per_seed": float(
            (per_seed["null_changepoints"] + per_seed["null_market_patterns"]).mean()
        ),
    }
    return per_seed, summary


def _parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            seeds.extend(range(lo, hi + 1))
        elif part:
            seeds.append(int(part))
    if not seeds:
        raise argparse.ArgumentTypeError("no seeds given")
    return seeds


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Calibrate the detectors on SYNTHETIC injected and null datasets."
    )
    parser.add_argument("--seeds", type=_parse_seeds, default=_parse_seeds("11-20"),
                        help="e.g. 11-20 or 1,2,5 (default 11-20)")
    args = parser.parse_args(argv)
    per_seed, summary = calibrate(args.seeds)
    print("SYNTHETIC calibration - recovery/false-alarm rates, not real-world accuracy\n")
    print(per_seed.to_string(index=False))
    print()
    for key, value in summary.items():
        if isinstance(value, dict) and "rate" in value:
            print(f"{key:34s} {value['k']}/{value['n']}  (Wilson 95% CI {value['ci95'][0]:.2f}"
                  f"-{value['ci95'][1]:.2f})")
        elif isinstance(value, dict):
            print(f"{key:34s} {value['k']}/{value['n']}")
        else:
            print(f"{key:34s} {value:.2f}")


if __name__ == "__main__":
    main()
