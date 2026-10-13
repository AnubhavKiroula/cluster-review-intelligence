"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import Plot from "@/components/Plot";
import { fmtNum, fmtPct, useData } from "@/lib/data";
import {
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageIntro,
  SectionHeading,
  SourceChip,
  SourceToggle,
  Table,
  WhosePill,
  useSource,
} from "@/components/ui";
import { COLORS, FLAG_COLORS, SYNTHETIC_MARK } from "@/lib/theme";

export default function PropertyPage() {
  const { data: real, demo, error } = useData();
  const [source, setSource] = useSource();
  const data = source === "demo" ? demo : real;
  const marks = source === "demo" ? [SYNTHETIC_MARK] : [];
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
      layout: { yaxis: { title: "mean sentiment (−1…+1)", range: [-1.05, 1.05] }, annotations: marks },
    };
  }, [pdata, prop, source]); // eslint-disable-line react-hooks/exhaustive-deps

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
        annotations: [...annotations, ...marks],
      },
      hasCps: cps.length > 0,
    };
  }, [pdata, aspect, source]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorState message={error} />;
  if (!data || !pdata) return <Loading />;

  const actions = pdata.priority_actions;
  const top = actions[0];
  // Market-wide patterns this property takes part in (per-property participation).
  const shared = data.market_scope.filter(
    (s) => s.scope === "market-wide" && s.properties.split(", ").includes(prop),
  );
  const strongest = [...pdata.scorecard].sort((a, b) => b.mean - a.mean)[0];
  const town = data.meta.provenance?.town ?? "the cluster";
  const weakest = [...pdata.scorecard].sort((a, b) => a.mean - b.mean)[0];

  return (
    <>
      <PageIntro
        eyebrow="Property workspace"
        icon="🏨"
        title={prop}
        description="What to fix first, and whether each problem is yours alone or the whole market's. Only the cluster can tell the two apart."
        chip={<SourceChip kind={source === "demo" ? "simulated" : "real"} />}
      />
      <SourceToggle value={source} onChange={setSource} />

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

      <div className="insight-strip">
        <div className="insight-tile">
          <div className="tile-label">Star average</div>
          <div className="tile-value">{pdata.stars.mean.toFixed(2)}★</div>
          <div className="tile-note">
            {pdata.stars.n_reviews} reviews; {actions.length} flagged gap
            {actions.length === 1 ? "" : "s"} below
          </div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Strongest aspect</div>
          <div className="tile-value">{strongest?.aspect ?? "—"}</div>
          <div className="tile-note">Highest mean sentiment in the scorecard</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Watch closely</div>
          <div className="tile-value">{weakest?.aspect ?? "—"}</div>
          <div className="tile-note">Lowest mean sentiment in the scorecard</div>
        </div>
      </div>

      <SectionHeading
        title="🎯 Fix this first — and whose problem is it?"
        description="Ranked by gap × share of your mentions. Each row is tested against the market: yours alone, or everyone's."
      />
      {actions.length === 0 ? (
        <Info>This property is on par with its cluster — nothing lags enough to flag.</Info>
      ) : (
        <>
          <div className="action-card">
            <div className="action-head">
              <h3>
                Fix {top.aspect} first{top.started ? ` since ${top.started}` : ""}
              </h3>
              <WhosePill value={top.whose_problem} />
            </div>
            <p>
              <strong>Why:</strong> {top.rationale}
            </p>
            <p>
              <strong>You or the market?</strong> {top.whose_detail}.
            </p>
            <details>
              <summary>Evidence</summary>
              <ul>
                <li>
                  Now {fmtNum(top.current_mean)} vs {fmtNum(top.reference_mean)} (
                  {top.basis === "cluster"
                    ? "the cluster over the same months"
                    : "your own level before the decline"}
                  ), mean sentiment on −1…+1
                </li>
                <li>
                  Gap {fmtNum(top.gap)} × {fmtPct(top.volume)} of your aspect mentions = impact{" "}
                  {fmtNum(top.impact_score, 3)}
                </li>
                <li>{top.n} mentions of {top.aspect} at this property</li>
              </ul>
            </details>
          </div>
          <Table
            rows={actions}
            columns={[
              { key: "aspect", label: "Aspect" },
              {
                key: "whose_problem",
                label: "Whose problem",
                render: (r) => (
                  <>
                    <WhosePill value={r.whose_problem} />
                    <div className="whose-detail">{r.whose_detail}</div>
                  </>
                ),
              },
              { key: "started", label: "Started", render: (r) => r.started ?? "—" },
              { key: "gap", label: "Gap", align: "right", render: (r) => fmtNum(r.gap) },
              {
                key: "volume",
                label: "Share",
                align: "right",
                render: (r) => fmtPct(r.volume),
              },
              {
                key: "impact_score",
                label: "Impact",
                align: "right",
                render: (r) => fmtNum(r.impact_score, 3),
              },
              { key: "rationale", label: "Why" },
            ]}
          />
          <div style={{ marginTop: 10 }}>
            <DownloadCsv rows={actions} filename={`priority_actions_${prop}.csv`} />
          </div>
        </>
      )}
      {shared.length > 0 && (
        <p className="caption">
          <strong>Also hitting you, but market-wide:</strong>{" "}
          {shared.map((s) => `${s.aspect}: ${s.pattern}`).join("; ")}. Most of the cluster shares
          these, so they are not a gap against your competitors — see{" "}
          <Link href="/market/">Market</Link>.
        </p>
      )}

      <SectionHeading
        title="📊 Aspect scores vs the cluster"
        description="Bars show this property; the navy marker is the cluster mean."
      />
      {scorecardChart && (
        <div className="chart-panel">
          <Plot data={scorecardChart.data} layout={scorecardChart.layout} />
        </div>
      )}
      <p className="caption">
        Bar colour = <strong>lead</strong> (teal) / <strong>lag</strong> (red) /{" "}
        <strong>on-par</strong> (grey), flagged only when the confidence interval supports it. Error
        bars are omitted for aspects with fewer than 10 reviews. The navy marker is the cluster mean.
      </p>

      <SectionHeading
        title="📈 Trend over time"
        description="Select an aspect to inspect monthly movement and significant changepoints."
      />
      {data.meta.has_dates && (
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
      )}
      {!data.meta.has_dates ? (
        <Info>
          The {town} reviews carry no dates, so trends and changepoints cannot be computed.
          The time method is shown on the simulated timeline: switch to{" "}
          <strong>Method demo</strong> above, or open <Link href="/fix-check/">Did my fix work?</Link>.
        </Info>
      ) : trendChart ? (
        <>
          <div className="chart-panel">
            <Plot data={trendChart.data} layout={trendChart.layout} />
          </div>
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
