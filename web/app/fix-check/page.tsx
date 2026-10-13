"use client";

import { useEffect, useMemo, useState } from "react";
import Plot from "@/components/Plot";
import { fmtNum, useData, useFixChecks, type FixCheck } from "@/lib/data";
import {
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageIntro,
  SectionHeading,
  SyntheticBanner,
} from "@/components/ui";
import { COLORS } from "@/lib/theme";

const VERDICT: Record<FixCheck["verdict"], { className: string; headline: string }> = {
  improved: { className: "state info", headline: "✅ Improved — relative to the market" },
  worsened: { className: "state error", headline: "⚠️ Worsened — relative to the market" },
  "no detectable change": {
    className: "state",
    headline: "➖ No detectable change relative to the market",
  },
  "too early to tell": { className: "callout", headline: "⏳ Too early to tell" },
  "no data": { className: "callout", headline: "Not enough reviews to check" },
};

const signed = (v: number | null) => (v == null ? "—" : `${v > 0 ? "+" : ""}${fmtNum(v)}`);

export default function FixCheckPage() {
  const { data, error } = useData();
  const fix = useFixChecks();
  const [prop, setProp] = useState("");
  const [aspect, setAspect] = useState("");
  const [month, setMonth] = useState("");

  // Defaults once both files are in. Deep link (demo):
  // /fix-check/?property=Property%20A&aspect=Room&month=2025-12
  useEffect(() => {
    if (!data || !fix.data) return;
    const q = new URLSearchParams(window.location.search);
    const pick = (wanted: string | null, options: string[], fallback: string) =>
      wanted && options.includes(wanted) ? wanted : fallback;
    const months = fix.data.meta.months;
    setProp((p) => p || pick(q.get("property"), data.meta.properties, data.meta.properties[0]));
    setAspect((a) => a || pick(q.get("aspect"), data.meta.aspects, data.meta.aspects[0]));
    setMonth((m) => m || pick(q.get("month"), months, months[Math.max(0, months.length - 7)]));
  }, [data, fix.data]);

  const result = fix.data && prop && aspect && month ? fix.data.results[prop]?.[aspect]?.[month] : null;
  const trend = data && prop && aspect ? data.per_property[prop]?.trends[aspect] : undefined;

  const chart = useMemo(() => {
    if (!trend || trend.length < 2 || !result) return null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const shapes: any[] = [
      {
        type: "line",
        x0: `${month}-01`,
        x1: `${month}-01`,
        yref: "paper",
        y0: 0,
        y1: 1,
        line: { color: COLORS.amber, width: 2, dash: "dash" },
      },
    ];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const annotations: any[] = [
      {
        x: `${month}-01`,
        yref: "paper",
        y: 1,
        yanchor: "bottom",
        text: "your change",
        showarrow: false,
        font: { size: 11, color: COLORS.amber },
      },
    ];
    if (result.baseline_start) {
      shapes.unshift({
        type: "rect",
        x0: `${result.baseline_start}-01`,
        x1: `${month}-01`,
        yref: "paper",
        y0: 0,
        y1: 1,
        fillcolor: COLORS.panel,
        line: { width: 1, color: COLORS.grid },
        layer: "below",
      });
      annotations.push({
        x: `${result.baseline_start}-01`,
        yref: "paper",
        y: 1,
        xanchor: "left",
        yanchor: "bottom",
        text: "before",
        showarrow: false,
        font: { size: 11, color: COLORS.muted },
      });
    }
    return {
      data: [
        {
          type: "scatter",
          mode: "lines+markers",
          name: aspect,
          x: trend.map((p) => p.month),
          y: trend.map((p) => p.mean),
          line: { color: COLORS.navy, width: 2.5 },
          customdata: trend.map((p) => p.n),
          hovertemplate: "%{x|%b %Y}<br>mean %{y:.2f} (n=%{customdata})<extra></extra>",
        },
      ],
      layout: {
        yaxis: { title: "mean sentiment (−1…+1)", range: [-1.05, 1.05] },
        xaxis: { type: "date" },
        shapes,
        annotations,
        showlegend: false,
      },
    };
  }, [trend, result, month, aspect]);

  if (error) return <ErrorState message={error} />;
  if (fix.error)
    return (
      <div className="state error">
        Failed to load <code>data/fixcheck.synthetic.json</code>: {fix.error}
        <br />
        Run <code>npm run export:data</code> to regenerate it.
      </div>
    );
  if (!data || !fix.data || !result) return <Loading />;

  const v = VERDICT[result.verdict];
  const tested = result.effect != null;

  return (
    <>
      <PageIntro
        eyebrow="Intervention check"
        icon="🔧"
        title="Did my fix work?"
        description="Pick what you changed and the first month after the change. A plain before/after mixes your change with whatever the whole market did at the same time; this check removes the market first."
      />
      <SyntheticBanner />

      <div className="controls">
        <div className="field">
          <label htmlFor="fx-prop">Property</label>
          <select id="fx-prop" value={prop} onChange={(e) => setProp(e.target.value)}>
            {data.meta.properties.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="fx-aspect">What did you change?</label>
          <select id="fx-aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
            {data.meta.aspects.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="fx-month">First month after the change</label>
          <select id="fx-month" value={month} onChange={(e) => setMonth(e.target.value)}>
            {fix.data.meta.months.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={v.className} role="status">
        <strong>{v.headline}.</strong> {result.summary}
      </div>

      {tested && (
        <div className="insight-strip">
          <div className="insight-tile">
            <div className="tile-label">Plain before → after</div>
            <div className="tile-value">{signed(result.naive_delta)}</div>
            <div className="tile-note">What a simple comparison would report</div>
          </div>
          <div className="insight-tile">
            <div className="tile-label">Market over the same months</div>
            <div className="tile-value">{signed(result.market_delta)}</div>
            <div className="tile-note">
              {result.market_delta == null
                ? "Too few properties review this aspect"
                : "What the other properties did meanwhile"}
            </div>
          </div>
          <div className="insight-tile">
            <div className="tile-label">Your change vs the market</div>
            <div className="tile-value">{signed(result.effect)}</div>
            <div className="tile-note">
              95% CI {signed(result.ci_low)} to {signed(result.ci_high)} · smallest detectable{" "}
              {fmtNum(result.mde)}
            </div>
          </div>
        </div>
      )}

      <SectionHeading
        title="📈 Before and after"
        description="Shaded = the before window; dashed = your change."
      />
      {chart ? (
        <div className="chart-panel">
          <Plot data={chart.data} layout={chart.layout} />
        </div>
      ) : (
        <Info>
          Not enough monthly data to plot {aspect} at {prop}.
        </Info>
      )}
      <p className="caption">
        The before window starts at the latest significant shift before your change (so a fix made
        after a decline is compared with the declined level), or at the first month of data.
      </p>

      <SectionHeading title="How this is decided" />
      <ul className="caption">
        <li>
          <strong>Your change vs the market</strong> = your after − before, minus the market&apos;s
          change over the same months. The market is the other properties, each measured against its
          own usual level.
        </li>
        <li>
          <strong>Verdict</strong>: improved / worsened when p ≤ 0.05 for the one month you chose.
          Choosing the month <em>after</em> looking at the chart makes the p-value too optimistic.
        </li>
        <li>
          <strong>Placebo check</strong>: every other property goes through the same check at the
          same months. If several moved as much as you, be wary of the verdict.
        </li>
        <li>
          <strong>Not proof of cause</strong>: anything else you changed in the same month is mixed
          in. Details: <code>docs/methodology.md</code> section 12.
        </li>
      </ul>
      <div style={{ marginTop: 10 }}>
        <DownloadCsv rows={[result]} filename={`fix_check_${prop}_${aspect}_${month}.csv`} />
      </div>
    </>
  );
}
