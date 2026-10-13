"use client";

import { useMemo } from "react";
import Plot from "@/components/Plot";
import { fmtPct, useData } from "@/lib/data";
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
  useSource,
} from "@/components/ui";
import { COLORS, SCOPE_COLORS, SYNTHETIC_MARK } from "@/lib/theme";

export default function MarketPage() {
  const { data: real, demo, error } = useData();
  const [source, setSource] = useSource();
  const data = source === "demo" ? demo : real;

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
        marker: { size: 16, color: SCOPE_COLORS[sc] ?? COLORS.muted, line: { width: 1, color: "#fff" } },
        customdata: g.map((s) => s.n_properties),
        hovertemplate:
          "%{text}<br>share of properties affected %{x:.0%}" +
          "<br>reviews negative %{y:.0%}<br>n_properties=%{customdata}<extra></extra>",
      };
    });

    return {
      traces,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shapes: [
        { type: "line", x0: 0.5, x1: 0.5, yref: "paper", y0: 0, y1: 1, line: { color: COLORS.muted, dash: "dot", width: 1 } },
        { type: "line", xref: "paper", x0: 0, x1: 1, y0: avgNeg, y1: avgNeg, line: { color: COLORS.muted, dash: "dot", width: 1 } },
      ] as any[],
    };
  }, [data]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  const headline = data.market_headline;
  const town = data.meta.provenance?.town ?? "this cluster";
  // Descriptive only (not a market-wide test): where guests complain most.
  const mostComplained = [...data.destination_summary]
    .sort((a, b) => b.pct_negative - a.pct_negative)
    .slice(0, 3);
  const marketWideCount = data.market_scope.filter((row) => row.scope === "market-wide").length;
  const propertySpecificCount = data.market_scope.filter((row) => row.scope === "property-specific").length;

  return (
    <>
      <PageIntro
        eyebrow="Market diagnosis"
        icon="⚖️"
        title="Market-wide vs property-specific"
        description="Is a weakness one property's problem or the whole market's? One hotel's own reviews cannot tell; the cluster can."
        chip={<SourceChip kind={source === "demo" ? "simulated" : "real"} />}
      />
      <SourceToggle value={source} onChange={setSource} />
      {headline ? (
        <div className="callout">
          <strong>{headline.aspect}</strong> is the biggest market-wide weak spot:{" "}
          {fmtPct(headline.pct_negative)} of its mentions are negative across{" "}
          {headline.n_properties_reviewed} properties ({headline.pattern}). It is not a gap
          against your competitors: it is a <strong>market opportunity for whoever fixes it
          first</strong>.
        </div>
      ) : (
        <div className="callout">
          <strong>No shared weak spot in {town}.</strong> No aspect draws more complaints at
          most properties, so every gap flagged below belongs to individual properties. Where
          guests complain most across the cluster (descriptive, not a market test):{" "}
          {mostComplained.map((r) => `${r.aspect} ${fmtPct(r.pct_negative)}`).join(", ")} of
          mentions.
        </div>
      )}
      <div className="insight-strip">
        <div className="insight-tile">
          <div className="tile-label">Market-wide signals</div>
          <div className="tile-value">{marketWideCount}</div>
          <div className="tile-note">Patterns shared across the cluster</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Property-specific gaps</div>
          <div className="tile-value">{propertySpecificCount}</div>
          <div className="tile-note">Issues a property can act on</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Decision rule</div>
          <div className="tile-value">Tested</div>
          <div className="tile-note">Scope comes from statistical patterns</div>
        </div>
      </div>

      {!chart ? (
        <Info>No aspects show a negative shift to classify yet.</Info>
      ) : (
        <>
          <div className="chart-panel">
            <Plot
              height={520}
              data={chart.traces}
              layout={{
                xaxis: { title: "share of properties affected", tickformat: ".0%", range: [-0.05, 1.05] },
                yaxis: { title: "share of reviews negative", tickformat: ".0%" },
                shapes: chart.shapes,
                annotations: source === "demo" ? [SYNTHETIC_MARK] : [],
              }}
            />
          </div>
          <p className="caption">
            Dotted lines: half the cluster (vertical) and the cluster&apos;s average negative rate
            (horizontal). Top-right = broad and severe (market-wide); left = property-specific.{" "}
            <code>undetermined</code> = too few properties review the aspect to tell.
          </p>

          <SectionHeading
            title="Scope by aspect"
            description="Each aspect is classified from the evidence across properties, not from chart position alone."
          />
          <Table
            rows={data.market_scope}
            columns={[
              { key: "aspect", label: "Aspect" },
              { key: "scope", label: "Scope" },
              { key: "fraction", label: "Share affected", align: "right", render: (r) => fmtPct(r.fraction) },
              { key: "n_properties", label: "# props", align: "right" },
              { key: "pattern", label: "Pattern" },
            ]}
          />
          <div style={{ marginTop: 10 }}>
            <DownloadCsv rows={data.market_scope} filename="market_scope.csv" />
          </div>
        </>
      )}
    </>
  );
}
