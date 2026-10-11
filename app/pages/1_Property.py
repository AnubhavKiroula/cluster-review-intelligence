"""Property view — the scorecard, priority actions, and trend. This page is the demo."""

from __future__ import annotations

import common
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import theme

from cri import api

common.configure("Property", icon="🏨")
d = common.load_data()
prop = common.property_selector(d)

st.title(f"🏨 {prop}")
common.synthetic_banner(d)

# --- Fix this first: priority actions -----------------------------------------------
st.subheader("🎯 Fix this first")
actions = common.cached(api.priority_actions, d, prop)
if actions.empty:
    st.success(
        "Nothing is flagged for this property: no aspect significantly lags the cluster "
        "or has declined relative to the market."
    )
else:
    top = actions.iloc[0]
    started = top["started"]
    when = "" if pd.isna(started) else f" — started around **{started}**"
    st.markdown(f"**{top['aspect']}** is the biggest opportunity{when}. {top['rationale']}")
    show = actions[["aspect", "gap", "volume", "impact_score", "started", "basis", "rationale"]]
    show = show.assign(started=show["started"].map(lambda s: "—" if pd.isna(s) else s))
    st.dataframe(show, use_container_width=True, hide_index=True)
    common.download_button(actions, f"priority_actions_{prop}.csv", key="dl_actions")

st.divider()

# --- Scorecard vs cluster -----------------------------------------------------------
st.subheader("📊 Aspect scores vs the cluster")
sc = common.cached(api.property_scorecard, d, prop)
if sc.empty:
    st.info("No labelled aspects for this property yet.")
else:
    # NaN CI (too few reviews) -> no error bar and a "not tested" colour, never "on par".
    err_plus = (sc["ci_high"] - sc["mean"]).clip(lower=0)
    err_minus = (sc["mean"] - sc["ci_low"]).clip(lower=0)
    bar_colours = [
        theme.UNTESTED if pd.isna(lo) else theme.FLAG_COLOURS.get(f, theme.MUTED)
        for f, lo in zip(sc["flag"], sc["ci_low"], strict=True)
    ]

    fig = go.Figure()
    fig.add_bar(
        name=prop,
        x=sc["aspect"],
        y=sc["mean"],
        marker_color=bar_colours,
        error_y={
            "type": "data",
            "symmetric": False,
            "array": err_plus,
            "arrayminus": err_minus,
            "color": theme.INK,
            "thickness": 1.2,
        },
        hovertemplate="%{x}<br>mean %{y:.2f} (n=%{customdata})<extra></extra>",
        customdata=sc["n"],
    )
    fig.add_scatter(
        name="Cluster mean",
        x=sc["aspect"],
        y=sc["cluster_mean"],
        mode="markers",
        marker={"symbol": "line-ew", "size": 28, "line": {"width": 3, "color": theme.NAVY}},
        hovertemplate="%{x}<br>cluster %{y:.2f}<extra></extra>",
    )
    common.style(fig, yaxis={"title": "mean sentiment (−1…+1)", "range": [-1.05, 1.05]})
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Bar colour = **lead** (teal) / **lag** (red) / **on par** (grey): lead/lag only when "
        "the gap is significant across the cluster and the 95% interval excludes the cluster "
        f"mean. **Light grey** = fewer than {api.MIN_REVIEWS_FOR_FLAG} reviews: not tested, no "
        "error bar. The navy marker is the cluster mean."
    )
    common.download_button(sc, f"scorecard_{prop}.csv", key="dl_scorecard")

st.divider()

# --- Trend + changepoint ------------------------------------------------------------
st.subheader("📈 Trend over time")
aspects = api.list_aspects()
default_aspect = str(actions.iloc[0]["aspect"]) if not actions.empty else aspects[0]
default_idx = aspects.index(default_aspect) if default_aspect in aspects else 0
aspect = st.selectbox("Aspect", aspects, index=default_idx, key="trend_aspect")

tr = common.cached(api.trend, d, prop, aspect)
if tr.empty or len(tr) < 2:
    st.info(f"Not enough monthly data to plot a trend for **{aspect}** at this property.")
else:
    fig = go.Figure()
    fig.add_scatter(
        x=tr["month"],
        y=tr["mean"],
        mode="lines+markers",
        line={"color": theme.NAVY, "width": 2.5},
        hovertemplate="%{x|%b %Y}<br>mean %{y:.2f} (n=%{customdata})<extra></extra>",
        customdata=tr["n"],
        name=aspect,
    )
    cps = common.cached(api.changepoints, d, prop, aspect)
    for _, cp in cps.iterrows():
        when = pd.Timestamp(cp["change_month"]).to_pydatetime()
        colour = theme.NEGATIVE if cp["direction"] == "negative" else theme.TEAL
        # Label via add_annotation: plotly 5.x add_vline(annotation_text=...) raises on
        # a datetime x (it averages the line's x values).
        fig.add_vline(x=when, line_width=2, line_dash="dash", line_color=colour)
        fig.add_annotation(
            x=when, y=1, yref="paper", yanchor="bottom", showarrow=False,
            text=f"{cp['direction']} shift {cp['delta']:+.2f}", font={"color": colour},
        )
    common.style(fig, yaxis={"title": "mean sentiment (−1…+1)", "range": [-1.05, 1.05]})
    st.plotly_chart(fig, use_container_width=True)
    if cps.empty:
        st.caption("No statistically significant changepoint detected for this series.")
    elif cps["market_delta"].notna().all():
        st.caption(
            "Dashed line = a significant shift **relative to the market** (the other "
            "properties' trend is removed first; FDR-controlled)."
        )
    else:
        st.caption(
            "Dashed line = a significant shift **in this property's own history**: too few "
            "properties review this aspect to compare with the market (FDR-controlled)."
        )
    common.download_button(tr, f"trend_{prop}_{aspect}.csv", key="dl_trend")
