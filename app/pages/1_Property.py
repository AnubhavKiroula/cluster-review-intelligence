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
actions = api.priority_actions(d, prop)
if actions.empty:
    st.success("No aspect is lagging enough to flag. This property is on par with its cluster.")
else:
    top = actions.iloc[0]
    started = top["started"]
    when = f" — started around **{started}**" if started else ""
    st.markdown(f"**{top['aspect']}** is the biggest opportunity{when}. {top['rationale']}")
    show = actions[["aspect", "gap", "volume", "impact_score", "started", "basis", "rationale"]]
    st.dataframe(show, use_container_width=True, hide_index=True)
    common.download_button(actions, f"priority_actions_{prop}.csv", key="dl_actions")

st.divider()

# --- Scorecard vs cluster -----------------------------------------------------------
st.subheader("📊 Aspect scores vs the cluster")
sc = api.property_scorecard(d, prop)
if sc.empty:
    st.info("No labelled aspects for this property yet.")
else:
    err_plus = (sc["ci_high"] - sc["mean"]).fillna(0).clip(lower=0)
    err_minus = (sc["mean"] - sc["ci_low"]).fillna(0).clip(lower=0)
    bar_colours = [theme.FLAG_COLOURS.get(f, theme.MUTED) for f in sc["flag"]]

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
        "Bar colour = **lead** (teal) / **lag** (red) / **on-par** (grey), flagged only when the "
        "confidence interval supports it. Error bars are omitted for aspects with fewer than 10 "
        "reviews (no reliable CI). The navy marker is the cluster mean."
    )
    common.download_button(sc, f"scorecard_{prop}.csv", key="dl_scorecard")

st.divider()

# --- Trend + changepoint ------------------------------------------------------------
st.subheader("📈 Trend over time")
aspects = api.list_aspects()
default_aspect = str(actions.iloc[0]["aspect"]) if not actions.empty else aspects[0]
default_idx = aspects.index(default_aspect) if default_aspect in aspects else 0
aspect = st.selectbox("Aspect", aspects, index=default_idx, key="trend_aspect")

tr = api.trend(d, prop, aspect)
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
    cps = api.changepoints(d, prop, aspect)
    for _, cp in cps.iterrows():
        when = pd.Timestamp(cp["change_month"]).to_pydatetime()
        colour = theme.NEGATIVE if cp["direction"] == "negative" else theme.TEAL
        fig.add_vline(
            x=when,
            line_width=2,
            line_dash="dash",
            line_color=colour,
            annotation_text=f"{cp['direction']} shift {cp['delta']:+.2f}",
            annotation_position="top",
        )
    common.style(fig, yaxis={"title": "mean sentiment (−1…+1)", "range": [-1.05, 1.05]})
    st.plotly_chart(fig, use_container_width=True)
    if cps.empty:
        st.caption("No statistically significant changepoint detected for this series.")
    else:
        st.caption("Dashed line = a significant shift relative to the market (FDR-controlled).")
    common.download_button(tr, f"trend_{prop}_{aspect}.csv", key="dl_trend")
