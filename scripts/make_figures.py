"""Reproducibly render the four README figures from the SYNTHETIC data.

Run: ``python scripts/make_figures.py`` -> writes PNGs into docs/img/.
Every figure is labelled SYNTHETIC. No real data, no network access.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from cri.benchmark import (  # noqa: E402
    MARKET_WIDE_FRACTION,
    aspect_scores,
    benchmark_vs_cluster,
    cluster_means,
    detect_changepoints,
    market_wide_summary,
    monthly_series,
)
from cri.generate import ASPECTS, FOOD_DECLINE_MONTH, generate  # noqa: E402
from cri.pipeline import label_reviews  # noqa: E402

NAVY = "#0B2545"
AMBER = "#F4A259"
TEAL = "#2A9D8F"
GREY = "#9AA5B1"
OUT = Path("docs/img")

plt.rcParams.update(
    {
        "figure.dpi": 120,
        "font.size": 10,
        "axes.edgecolor": NAVY,
        "axes.labelcolor": NAVY,
        "text.color": NAVY,
        "xtick.color": NAVY,
        "ytick.color": NAVY,
        "axes.titleweight": "bold",
    }
)


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT / name}")


def fig_benchmark(labelled, prop="Property F"):
    bench = benchmark_vs_cluster(labelled)
    sub = bench[bench["property_id"] == prop].set_index("aspect").reindex(ASPECTS)
    y = np.arange(len(ASPECTS))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(y - 0.2, sub["cluster_mean"], height=0.4, color=NAVY, label="Cluster mean")
    err = np.vstack([sub["mean"] - sub["ci_low"], sub["ci_high"] - sub["mean"]]).clip(min=0)
    ax.barh(y + 0.2, sub["mean"], height=0.4, color=AMBER, label=f"{prop} (95% CI)",
            xerr=err, error_kw={"ecolor": NAVY, "capsize": 3, "lw": 1})
    ax.set_yticks(y)
    ax.set_yticklabels(ASPECTS)
    ax.axvline(0, color="grey", lw=0.8)
    ax.set_xlabel("Mean sentiment (-1 = negative, +1 = positive)")
    ax.set_title(f"Aspect benchmark: {prop} vs cluster  (SYNTHETIC data)")
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    _save(fig, "benchmark.png")


def fig_heatmap(labelled):
    scores = aspect_scores(labelled)
    pivot = scores.pivot(index="property_id", columns="aspect", values="mean")
    pivot = pivot.reindex(columns=ASPECTS)
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(ASPECTS)))
    ax.set_xticklabels(ASPECTS, rotation=40, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{pivot.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("Cluster heatmap: mean sentiment by property x aspect  (SYNTHETIC data)")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Mean sentiment")
    _save(fig, "heatmap.png")


def fig_trend(labelled, prop="Property F", aspect="Food"):
    series = monthly_series(labelled, prop, aspect)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(series.index, series.to_numpy(), marker="o", color=TEAL, label=f"{prop} - {aspect}")
    ax.axhline(0, color="grey", lw=0.8)
    # Ground truth is drawn separately and labelled as such; the marker below is
    # what the detector actually found (or a note when it found nothing).
    ax.axvline(FOOD_DECLINE_MONTH, color=GREY, lw=1, ls=":",
               label=f"Injected change ({FOOD_DECLINE_MONTH:%Y-%m}, SYNTHETIC ground truth)")
    cps = detect_changepoints(labelled)
    found = cps[(cps["property_id"] == prop) & (cps["aspect"] == aspect)]
    if found.empty:
        ax.text(0.99, 0.95, "No significant changepoint detected", transform=ax.transAxes,
                ha="right", va="top", fontsize=9, color=NAVY)
    else:
        row = found.iloc[0]
        ax.axvline(pd.Timestamp(f"{row['change_month']}-01"), color=AMBER, lw=2, ls="--",
                   label=f"Detected changepoint ({row['change_month']}, q={row['q_value']:.1g})")
    ax.set_ylabel("Monthly mean sentiment")
    ax.set_ylim(-1.1, 1.1)
    ax.set_title(f"Trend + changepoint: {prop} {aspect}  (SYNTHETIC data)")
    ax.legend(loc="lower left")
    _save(fig, "trend.png")


def fig_quadrant(labelled):
    cmeans = cluster_means(aspect_scores(labelled))
    summary = market_wide_summary(labelled).set_index("aspect")

    # Colour comes from the statistically tested scope, not from the y position.
    colours = {"market-wide": AMBER, "property-specific": TEAL, "undetermined": GREY}
    fig, ax = plt.subplots(figsize=(8, 6))
    points = sorted(
        (float(cmeans.get(a, 0.0)), float(summary["fraction"].get(a, 0.0)), a) for a in ASPECTS
    )
    placed: list[tuple[float, float]] = []
    for x, y, aspect in points:
        scope = summary["scope"].get(aspect, "stable")
        ax.scatter(x, y, s=120, color=colours.get(scope, "white"), edgecolor=NAVY, zorder=3)
        # Stagger labels of points that sit close together so they stay readable.
        crowd = sum(1 for px, py in placed if abs(px - x) < 0.06 and abs(py - y) < 0.05)
        placed.append((x, y))
        ax.annotate(aspect, (x, y), textcoords="offset points", fontsize=8,
                    xytext=(6, 6 + 13 * crowd), ha="left",
                    arrowprops={"arrowstyle": "-", "color": GREY, "lw": 0.6} if crowd else None)
    ax.axhline(MARKET_WIDE_FRACTION, color="grey", ls="--", lw=1)
    ax.text(0.02, MARKET_WIDE_FRACTION + 0.03,
            "market-wide needs >= 60% sharing a significant pattern",
            transform=ax.get_yaxis_transform(), fontsize=8, color=NAVY)
    for label, colour in [*colours.items(), ("stable (no significant shift)", "white")]:
        ax.scatter([], [], s=80, color=colour, edgecolor=NAVY, label=label)
    ax.legend(loc="center right", fontsize=8, frameon=False)
    ax.set_xlabel("Cluster mean sentiment for the aspect")
    ax.set_ylabel("Share of properties affected by a significant negative shift")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Market-wide vs property-specific  (SYNTHETIC data)")
    _save(fig, "quadrant.png")


def main() -> None:
    labelled = label_reviews(generate(seed=42))
    fig_benchmark(labelled)
    fig_heatmap(labelled)
    fig_trend(labelled)
    fig_quadrant(labelled)
    print("All figures regenerated from SYNTHETIC data.")


if __name__ == "__main__":
    main()
