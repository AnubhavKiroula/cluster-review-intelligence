"""Visual theme for the dashboard: the project palette and a Plotly layout.

Palette is from docs/HACKATHON_PLAN.md section 4 (navy / amber / teal), kept in one
place so every page and chart reads as one product. This module has no third-party
imports on purpose, so it stays trivially importable from the smoke test.
"""

from __future__ import annotations

# --- Brand palette ------------------------------------------------------------------
NAVY = "#0B2545"
AMBER = "#F4A259"
TEAL = "#2A9D8F"
INK = "#13293D"
MUTED = "#5B6B7B"
PAPER = "#FFFFFF"
PANEL = "#F2F5F8"
GRID = "#E6EBF0"

# --- Semantic colours ---------------------------------------------------------------
# Sentiment runs -1..+1, so charts centre on zero.
NEGATIVE = "#C1443C"
NEUTRAL = "#E9C46A"
POSITIVE = TEAL

# Scorecard lead/lag flags.
LEAD = TEAL
LAG = NEGATIVE
ON_PAR = MUTED

UNTESTED = "#C9D1D9"  # fewer reviews than the API needs to test lead/lag

FLAG_COLOURS = {"lead": LEAD, "lag": LAG, "on_par": ON_PAR}

# Market-scope categories.
SCOPE_COLOURS = {
    "market-wide": NAVY,
    "property-specific": AMBER,
    "undetermined": MUTED,
    "stable": TEAL,
}

# Diverging scale for the -1..+1 sentiment heatmap.
DIVERGING = [[0.0, NEGATIVE], [0.5, "#F4F6F8"], [1.0, POSITIVE]]


def plotly_layout(**overrides) -> dict:
    """Shared Plotly layout. Pass keyword overrides for per-chart tweaks."""
    layout = {
        "template": "simple_white",
        "font": {"family": "Inter, Segoe UI, sans-serif", "color": INK, "size": 14},
        "colorway": [NAVY, AMBER, TEAL, NEGATIVE, MUTED],
        "margin": {"l": 64, "r": 24, "t": 56, "b": 48},
        "paper_bgcolor": PAPER,
        "plot_bgcolor": PAPER,
        "hoverlabel": {"font_size": 13},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    }
    layout.update(overrides)
    return layout
