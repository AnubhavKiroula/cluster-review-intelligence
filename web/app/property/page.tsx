"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import Plot from "@/components/Plot";
import { fmtNum, fmtPct, syncQuery, useData } from "@/lib/data";
import {
  ChangeSplit,
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageHeader,
  SectionHeading,
  Table,
  WhosePill,
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

  // Keep the URL shareable: it always names the property on screen.
  useEffect(() => {
    if (prop) syncQuery({ property: prop });
  }, [prop]);

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
          marker: { symbol: "line-ew", size: 26, line: { width: 3, color: COLORS.ink } },
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
        color: c.direction === "negative" ? COLORS.negative : COLORS.positive,
        width: 1.5,
        dash: "dash",
      },
    }));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const annotations: any[] = cps.map((c) => ({
      x: `${c.change_month}-01`,
      yref: "paper",
      y: 1,
      text: `${c.change_month}: ${c.delta > 0 ? "+" : "−"}${Math.abs(c.delta).toFixed(2)} vs the market`,
      showarrow: false,
      font: { size: 12, color: c.direction === "negative" ? COLORS.negative : COLORS.positive },
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
          line: { color: COLORS.slate, width: 2 },
          marker: { size: 5 },
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
  const topShift = top?.started
    ? pdata.changepoints.find((c) => c.aspect === top.aspect && c.change_month === top.started)
    : undefined;
  // Market-wide patterns this property takes part in (per-property participation).
  const shared = data.market_scope.filter(
    (s) => s.scope === "market-wide" && s.properties.split(", ").includes(prop),
  );
  const leads = pdata.scorecard.filter((r) => r.flag === "lead").map((r) => r.aspect);
  const lags = pdata.scorecard.filter((r) => r.flag === "lag").map((r) => r.aspect);

  return (
    <>
      <PageHeader
        title={prop}
        lede="What to fix first, and whether each problem is yours alone or the whole market's."
      >
        <div className="controls">
          <div className="field">
            <label htmlFor="prop">Property</label>
            <select id="prop" name="property" value={prop} onChange={(e) => setProp(e.target.value)}>
              {data.meta.properties.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <p className="standing">
            {lags.length ? `Behind the cluster on ${lags.join(", ")}.` : "Not behind the cluster on any aspect."}
            {leads.length ? ` Ahead on ${leads.join(", ")}.` : ""}
          </p>
        </div>
      </PageHeader>

      {actions.length === 0 ? (
        <Info>Nothing lags the cluster enough to flag. This property is on par.</Info>
      ) : (
        <section className="priority" aria-labelledby="priority-title">
          <div className="priority-head">
            <h2 id="priority-title">
              Fix {top.aspect} first{top.started ? ` since ${top.started}` : ""}
            </h2>
            <WhosePill value={top.whose_problem} />
          </div>
          <div className={topShift ? "priority-body with-split" : "priority-body"}>
            <div className="priority-text">
              <p>{top.rationale}</p>
              <p>
                <strong>You or the market?</strong> {top.whose_detail}.
              </p>
              <details>
                <summary>Evidence</summary>
                <ul>
                  <li>
                    Now {fmtNum(top.current_mean)} against {fmtNum(top.reference_mean)} (
                    {top.basis === "cluster"
                      ? "the cluster over the same months"
                      : "your own level before the decline"}
                    ), mean sentiment on −1 to +1.
                  </li>
                  <li>
                    Gap {fmtNum(top.gap)} × {fmtPct(top.volume)} of your aspect mentions = impact{" "}
                    {fmtNum(top.impact_score, 3)}.
                  </li>
                  <li>
                    {top.n} mentions of {top.aspect} at this property.
                  </li>
                </ul>
              </details>
            </div>
            {topShift && (
              <ChangeSplit
                rows={[
                  { label: "Your reviews", note: "plain before and after", value: topShift.raw_delta },
                  { label: "The market", note: "other properties, same months", value: topShift.market_delta },
                  { label: "Yours alone", note: "after taking the market out", value: topShift.delta, verdict: true },
                ]}
                caption={`Change in mean ${top.aspect.toLowerCase()} sentiment at ${topShift.change_month}, on a scale from −1 to +1.`}
              />
            )}
          </div>
        </section>
      )}

      {actions.length > 0 && (
        <>
          <SectionHeading
            title="Everything behind the cluster"
            description="Ranked by gap × share of your mentions. Each row is tested against the market."
          />
          <Table
            caption={`Priority actions for ${prop}`}
            rows={actions}
            columns={[
              { key: "aspect", label: "Aspect" },
              {
                key: "whose_problem",
                label: "Whose problem",
                wide: true,
                render: (r) => (
                  <>
                    <WhosePill value={r.whose_problem} />
                    <div className="cell-note">{r.whose_detail}</div>
                  </>
                ),
              },
              { key: "started", label: "Since", render: (r) => <span className="nowrap">{r.started ?? "—"}</span> },
              { key: "gap", label: "Gap", align: "right", render: (r) => fmtNum(r.gap) },
              { key: "volume", label: "Share", align: "right", render: (r) => fmtPct(r.volume) },
              { key: "impact_score", label: "Impact", align: "right", render: (r) => fmtNum(r.impact_score, 3) },
              { key: "rationale", label: "Why", wide: true },
            ]}
          />
          <div className="table-actions">
            <DownloadCsv rows={actions} filename={`priority_actions_${prop}.csv`} />
          </div>
        </>
      )}
      {shared.length > 0 && (
        <aside className="note">
          <h3>Also hitting you, but market-wide</h3>
          <p>
            {shared.map((s) => `${s.aspect}: ${s.pattern}`).join("; ")}. Most of the cluster shares
            this, so it is not a gap against your competitors. See{" "}
            <Link href="/market/">the market</Link>.
          </p>
        </aside>
      )}

      <SectionHeading
        title="Aspect scores against the cluster"
        description="Bars are this property, with 95% intervals; the dark tick is the cluster mean."
      />
      {scorecardChart && (
        <div className="chart-panel">
          <Plot data={scorecardChart.data} layout={scorecardChart.layout} />
        </div>
      )}
      <p className="caption">
        <span className="key" style={{ background: FLAG_COLORS.lead }} /> ahead{" "}
        <span className="key" style={{ background: FLAG_COLORS.lag }} /> behind{" "}
        <span className="key" style={{ background: FLAG_COLORS.on_par }} /> on par. Flagged only
        when the interval supports it after a multiple-testing correction. Intervals are omitted for
        aspects with fewer than 10 reviews.
      </p>

      <SectionHeading
        title="Trend over time"
        description="Monthly mean sentiment for one aspect, with any significant shift against the market."
      />
      <div className="controls">
        <div className="field">
          <label htmlFor="aspect">Aspect</label>
          <select id="aspect" name="aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
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
          <div className="chart-panel">
            <Plot data={trendChart.data} layout={trendChart.layout} />
          </div>
          <p className="caption">
            {trendChart.hasCps
              ? "Dashed line: a significant shift relative to the market (false discovery rate controlled)."
              : "No statistically significant shift in this series."}
          </p>
        </>
      ) : (
        <Info>Not enough monthly data to plot {aspect} at this property.</Info>
      )}
    </>
  );
}
