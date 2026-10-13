"use client";

import { useEffect, useMemo, useState } from "react";
import Plot from "@/components/Plot";
import { fmtNum, syncQuery, useData, useFixChecks, type FixCheck } from "@/lib/data";
import {
  ChangeSplit,
  ChartNumbers,
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageHeader,
  SectionHeading,
  signed,
  ZoneRule,
} from "@/components/ui";
import { usePalette } from "@/lib/theme";

const VERDICT: Record<FixCheck["verdict"], { tone: string; headline: string }> = {
  improved: { tone: "up", headline: "Improved, relative to the market" },
  worsened: { tone: "down", headline: "Worsened, relative to the market" },
  "no detectable change": { tone: "flat", headline: "No detectable change relative to the market" },
  "too early to tell": { tone: "wait", headline: "Too early to tell" },
  "no data": { tone: "wait", headline: "Not enough reviews to check" },
};

export default function FixCheckPage() {
  const { data, error } = useData();
  const fix = useFixChecks();
  const [prop, setProp] = useState("");
  const [aspect, setAspect] = useState("");
  const [month, setMonth] = useState("");
  // Charts need literal colours for the viewer's scheme (light or dark).
  const C = usePalette();

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

  // Keep the URL shareable: it always names the check on screen.
  useEffect(() => {
    if (prop && aspect && month) syncQuery({ property: prop, aspect, month });
  }, [prop, aspect, month]);

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
        line: { color: C.ink, width: 1.5, dash: "dash" },
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
        font: { size: 12, color: C.ink },
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
        fillcolor: C.mist,
        line: { width: 0 },
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
        font: { size: 12, color: C.muted },
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
          line: { color: C.slate, width: 2 },
          marker: { size: 5 },
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
  }, [trend, result, month, aspect, C]);

  if (error) return <ErrorState message={error} />;
  if (fix.error) return <ErrorState message={fix.error} file="fixcheck.synthetic.json" />;
  if (!data || !fix.data || !result) return <Loading what="the fix checks" />;

  const v = VERDICT[result.verdict];
  const tested = result.effect != null;

  return (
    <>
      <PageHeader
        title="Did my fix work?"
        lede="Pick what you changed and the first month after the change. A plain before and after mixes your change with whatever the whole market did at the same time; this check takes the market out first."
      >
        <div className="controls">
          <div className="field">
            <label htmlFor="fx-prop">Property</label>
            <select id="fx-prop" name="property" value={prop} onChange={(e) => setProp(e.target.value)}>
              {data.meta.properties.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="fx-aspect">What did you change?</label>
            <select id="fx-aspect" name="aspect" value={aspect} onChange={(e) => setAspect(e.target.value)}>
              {data.meta.aspects.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="fx-month">First month after the change</label>
            <select id="fx-month" name="month" value={month} onChange={(e) => setMonth(e.target.value)}>
              {fix.data.meta.months.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>
      </PageHeader>

      <section className={`verdict ${v.tone}`} aria-live="polite">
        <h2>{v.headline}</h2>
        <p>{result.summary}</p>
      </section>

      {tested && (
        <ChangeSplit
          rows={[
            { label: "Plain before and after", note: "what a simple comparison reports", value: result.naive_delta },
            {
              label: "The market, same months",
              note: result.market_delta == null ? "too few properties review this aspect" : "what the other properties did",
              value: result.market_delta,
            },
            { label: "Your change vs the market", note: "the plain change minus the market's", value: result.effect, verdict: true },
          ]}
          caption={
            <>
              Change in mean {aspect.toLowerCase()} sentiment (−1 to +1). 95% interval for your
              change: {signed(result.ci_low)} to {signed(result.ci_high)}. Smallest change this
              data could detect: {fmtNum(result.mde)}.
            </>
          }
        />
      )}

      <ZoneRule label="The evidence" />

      <SectionHeading
        title="Before and after"
        description="The shaded band is the before window; the dashed line is your change."
      />
      {chart ? (
        <div className="chart-panel">
          <Plot
            data={chart.data}
            layout={chart.layout}
            summary={`Monthly mean ${aspect} sentiment at ${prop}, with the before window shaded and your change at ${month}.`}
          />
          <ChartNumbers
            caption={`Monthly ${aspect} sentiment at ${prop}`}
            rows={trend ?? []}
            columns={[
              { key: "month", label: "Month", render: (r) => r.month.slice(0, 7) },
              { key: "mean", label: "Mean sentiment", align: "right", render: (r) => signed(r.mean) },
              { key: "n", label: "Mentions", align: "right" },
            ]}
          />
        </div>
      ) : (
        <Info>
          Not enough monthly data to plot {aspect} at {prop}.
        </Info>
      )}
      <p className="caption">
        The before window starts at the latest significant shift before your change, so a fix made
        after a decline is compared with the declined level. Without such a shift it starts at the
        first month of data.
      </p>

      <SectionHeading title="How this is decided" />
      <dl className="method">
        <div>
          <dt>Your change vs the market</dt>
          <dd>
            Your after minus before, minus the market&apos;s change over the same months. The market
            is the other properties, each measured against its own usual level.
          </dd>
        </div>
        <div>
          <dt>Verdict</dt>
          <dd>
            Improved or worsened when p ≤ 0.05 for the one month you chose. Choosing the month
            after looking at the chart makes the p-value too optimistic.
          </dd>
        </div>
        <div>
          <dt>Placebo check</dt>
          <dd>
            Every other property goes through the same check at the same months. If several moved
            as much as you, be wary of the verdict.
          </dd>
        </div>
        <div>
          <dt>Not proof of cause</dt>
          <dd>
            Anything else you changed in the same month is mixed in. Details in{" "}
            <code>docs/methodology.md</code>, section 12.
          </dd>
        </div>
      </dl>
      <div className="table-actions">
        <DownloadCsv rows={[result]} filename={`fix_check_${prop}_${aspect}_${month}.csv`} />
      </div>
    </>
  );
}
