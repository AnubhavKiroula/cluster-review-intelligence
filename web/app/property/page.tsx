"use client";

import { useEffect, useMemo, useState } from "react";
import Plot from "@/components/Plot";
import { fmtNum, useData } from "@/lib/data";
import {
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  SyntheticBanner,
  Table,
} from "@/components/ui";
import { COLORS, FLAG_COLORS } from "@/lib/theme";

export default function PropertyPage() {
  const { data, error } = useData();
  const [prop, setProp] = useState<string>("");
  const [aspect, setAspect] = useState<string>("");

  // Deep link: /property?property=Property%20F (read once, client-side).
  useEffect(() => {
    if (!data) return;
    const wanted = new URLSearchParams(window.location.search).get("property");
    setProp(wanted && data.meta.properties.includes(wanted) ? wanted : data.meta.properties[0]);
  }, [data]);

  const pdata = data && prop ? data.per_property[prop] : null;

  // Default the trend aspect to the top priority, else the first aspect.
  useEffect(() => {
    if (!pdata) return;
    const top = pdata.priority_actions[0]?.aspect;
    const first = Object.keys(pdata.trends)[0];
    setAspect(top ?? first ?? "");
  }, [pdata]);

  const scorecardChart = useMemo(() => {
    if (!pdata) return null;
    const sc = pdata.scorecard;
    return {
      data: [
        {
          type: "bar",
          name: prop,
          x: sc.map((r) => r.aspect),
          y: sc.map((r) => r.mean),
          marker: { color: sc.map((r) => FLAG_COLORS[r.flag] ?? COLORS.muted) },
          error_y: {
            type: "data",
            symmetric: false,
            array: sc.map((r) => (r.ci_high != null ? r.ci_high - r.mean : 0)),
            arrayminus: sc.map((r) => (r.ci_low != null ? r.mean - r.ci_low : 0)),
            color: COLORS.ink,
            thickness: 1.2,
          },
          customdata: sc.map((r) => r.n),
          hovertemplate: "%{x}<br>mean %{y:.2f} (n=%{customdata})<extra></extra>",
        },
        {
          type: "scatter",
          mode: "markers",
          name: "Cluster mean",
          x: sc.map((r) => r.aspect),
          y: sc.map((r) => r.cluster_mean),
          marker: { symbol: "line-ew", size: 26, line: { width: 3, color: COLORS.navy } },
          hovertemplate: "%{x}<br>cluster %{y:.2f}<extra></extra>",
        },
      ],
      layout: { yaxis: { title: "mean sentiment (−1…+1)", range: [-1.05, 1.05] } },
    };
  }, [pdata, prop]);

  const trendChart = useMemo(() => {
    if (!pdata || !aspect) return null;
    const tr = pdata.trends[aspect];
    if (!tr || tr.length < 2) return null;
    const cps = pdata.changepoints.filter((c) => c.aspect === aspect);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const shapes: any[] = cps.map((c) => ({
      type: "line",
      x0: `${c.change_month}-01`,
      x1: `${c.change_month}-01`,
      yref: "paper",
      y0: 0,
      y1: 1,
      line: {
        color: c.direction === "negative" ? COLORS.negative : COLORS.teal,
        width: 2,
        dash: "dash",
      },
    }));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const annotations: any[] = cps.map((c) => ({
      x: `${c.change_month}-01`,
      yref: "paper",
      y: 1,
      text: `${c.direction} ${c.delta > 0 ? "+" : ""}${c.delta.toFixed(2)}`,
      showarrow: false,
      font: { size: 11, color: c.direction === "negative" ? COLORS.negative : COLORS.teal },
      yanchor: "bottom",
    }));
    return {
      data: [
        {
          type: "scatter",
          mode: "lines+markers",
          name: aspect,
          x: tr.map((p) => p.month),
          y: tr.map((p) => p.mean),
          line: { color: COLORS.navy, width: 2.5 },
          customdata: tr.map((p) => p.n),
          hovertemplate: "%{x|%b %Y}<br>mean %{y:.2f} (n=%{customdata})<extra></extra>",
        },
      ],
      layout: {
        yaxis: { title: "mean sentiment (−1…+1)", range: [-1.05, 1.05] },
        xaxis: { type: "date" },
        shapes,
        annotations,
      },
      hasCps: cps.length > 0,
    };
  }, [pdata, aspect]);

  if (error) return <ErrorState message={error} />;
  if (!data || !pdata) return <Loading />;

  const actions = pdata.priority_actions;
  const top = actions[0];

  return (
    <>
      <h1>🏨 {prop}</h1>
      <SyntheticBanner />

      <div className="controls">
        <div className="field">
          <label htmlFor="prop">Property</label>
          <select id="prop" value={prop} onChange={(e) => setProp(e.target.value)}>
            {data.meta.properties.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
      </div>

      <h2>🎯 Fix this first</h2>
      {actions.length === 0 ? (
        <Info>This property is on par with its cluster — nothing lags enough to flag.</Info>
      ) : (
        <>
          <div className="callout">
            <strong>{top.aspect}</strong> is the biggest opportunity
            {top.started ? (
              <>
                {" "}
                — started around <strong>{top.started}</strong>
              </>
            ) : null}
            . {top.rationale}
          </div>
          <Table
            rows={actions}
            columns={[
              { key: "aspect", label: "Aspect" },
              { key: "gap", label: "Gap", align: "right", render: (r) => fmtNum(r.gap) },
              { key: "volume", label: "Volume", align: "right", render: (r) => fmtNum(r.volume) },
              {
                key: "impact_score",
                label: "Impact",
                align: "right",
                render: (r) => fmtNum(r.impact_score, 3),
              },
              { key: "started", label: "Started", render: (r) => r.started ?? "—" },
              { key: "basis", label: "Basis" },
              { key: "rationale", label: "Why" },
            ]}
          />
          <div style={{ marginTop: 10 }}>
            <DownloadCsv rows={actions} filename={`priority_actions_${prop}.csv`} />
          </div>
        </>
      )}

      <h2>📊 Aspect scores vs the cluster</h2>
      {scorecardChart && <Plot data={scorecardChart.data} layout={scorecardChart.layout} />}
      <p className="caption">
        Bar colour = <strong>lead</strong> (teal) / <strong>lag</strong> (red) /{" "}
        <strong>on-par</strong> (grey), flagged only when the confidence interval supports it. Error
        bars are omitted for aspects with fewer than 10 reviews. The navy marker is the cluster mean.
      </p>

      <h2>📈 Trend over time</h2>
      <div className="controls">
        <div className="field">
          <label htmlFor="aspect">Aspect</label>
          <select id="aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
            {Object.keys(pdata.trends).map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
      </div>
      {trendChart ? (
        <>
          <Plot data={trendChart.data} layout={trendChart.layout} />
          <p className="caption">
            {trendChart.hasCps
              ? "Dashed line = a significant shift relative to the market (FDR-controlled)."
              : "No statistically significant changepoint detected for this series."}
          </p>
        </>
      ) : (
        <Info>Not enough monthly data to plot a trend for {aspect} at this property.</Info>
      )}
    </>
  );
}
