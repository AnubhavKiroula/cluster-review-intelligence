"""Cluster Review Intelligence — dashboard entry point.

Run with:  streamlit run app/Home.py
"""

from __future__ import annotations

import common
import streamlit as st

from cri import api

common.configure("Home", icon="🏔️")
d = common.load_data()

st.title("🏔️ Cluster Review Intelligence")
st.markdown(
    "#### *“Am I behind my cluster, since when, and is it just me or the whole market?”*"
)
common.synthetic_banner(d)

st.markdown(
    "The **same star average** means different things for different hotels. One property's "
    "weak spot is a competitive gap it owns; another's is a problem the *entire cluster* "
    "shares every winter. This dashboard separates the two — and tells you what to fix first."
)

# --- Cluster at a glance -------------------------------------------------------------
properties = api.list_properties(d)
aspects = api.list_aspects()
lo, hi = api.date_range(d)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Properties", len(properties))
c2.metric("Reviews", f"{len(d.reviews):,}")
c3.metric("Aspects tracked", len(aspects))
c4.metric("Date range", f"{lo:%b %Y} – {hi:%b %Y}")

st.divider()

# --- Navigation guide ---------------------------------------------------------------
st.subheader("Where to go")
left, right = st.columns(2)
with left:
    st.markdown(
        "- **🏨 Property** — your scorecard vs the cluster, trends, and *fix-this-first* actions.\n"
        "- **🗺️ Cluster** — the property × aspect heatmap: who leads, who lags.\n"
        "- **⚖️ Market** — the differentiator: market-wide vs property-specific issues."
    )
with right:
    st.markdown(
        "- **🧭 Destination** — the tourism-board view of cluster-wide problems.\n"
        "- **🔍 Explorer** — search reviews; see the exact clause each label came from.\n"
        "- **🔧 Did my fix work?** — did your change help, *relative to the market*?\n"
    )

st.info(
    "Use the **sidebar** to switch data source and pick a property. "
    "Every table has a **Download CSV** button.",
    icon="👈",
)

st.caption(
    "Honesty note: no accuracy or F1 numbers are shown here — see `docs/TODO_RESULTS.md` "
    "for what is measured and what is still `TBD` (CLAUDE.md rule 1)."
)
