"""Shared dashboard helpers: data loading, sidebar controls, banner, chart styling.

The dashboard consumes ONLY ``cri.api`` (the frozen contract in
docs/HACKATHON_PLAN.md section 3.2) plus this module. No other ``cri`` internals are
imported anywhere under ``app/``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import theme

from cri import api

SYNTHETIC = "SYNTHETIC sample"
RAW = "Local data/raw"


def configure(title: str, icon: str = "📊") -> None:
    """``st.set_page_config`` with a consistent title/layout. Call first on every page."""
    st.set_page_config(
        page_title=f"{title} · Cluster Review Intelligence",
        page_icon=icon,
        layout="wide",
    )


@st.cache_data(show_spinner="Loading and labelling reviews…")
def _load(source: str) -> api.ClusterData:
    # Cached on the source string so switching data sources is instant on re-select.
    if source == RAW:
        return api.load_cluster(synthetic=False)
    return api.load_cluster(synthetic=True)


def load_data() -> api.ClusterData:
    """Sidebar data-source selector + cached load, with graceful error handling."""
    source = st.sidebar.radio("Data source", [SYNTHETIC, RAW], index=0, key="data_source")
    try:
        return _load(source)
    except Exception as exc:  # noqa: BLE001 - surface any loader error to the user, not a trace
        st.sidebar.error(f"Could not load **{source}**.")
        st.error(
            f"Failed to load data from **{source}**: {exc}\n\n"
            "If you selected *Local data/raw*, add schema-conforming CSV/JSON files to "
            "`data/raw/` (see `docs/data_schema.md`), or switch back to the SYNTHETIC sample."
        )
        st.stop()


def synthetic_banner(d: api.ClusterData) -> None:
    """Prominent banner required by CLAUDE.md rule 2 whenever data is synthetic."""
    if d.is_synthetic:
        st.warning(
            f"🧪 **SYNTHETIC DATA** — {d.source_name}. "
            "Figures below describe generated reviews, not real properties.",
            icon="🧪",
        )
    else:
        st.caption(f"Source: {d.source_name}")


def property_selector(d: api.ClusterData, *, key: str = "property") -> str:
    """Sidebar property picker. Returns the selected ``property_id``."""
    return st.sidebar.selectbox("Property", api.list_properties(d), key=key)


def date_bounds(d: api.ClusterData, *, key: str = "dates") -> tuple[pd.Timestamp, pd.Timestamp]:
    """Sidebar date-range slider. Returns inclusive (start, end) timestamps."""
    lo, hi = api.date_range(d)
    lo_d, hi_d = lo.date(), hi.date()
    if lo_d == hi_d:
        return lo, hi
    start, end = st.sidebar.slider(
        "Date range", min_value=lo_d, max_value=hi_d, value=(lo_d, hi_d), key=key
    )
    return pd.Timestamp(start), pd.Timestamp(end)


def style(fig: go.Figure, **overrides) -> go.Figure:
    """Apply the shared Plotly layout to a figure."""
    fig.update_layout(**theme.plotly_layout(**overrides))
    return fig


def download_button(
    df: pd.DataFrame, filename: str, *, key: str, label: str = "Download CSV"
) -> None:
    """A per-table CSV export button."""
    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


SENTIMENT_LABELS = {1: "👍 positive", 0: "😐 neutral", -1: "👎 negative"}


def sentiment_label(value) -> str:
    """Map a -1/0/1 sentiment (or NA) to a readable label for the explorer."""
    if pd.isna(value):
        return "— none detected"
    return SENTIMENT_LABELS.get(int(value), str(value))
