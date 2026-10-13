"""Did my fix work? — a market-adjusted before/after check of one change."""

from __future__ import annotations

import common
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import theme

from cri import api

VERDICT_STYLE = {
    "improved": (st.success, "✅ Improved — relative to the market"),
    "worsened": (st.error, "⚠️ Worsened — relative to the market"),
    "no detectable change": (st.info, "➖ No detectable change relative to the market"),
    "too early to tell": (st.warning, "⏳ Too early to tell"),
    "no data": (st.warning, "Not enough reviews to check"),
}

common.configure("Did my fix work?", icon="🔧")
d = common.load_data()
prop = common.property_selector(d)

st.title(f"🔧 Did my fix work? — {prop}")
common.synthetic_banner(d)
st.markdown(
    "Pick what you changed and the **first month after the change**. A plain "
    "before/after comparison mixes your change with whatever the whole market did at "
    "the same time (season, roads, a festival); this check removes the market first."
)

lo, hi = api.date_range(d)
months = [p.strftime("%Y-%m") for p in pd.period_range(lo, hi, freq="M")][1:]
aspects = api.list_aspects()
left, right = st.columns(2)
aspect = left.selectbox("What did you change?", aspects, key="fix_aspect")
start = right.selectbox(
    "First month after the change", months, index=max(0, len(months) - 7), key="fix_start"
)

result = common.cached(api.intervention_check, d, prop, aspect, start)
show, headline = VERDICT_STYLE[result["verdict"]]
show(f"**{headline}.** {result['summary']}")

if result["effect"] is not None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Plain before → after", f"{result['naive_delta']:+.2f}")
    market = result["market_delta"]
    c2.metric("Market over same months", "—" if market is None else f"{market:+.2f}")
    c3.metric(
        "Your change vs the market",
        f"{result['effect']:+.2f}",
        help=f"95% CI {result['ci_low']:+.2f} to {result['ci_high']:+.2f}; "
        f"p = {result['p_value']:.3g}. Sentiment scale −1…+1, so changes run −2…+2.",
    )
    c4.metric(
        "Smallest detectable change",
        f"{result['mde']:.2f}",
        help="With this many reviews, a change of at least this size is detected 80% of "
        "the time. Smaller real effects can be missed.",
    )

# --- Trend with the before/after windows ----------------------------------------------
tr = common.cached(api.trend, d, prop, aspect)
if len(tr) >= 2:
    fig = go.Figure()
    base = result["baseline_start"]
    if base:
        fig.add_vrect(
            x0=pd.Timestamp(base).to_pydatetime(), x1=pd.Timestamp(start).to_pydatetime(),
            fillcolor=theme.PANEL, line_width=1, line_color=theme.GRID, layer="below",
        )
        fig.add_annotation(
            x=pd.Timestamp(base).to_pydatetime(), y=1, yref="paper", xanchor="left",
            yanchor="bottom", showarrow=False, text="before", font={"color": theme.MUTED},
        )
    fig.add_scatter(
        x=tr["month"], y=tr["mean"], mode="lines+markers",
        line={"color": theme.NAVY, "width": 2.5}, name=aspect, customdata=tr["n"],
        hovertemplate="%{x|%b %Y}<br>mean %{y:.2f} (n=%{customdata})<extra></extra>",
    )
    when = pd.Timestamp(start).to_pydatetime()
    fig.add_vline(x=when, line_width=2, line_dash="dash", line_color=theme.AMBER)
    fig.add_annotation(
        x=when, y=1, yref="paper", yanchor="bottom", showarrow=False,
        text="your change", font={"color": theme.AMBER},
    )
    common.style(fig, yaxis={"title": "mean sentiment (−1…+1)", "range": [-1.05, 1.05]})
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Shaded = the **before** window. It starts at the latest significant shift before "
        "your change (so a fix made after a decline is compared with the declined level), "
        "or at the first month of data. Dashed = your change."
    )

with st.expander("How this is decided"):
    st.markdown(
        "- **Your change vs the market** = your after − before, minus the market's change "
        "over the same months. The market is the other properties, each measured against "
        "its own usual level (the same reference as the *Property* page's shifts).\n"
        "- **Verdict**: improved / worsened when p ≤ 0.05 for this one month you chose. "
        "Choosing the month *after* looking at the chart makes the p-value too optimistic.\n"
        "- **Placebo check**: every other property goes through the same check at the "
        "same months. If several moved as much as you, be wary of the verdict.\n"
        "- **Not proof of cause**: anything else you changed in the same month is mixed "
        "in. Details: `docs/methodology.md` section 12."
    )
common.download_button(
    pd.DataFrame([result]), f"fix_check_{prop}_{aspect}_{start}.csv", key="dl_fix"
)
