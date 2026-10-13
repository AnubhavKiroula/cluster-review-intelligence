"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import ClusterMap from "@/components/ClusterMap";
import Plot from "@/components/Plot";
import { fmtNum, fmtPct, syncQuery, useData } from "@/lib/data";
import { haversineKm, positionsNote, statusFor } from "@/lib/geo";
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
  Table,
  WhosePill,
  ZoneRule,
} from "@/components/ui";
import { flagColors, FLAG_VARS, usePalette } from "@/lib/theme";

const FLAG_WORD: Record<string, string> = { lead: "ahead", lag: "behind", on_par: "on par" };

export default function PropertyPage() {
  const { data, error } = useData();
  const [prop, setProp] = useState<string>("");
  const [aspect, setAspect] = useState<string>("");
  // Charts need literal colours for the viewer's scheme (light or dark).
  const C = usePalette();

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
          marker: { color: sc.map((r) => flagColors(C)[r.flag] ?? C.muted) },
          error_y: {
            type: "data",
            symmetric: false,
            array: sc.map((r) => (r.ci_high != null ? r.ci_high - r.mean : 0)),
            arrayminus: sc.map((r) => (r.ci_low != null ? r.mean - r.ci_low : 0)),
            color: C.ink,
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
          marker: { symbol: "line-ew", size: 26, line: { width: 3, color: C.ink } },
          hovertemplate: "%{x}<br>cluster %{y:.2f}<extra></extra>",
        },
      ],
      layout: {
        yaxis: { title: "mean sentiment (−1…+1)", range: [-1.05, 1.05] },
        xaxis: {
          tickvals: sc.map((r) => r.aspect),
          ticktext: sc.map((r) =>
            r.flag === "on_par"
              ? r.aspect
              : `${r.aspect}<br><span style="color:${flagColors(C)[r.flag]}">${FLAG_WORD[r.flag] ?? r.flag}</span>`,
          ),
        },
        margin: { l: 56, r: 16, t: 36, b: 64 },
      },
    };
  }, [pdata, prop, C]);

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
        color: c.direction === "negative" ? C.buransh : C.deodar,
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
      font: { size: 12, color: c.direction === "negative" ? C.buransh : C.deodar },
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
          line: { color: C.slate, width: 2 },
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
  }, [pdata, aspect, C]);

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
  // A top priority shared with the neighbours: the response is collective.
  const topHood =
    top?.whose_problem === "your neighbourhood's"
      ? data.neighbourhoods.find((h) => h.aspect === top.aspect && h.members.includes(prop))
      : undefined;
  const myHoods = data.neighbourhoods.filter((h) => h.members.includes(prop));
  const here = data.locations.find((l) => l.property_id === prop);
  const mapAspect = myHoods[0]?.aspect ?? top?.aspect ?? data.meta.aspects[0];
  const mapHood = data.neighbourhoods.find((h) => h.aspect === mapAspect);
  const nearby = here
    ? data.locations
        .filter((l) => l.property_id !== prop)
        .map((l) => ({ id: l.property_id, km: haversineKm(here, l) }))
        .sort((a, b) => a.km - b.km)
        .slice(0, 3)
    : [];
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
        <section className={topHood ? "priority hood" : "priority"} aria-labelledby="priority-title">
          <div className="priority-head">
            <h2 id="priority-title">
              {topHood ? `Raise ${top.aspect} with your neighbours` : `Fix ${top.aspect} first`}
              {top.started ? ` since ${top.started}` : ""}
            </h2>
            <WhosePill value={top.whose_problem} />
          </div>
          <div className={topShift || topHood ? "priority-body with-split" : "priority-body"}>
            <div className="priority-text">
              <p>{top.rationale}</p>
              <p>
                <strong>Whose problem is it?</strong> {top.whose_detail}.
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
            {topHood && (
              <ChangeSplit
                rows={[
                  {
                    label: "You",
                    note: "your shift, relative to the rest of the market",
                    value: topHood.gaps[prop] ?? null,
                  },
                  {
                    label: "Your neighbourhood",
                    note: `${topHood.n_members} properties within ${topHood.radius_km.toFixed(2)} km, together`,
                    value: topHood.delta,
                    verdict: true,
                  },
                ]}
                caption={`Change in mean ${top.aspect.toLowerCase()} sentiment from ${topHood.change_month}, relative to the properties outside the neighbourhood (−1 to +1). The rest of the market is the zero line.`}
              />
            )}
            {!topHood && topShift && (
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

      <ZoneRule label="The evidence" />

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
          {/* A sibling of this page's other sections, so h2: with no priority actions
              above it, an h3 here skipped a level. The market page's note is nested
              inside a section and correctly stays an h3. */}
          <h2>Also hitting you, but market-wide</h2>
          <p>
            {shared.map((s) => `${s.aspect}: ${s.pattern}`).join("; ")}. Most of the cluster shares
            this, so it is not a gap against your competitors. See{" "}
            <Link href="/market/">the market</Link>.
          </p>
        </aside>
      )}

      {here && (
        <section aria-labelledby="hood-title">
          <div className="section-heading">
            <h2 id="hood-title">Your neighbourhood</h2>
            <p>
              {myHoods.length
                ? `You share a decline with nearby properties on ${myHoods.map((h) => h.aspect).join(", ")}.`
                : "No decline is shared with your neighbours: nothing nearby moved together."}{" "}
              Nearest: {nearby.map((n) => `${n.id} (${n.km.toFixed(2)} km)`).join(", ")}.
            </p>
          </div>
          <div className="chart-panel map-panel">
            <ClusterMap
              height={340}
              locations={data.locations}
              neighbourhoods={mapHood ? [mapHood] : []}
              points={data.meta.properties.map((p) => {
                const st = statusFor(data, p, mapAspect, C, mapHood);
                return { id: p, status: st.word, color: st.color, focus: p === prop };
              })}
              summary={`Map of the cluster for ${mapAspect}, with ${prop} drawn larger. ${
                mapHood ? `Neighbourhood-wide decline at ${mapHood.members.join(", ")}.` : ""
              }`}
            />
          </div>
          <p className="caption">
            Showing {mapAspect}. {positionsNote(data)} Basemap © OpenStreetMap contributors,
            OpenMapTiles, OpenFreeMap. <Link href={`/market/?aspect=${encodeURIComponent(mapAspect)}`}>Open the market map</Link>.
          </p>
        </section>
      )}

      <SectionHeading
        title="Aspect scores against the cluster"
        description="Bars are this property, with 95% intervals; the short horizontal tick is the cluster mean."
      />
      {scorecardChart && (
        <div className="chart-panel">
          <Plot
            data={scorecardChart.data}
            layout={scorecardChart.layout}
            summary={`Mean sentiment per aspect at ${prop} against the cluster mean. ${
              lags.length ? `Behind on ${lags.join(", ")}.` : "Behind on nothing."
            } ${leads.length ? `Ahead on ${leads.join(", ")}.` : ""}`}
          />
          <ChartNumbers
            caption={`Aspect scores for ${prop}`}
            rows={pdata.scorecard}
            columns={[
              { key: "aspect", label: "Aspect" },
              { key: "mean", label: "You", align: "right", render: (r) => signed(r.mean) },
              {
                key: "ci_low",
                label: "95% interval",
                align: "right",
                render: (r) => (r.ci_low == null ? "—" : `${signed(r.ci_low)} to ${signed(r.ci_high)}`),
              },
              { key: "cluster_mean", label: "Cluster", align: "right", render: (r) => signed(r.cluster_mean) },
              { key: "n", label: "Mentions", align: "right" },
              { key: "flag", label: "Verdict", render: (r) => FLAG_WORD[r.flag] ?? r.flag },
            ]}
          />
        </div>
      )}
      <p className="caption">
        <span className="key" style={{ background: FLAG_VARS.lead }} /> ahead{" "}
        <span className="key" style={{ background: FLAG_VARS.lag }} /> behind{" "}
        <span className="key" style={{ background: FLAG_VARS.on_par }} /> on par. Flagged only
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
            <Plot
              data={trendChart.data}
              layout={trendChart.layout}
              summary={`Monthly mean ${aspect} sentiment at ${prop}. ${
                trendChart.hasCps ? "Significant shifts are marked with a dashed line." : "No significant shift."
              }`}
            />
            <ChartNumbers
              caption={`Monthly ${aspect} sentiment at ${prop}`}
              rows={pdata.trends[aspect] ?? []}
              columns={[
                { key: "month", label: "Month", render: (r) => r.month.slice(0, 7) },
                { key: "mean", label: "Mean sentiment", align: "right", render: (r) => signed(r.mean) },
                { key: "n", label: "Mentions", align: "right" },
              ]}
            />
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
