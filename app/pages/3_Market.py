"""Market view — the differentiator: market-wide vs property-specific issues."""

from __future__ import annotations

import common
import plotly.graph_objects as go
import streamlit as st
import theme

from cri import api

common.configure("Market", icon="⚖️")
d = common.load_data()

st.title("⚖️ Market-wide vs property-specific")
common.synthetic_banner(d)
st.markdown(
    "The same low score means two different things. A **property-specific** gap is one a "
    "hotel owns and can win on. A **market-wide** issue hits most of the cluster — it's a "
    "destination problem, not a hotel one. *Same chart, two completely different actions.*"
)

scope = common.cached(api.market_scope, d)
if scope.empty:
    st.info("No aspects show a negative shift to classify yet.")
    st.stop()

# Severity (how negative) comes from the destination aggregate; breadth from market_scope.
dest = common.cached(api.destination_summary, d)[["aspect", "pct_negative"]]
plot = scope.merge(dest, on="aspect", how="left")
plot["pct_negative"] = plot["pct_negative"].fillna(0.0)

avg_neg = float(plot["pct_negative"].mean())

fig = go.Figure()
for scope_name, group in plot.groupby("scope"):
    fig.add_scatter(
        x=group["fraction"],
        y=group["pct_negative"],
        mode="markers+text",
        text=group["aspect"],
        textposition="top center",
        name=str(scope_name),
        marker={
            "size": 16,
            "color": theme.SCOPE_COLOURS.get(str(scope_name), theme.MUTED),
            "line": {"width": 1, "color": theme.PAPER},
        },
        customdata=group[["n_properties", "scope"]],
        hovertemplate=(
            "%{text}<br>share of properties affected %{x:.0%}"
            "<br>mentions negative %{y:.0%}"
            "<br>%{customdata[1]} · n_properties=%{customdata[0]}<extra></extra>"
        ),
    )

# Guides: the API's market-wide threshold (vertical) and the average negative share
# of the aspects shown (horizontal). Explicit widths: the simple_white template's
# shape default is width 0, which drew both guides invisibly.
guide = {"line_dash": "dot", "line_color": theme.MUTED, "line_width": 1.5}
fig.add_vline(x=api.MARKET_WIDE_FRACTION, **guide)
fig.add_hline(y=avg_neg, **guide)
fig.add_annotation(
    x=api.MARKET_WIDE_FRACTION, y=0, xref="x", yref="paper", xanchor="left",
    yanchor="bottom", showarrow=False, text=" market-wide threshold →",
    font={"color": theme.MUTED, "size": 12},
)
common.style(
    fig,
    height=520,
    xaxis={"title": "share of properties affected", "tickformat": ".0%", "range": [-0.05, 1.05]},
    yaxis={"title": "share of mentions negative", "tickformat": ".0%"},
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Colour = scope, decided by statistical tests across properties (see the table), not by "
    f"position. Vertical dotted line: the market-wide threshold ({api.MARKET_WIDE_FRACTION:.0%} "
    "of the properties reviewing the aspect share the pattern). Horizontal: the average "
    "negative share of the aspects shown. `undetermined` = too few properties review the "
    "aspect to tell."
)

st.subheader("Scope by aspect")
table = scope[["aspect", "scope", "fraction", "n_properties", "pattern"]]
st.dataframe(table, use_container_width=True, hide_index=True)
common.download_button(scope, "market_scope.csv", key="dl_scope")
