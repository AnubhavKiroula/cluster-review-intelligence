"""Reproducible SYNTHETIC calibration of the "Did my fix work?" check.

    python scripts/calibrate_intervention.py

Simulated 6-property clusters (tests/sim_helpers.py, 15 reviews per property-month,
2024-01..2025-12, change month 2025-06). For each scenario it counts verdicts of the
market-adjusted check and of a NAIVE check (the same test on the property's own
reviews only, i.e. a plain before/after). These are rates on simulated data, not
accuracy on real reviews.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from cri.calibration import wilson_interval  # noqa: E402
from cri.intervention import evaluate_intervention  # noqa: E402
from sim_helpers import constant, simulate, step  # noqa: E402

OTHERS = [f"P{i}" for i in range(1, 6)]


def _dip_then_fix(month: pd.Timestamp) -> float:
    if month < pd.Timestamp("2025-01"):
        return 0.7
    return 0.2 if month < pd.Timestamp("2025-06") else 0.7


SCENARIOS = {
    # name: (target, others, truth, seeds)
    "nothing changed": (constant(0.6), constant(0.6), "no detectable change", range(100)),
    "whole market improved": (
        step(0.4, 0.7, "2025-06"), step(0.4, 0.7, "2025-06"), "no detectable change", range(100)
    ),
    "real fix (+1.0)": (step(0.3, 0.8, "2025-06"), constant(0.6), "improved", range(50)),
    "small fix (+0.2)": (step(0.5, 0.6, "2025-06"), constant(0.6), "improved", range(50)),
    "fix after a decline": (_dip_then_fix, constant(0.6), "improved", range(50)),
}


def main() -> None:
    print("SYNTHETIC calibration of intervention_check - simulated clusters, not real data\n")
    for name, (target, other, truth, seeds) in SCENARIOS.items():
        adjusted, naive, baselines = Counter(), Counter(), Counter()
        for seed in seeds:
            labelled = simulate({"P0": target, **dict.fromkeys(OTHERS, other)}, seed=seed)
            r = evaluate_intervention(labelled, "P0", "Food", "2025-06")
            adjusted[r["verdict"]] += 1
            baselines[r["baseline_start"]] += 1
            own = labelled[labelled["property_id"] == "P0"]
            naive[evaluate_intervention(own, "P0", "Food", "2025-06")["verdict"]] += 1
        n = len(seeds)
        k = adjusted[truth]
        lo, hi = wilson_interval(k, n)
        print(f"{name}  (truth: {truth})")
        print(f"  market-adjusted: {k}/{n} correct (Wilson 95% CI {lo:.2f}-{hi:.2f}); "
              f"{dict(adjusted)}")
        print(f"  naive:           {naive[truth]}/{n} correct; {dict(naive)}")
        if name == "fix after a decline":
            print(f"  baseline_start:  {dict(baselines)}")
        print()


if __name__ == "__main__":
    main()
