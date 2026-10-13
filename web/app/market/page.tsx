"use client";

import { useEffect, useMemo, useState } from "react";
import ClusterMap from "@/components/ClusterMap";
import Plot from "@/components/Plot";
import { fmtPct, syncQuery, useData } from "@/lib/data";
import { nearestKm, positionsNote, statusFor } from "@/lib/geo";
import {
  ChartNumbers,
  Counter,
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageHeader,
  SectionHeading,
  Table,
  ZoneRule,
} from "@/components/ui";
import { SCOPE_VARS, scopeColors, usePalette } from "@/lib/theme";

// The four scopes, in the order the reader should weigh them: shared by everyone
// first, one property's own last.
const COUNTED: [string, string][] = [
  ["market-wide", "Shared across the market"],
  ["neighbourhood-wide", "Shared by one neighbourhood"],
  ["property-specific", "Belong to one property"],
  ["undetermined", "Too few properties to tell"],
];

// Shape as well as colour tells the scopes apart.
const SCOPE_SYMBOLS: Record<string, string> = {
  "market-wide": "circle",
  "neighbourhood-wide": "hexagon",
  "property-specific": "diamond",
  undetermined: "square",
  stable: "triangle-up",
};

export default function MarketPage() {
  const { data, error } = useData();
  // Charts need literal colours for the viewer's scheme (light or dark).
  const C = usePalette();
  const [mapAspect, setMapAspect] = useState("");

  // Default to an aspect with a neighbourhood-wide decline, else the headline aspect.
  // Deep link: /market/?aspect=Location
  useEffect(() => {
    if (!data || mapAspect) return;
    const wanted = new URLSearchParams(window.location.search).get("aspect");
    const fallback = data.neighbourhoods[0]?.aspect ?? data.market_headline?.aspect ?? data.meta.aspects[0];
    setMapAspect(wanted && data.meta.aspects.includes(wanted) ? wanted : fallback);
  }, [data, mapAspect]);

  useEffect(() => {
    if (mapAspect) syncQuery({ aspect: mapAspect });
  }, [mapAspect]);

  const chart = useMemo(() => {
    if (!data) return null;
    const scope = data.market_scope;
    if (scope.length === 0) return null;
    const negByAspect = new Map(data.destination_summary.map((d) => [d.aspect, d.pct_negative]));
    const scopes = Array.from(new Set(scope.map((s) => s.scope)));
    const avgNeg =
      scope.reduce((acc, s) => acc + (negByAspect.get(s.aspect) ?? 0), 0) / scope.length;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const traces: any[] = scopes.map((sc) => {
      const g = scope.filter((s) => s.scope === sc);
      return {
        type: "scatter",
        mode: "markers+text",
        name: sc,
        x: g.map((s) => s.fraction),
        y: g.map((s) => negByAspect.get(s.aspect) ?? 0),
        text: g.map((s) => s.aspect),
        textposition: "top center",
        marker: {
          size: 15,
          symbol: SCOPE_SYMBOLS[sc] ?? "circle",
          color: scopeColors(C)[sc] ?? C.stone,
          line: { width: 1.5, color: C.paper },
        },
        customdata: g.map((s) => s.n_properties),
        hovertemplate:
          "%{text}<br>share of properties affected %{x:.0%}" +
          "<br>mentions negative %{y:.0%}<br>%{customdata} properties<extra></extra>",
      };
    });

    return {
      traces,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shapes: [
        { type: "line", x0: 0.5, x1: 0.5, yref: "paper", y0: 0, y1: 1, line: { color: C.stone, dash: "dot", width: 1 } },
        { type: "line", xref: "paper", x0: 0, x1: 1, y0: avgNeg, y1: avgNeg, line: { color: C.stone, dash: "dot", width: 1 } },
      ] as any[],
    };
  }, [data, C]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  const headline = data.market_headline;
  const count = (scope: string) => data.market_scope.filter((row) => row.scope === scope).length;
  const hood = data.neighbourhoods.find((h) => h.aspect === mapAspect);
  const nearest = nearestKm(data.locations);
  const mapRows = data.meta.properties.map((p) => {
    const status = statusFor(data, p, mapAspect, C, hood);
    const loc = data.locations.find((l) => l.property_id === p);
    return { property: p, status: status.word, color: status.color, zone: loc?.zone ?? "—",
             nearest: nearest.get(p) };
  });

  return (
    <>
      <PageHeader
        title="The market"
        lede="Which declines the whole cluster shares, and which belong to one property. A shared decline is not a gap against your competitors."
      />

      {headline && (
        <section className="headline-case" aria-labelledby="headline-title">
          <h2 id="headline-title">
            {headline.aspect} is the market&apos;s biggest problem, not any one property&apos;s
          </h2>
          <p className="contrast-figure">
            <span>
              <Counter value={headline.pct_negative} format={(v) => fmtPct(v)} />
            </span>{" "}
            of {headline.aspect.toLowerCase()} mentions are negative across{" "}
            {headline.n_properties_reviewed} properties.
          </p>
          <p>Pattern: {headline.pattern}.</p>
        </section>
      )}

      {/* Four counts of aspects, by who owns the decline. Each takes the colour it
          carries everywhere else on the site, on the rule above it as well as in the
          figure. Not counted up: these are single digits, where a count would be
          motion without a quantity behind it. */}
      <dl className="counts">
        {COUNTED.map(([scope, label]) => (
          <div key={scope} style={{ "--tone": SCOPE_VARS[scope] ?? "var(--stone)" } as React.CSSProperties}>
            <dt>{label}</dt>
            <dd>{count(scope)}</dd>
          </div>
        ))}
      </dl>

      <ZoneRule label="Where it comes from" />

      {data.locations.length > 0 && mapAspect && (
        <section aria-labelledby="where-title">
          <div className="section-heading">
            <h2 id="where-title">Where it is happening</h2>
            <p>
              Each point is a property, labelled with its status for one aspect. A shaded circle
              marks a decline that nearby properties share and the rest of the market does not.
            </p>
          </div>
          <div className="controls">
            <div className="field">
              <label htmlFor="map-aspect">Aspect</label>
              <select id="map-aspect" name="aspect" value={mapAspect} onChange={(e) => setMapAspect(e.target.value)}>
                {data.meta.aspects.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {hood && (
            <aside className="note hood">
              <h3>
                {hood.aspect}: a neighbourhood problem since {hood.change_month}
              </h3>
              <p>
                {hood.members.join(", ")} declined together, by {(-hood.delta).toFixed(2)} on
                average relative to the rest of the market, within {hood.radius_km.toFixed(2)} km
                of each other. A decline this concentrated in one place arises by chance with
                p = {hood.p_value.toFixed(3)}. The useful response is shared: neighbours, the hotel
                association or the municipality, not each property on its own.
              </p>
            </aside>
          )}
          <div className="chart-panel map-panel">
            <ClusterMap
              locations={data.locations}
              neighbourhoods={hood ? [hood] : []}
              points={mapRows.map((r) => ({ id: r.property, status: r.status, color: r.color }))}
              summary={`Map of ${data.locations.length} properties for ${mapAspect}. ${
                hood
                  ? `Neighbourhood-wide decline since ${hood.change_month} at ${hood.members.join(", ")}.`
                  : "No neighbourhood-wide decline for this aspect."
              }`}
            />
            <ChartNumbers
              caption={`Status of each property for ${mapAspect}`}
              rows={mapRows}
              columns={[
                { key: "property", label: "Property" },
                {
                  key: "status",
                  label: "Status",
                  render: (r) => (
                    <span className="scope" style={{ "--tone": r.color } as React.CSSProperties}>
                      {r.status}
                    </span>
                  ),
                },
                { key: "zone", label: "Zone" },
                {
                  key: "nearest",
                  label: "Nearest property",
                  align: "right",
                  render: (r) => (r.nearest == null || !isFinite(r.nearest) ? "—" : `${r.nearest.toFixed(2)} km`),
                },
              ]}
            />
          </div>
          <p className="caption">
            {positionsNote(data)} Basemap © OpenStreetMap contributors, OpenMapTiles, OpenFreeMap.
          </p>
        </section>
      )}

      {!chart ? (
        <Info>No aspect shows a negative shift to classify yet.</Info>
      ) : (
        <>
          <SectionHeading
            title="How broad, how severe"
            description="Each dot is an aspect with a negative shift somewhere in the cluster."
          />
          <div className="chart-panel">
            <Plot
              summary={`Each aspect with a negative shift, by share of properties affected and share of mentions negative. ${data.market_scope
                .map((s) => `${s.aspect}: ${s.scope}`)
                .join("; ")}.`}
              height={480}
              data={chart.traces}
              layout={{
                xaxis: { title: "share of properties affected", tickformat: ".0%", range: [-0.05, 1.05] },
                yaxis: { title: "share of mentions negative", tickformat: ".0%" },
                shapes: chart.shapes,
              }}
            />
          </div>
          <p className="caption">
            Dotted lines mark half the cluster (vertical) and the cluster&apos;s average negative rate
            (horizontal). Top right is broad and severe; the left side is one property&apos;s
            problem. The scope itself comes from the test across properties, not from where a dot
            sits.
          </p>

          <SectionHeading
            title="Scope by aspect"
            description="Each aspect is classified from the evidence across properties."
          />
          <Table
            caption="Scope by aspect"
            rows={data.market_scope}
            columns={[
              { key: "aspect", label: "Aspect" },
              {
                key: "scope",
                label: "Scope",
                render: (r) => (
                  <span className="scope" style={{ "--tone": SCOPE_VARS[r.scope] ?? "var(--stone)" } as React.CSSProperties}>
                    {r.scope}
                  </span>
                ),
              },
              { key: "fraction", label: "Share affected", align: "right", render: (r) => fmtPct(r.fraction) },
              { key: "n_properties", label: "Properties", align: "right" },
              { key: "pattern", label: "Pattern", wide: true },
            ]}
          />
          <div className="table-actions">
            <DownloadCsv rows={data.market_scope} filename="market_scope.csv" />
          </div>
        </>
      )}
    </>
  );
}
