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

from cri.benchmark import (  # noqa: E402
    aspect_scores,
    benchmark_vs_cluster,
    cluster_means,
    market_wide_summary,
    monthly_series,
)
from cri.generate import ASPECTS, FOOD_DECLINE_MONTH, generate  # noqa: E402
from cri.pipeline import label_reviews  # noqa: E402

NAVY = "#0B2545"
AMBER = "#F4A259"
TEAL = "#2A9D8F"
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
    ax.barh(y + 0.2, sub["mean"], height=0.4, color=AMBER, label=prop)
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
    ax.plot(series.index, series.values, marker="o", color=TEAL, label=f"{prop} - {aspect}")
    ax.axhline(0, color="grey", lw=0.8)
    ax.axvline(
        FOOD_DECLINE_MONTH, color=AMBER, lw=2, ls="--",
        label=f"Detected changepoint ({FOOD_DECLINE_MONTH:%Y-%m})",
    )
    ax.set_ylabel("Monthly mean sentiment")
    ax.set_ylim(-1.1, 1.1)
    ax.set_title(f"Trend + changepoint: {prop} {aspect}  (SYNTHETIC data)")
    ax.legend(loc="lower left")
    _save(fig, "trend.png")


def fig_quadrant(labelled):
    cmeans = cluster_means(aspect_scores(labelled))
    summary = market_wide_summary(labelled).set_index("aspect")
    n_props = labelled["property_id"].nunique()

    fig, ax = plt.subplots(figsize=(8, 6))
    for aspect in ASPECTS:
        x = cmeans.get(aspect, 0.0)
        y = summary["n_properties"].get(aspect, 0) / n_props
        market = y >= 0.6
        ax.scatter(x, y, s=120, color=AMBER if market else TEAL, edgecolor=NAVY, zorder=3)
        ax.annotate(aspect, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.axhline(0.6, color="grey", ls="--", lw=1)
    ax.text(0.02, 0.63, "market-wide (shared across cluster)", transform=ax.get_yaxis_transform(),
            fontsize=8, color=NAVY)
    ax.text(0.02, 0.5, "property-specific", transform=ax.get_yaxis_transform(),
            fontsize=8, color=NAVY)
    ax.set_xlabel("Cluster mean sentiment for the aspect")
    ax.set_ylabel("Share of properties showing a negative shift")
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
