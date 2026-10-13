"""Reproducible SYNTHETIC calibration of the neighbourhood scan.

    python scripts/calibrate_neighbourhood.py            # 100 seeds per scenario
    python scripts/calibrate_neighbourhood.py --seeds 20 # quicker

Simulated 12-property clusters (tests/sim_helpers.py): one aspect, 3 reviews per
property-month (about what a hill-town property gets on Location), 2024-01..2025-12,
each property with its own baseline. Positions come from
``cri.generate.generate_locations``: either the layout with four properties inside
one 0.4 km neighbourhood, or all twelve scattered over the town. A "decline" is a
drop in P(positive) from the property's baseline to 0.15 from 2025-03. Rates are on
simulated data, not accuracy on real reviews.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from cri.calibration import wilson_interval  # noqa: E402
from cri.generate import PROPERTIES, ROAD_WORKS_PROPERTIES, generate_locations  # noqa: E402
from cri.neighbourhood import neighbourhood_findings  # noqa: E402
from sim_helpers import constant, simulate, step  # noqa: E402

NEIGHBOURS = list(ROAD_WORKS_PROPERTIES)
CHANGE = "2025-03"
AFTER = 0.15


def _spec(seed: int, declining: list[str]) -> dict:
    base = np.random.default_rng(10_000 + seed).uniform(0.45, 0.85, size=len(PROPERTIES))
    return {
        p: step(b, AFTER, CHANGE) if p in declining else constant(b)
        for p, b in zip(PROPERTIES, base, strict=True)
    }


SCENARIOS = {
    # name: (declining properties, clustered layout?, truth = "neighbourhood found")
    "nothing changed": ([], False, False),
    "4 neighbours decline (clustered)": (NEIGHBOURS, True, True),
    "the same 4 decline, scattered": (NEIGHBOURS, False, False),
    "1 property declines (in the neighbourhood)": (NEIGHBOURS[:1], True, False),
    "whole market declines": (PROPERTIES, True, False),
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--permutations", type=int, default=199)
    args = parser.parse_args(argv)
    print("SYNTHETIC calibration of the neighbourhood scan - simulated clusters, not real data")
    print(f"{args.seeds} seeds per scenario, {args.permutations} permutations per scan\n")
    for name, (declining, clustered, truth) in SCENARIOS.items():
        found = exact = 0
        for seed in range(args.seeds):
            labelled = simulate(_spec(seed, declining), aspect="Location", per_month=3, seed=seed)
            locations = generate_locations(seed=seed, neighbourhood=clustered)
            f = neighbourhood_findings(
                labelled, locations, permutations=args.permutations, seed=seed
            )
            found += bool(f)
            exact += bool(f) and set(f[0]["members"]) == set(declining)
        lo, hi = wilson_interval(found, args.seeds)
        print(f"{name}  (truth: {'neighbourhood' if truth else 'no neighbourhood'})")
        print(f"  flagged neighbourhood-wide: {found}/{args.seeds}  (95% CI {lo:.0%}-{hi:.0%})")
        if truth:
            print(f"  with exactly the 4 declining properties: {exact}/{args.seeds}")
        print()


if __name__ == "__main__":
    main()
