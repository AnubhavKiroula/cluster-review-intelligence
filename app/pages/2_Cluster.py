"""Cluster view — the property × aspect heatmap."""

from __future__ import annotations

import common
import plotly.graph_objects as go
import streamlit as st
import theme

from cri import api

common.configure("Cluster", icon="🗺️")
d = common.load_data()

st.title("🗺️ Cluster heatmap")
common.synthetic_banner(d)
st.markdown("Mean sentiment per **property × aspect**. Red = negative, teal = positive.")

matrix = api.cluster_matrix(d)
if matrix.empty:
    st.info("No labelled aspects to display yet.")
    st.stop()

fig = go.Figure(
    go.Heatmap(
        z=matrix.values,
        x=list(matrix.columns),
        y=list(matrix.index),
        colorscale=theme.DIVERGING,
        zmid=0,
        zmin=-1,
        zmax=1,
        colorbar={"title": "mean"},
        hovertemplate="%{y} · %{x}<br>mean %{z:.2f}<extra></extra>",
    )
)
common.style(
    fig,
    height=max(360, 60 + 32 * len(matrix.index)),
    xaxis={"title": "aspect", "side": "top"},
    yaxis={"title": "property", "autorange": "reversed"},
)
st.plotly_chart(fig, use_container_width=True)
st.caption("Blank cells mean the property has no reviews mentioning that aspect.")

st.dataframe(matrix.round(2), use_container_width=True)
common.download_button(
    matrix.round(3).reset_index(), "cluster_matrix.csv", key="dl_matrix"
)
