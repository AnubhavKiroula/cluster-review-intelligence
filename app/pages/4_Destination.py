"""Destination view — the tourism-board aggregate: cluster-wide issues."""

from __future__ import annotations

import common
import plotly.graph_objects as go
import streamlit as st
import theme

from cri import api

common.configure("Destination", icon="🧭")
d = common.load_data()

st.title("🧭 Destination view")
common.synthetic_banner(d)
st.markdown(
    "For a tourism board, not a single hotel: where does the **whole cluster** underperform? "
    "Issues flagged **market-wide** are destination problems — worth coordinated action."
)

dest = api.destination_summary(d)
if dest.empty:
    st.info("No aspects to aggregate yet.")
    st.stop()

# --- Top cluster-wide issues --------------------------------------------------------
market_wide = dest[dest["scope"] == "market-wide"].sort_values("pct_negative", ascending=False)
st.subheader("🚩 Top cluster-wide issues")
if market_wide.empty:
    st.success(
        "No aspect is flagged market-wide — problems look property-specific, "
        "not destination-wide."
    )
else:
    worst = market_wide.iloc[0]
    st.markdown(
        f"**{worst['aspect']}** is the biggest cluster-wide issue: "
        f"{worst['pct_negative']:.0%} of its mentions are negative across "
        f"{int(worst['n_properties_reviewed'])} properties."
    )
    st.dataframe(
        market_wide[["aspect", "pct_negative", "cluster_mean", "n", "n_properties_reviewed"]],
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# --- Negative share across all aspects ----------------------------------------------
st.subheader("Negative share by aspect")
ordered = dest.sort_values("pct_negative", ascending=True)
colours = [theme.SCOPE_COLOURS.get(s, theme.MUTED) for s in ordered["scope"]]
fig = go.Figure(
    go.Bar(
        x=ordered["pct_negative"],
        y=ordered["aspect"],
        orientation="h",
        marker_color=colours,
        customdata=ordered[["scope", "n"]],
        hovertemplate=(
            "%{y}<br>negative %{x:.0%}<br>%{customdata[0]} · n=%{customdata[1]}<extra></extra>"
        ),
    )
)
common.style(
    fig,
    height=max(320, 40 + 36 * len(ordered)),
    xaxis={"title": "share of reviews negative", "tickformat": ".0%"},
    yaxis={"title": ""},
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Bar colour encodes scope: navy = market-wide, amber = property-specific, "
    "grey = undetermined, teal = stable."
)

common.download_button(dest, "destination_summary.csv", key="dl_dest")
