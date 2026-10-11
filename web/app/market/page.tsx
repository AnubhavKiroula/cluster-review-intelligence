"use client";

import { useMemo } from "react";
import Plot from "@/components/Plot";
import { fmtPct, useData } from "@/lib/data";
import { DownloadCsv, ErrorState, Info, Loading, SyntheticBanner, Table } from "@/components/ui";
import { COLORS, SCOPE_COLORS } from "@/lib/theme";

export default function MarketPage() {
  const { data, error } = useData();

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

  return (
    <>
      <h1>⚖️ Market-wide vs property-specific</h1>
      <SyntheticBanner />
      <p className="lede">
        The same low score means two different things. A <strong>property-specific</strong> gap is
        one a hotel owns and can win on. A <strong>market-wide</strong> issue hits most of the
        cluster — a destination problem, not a hotel one. <em>Same chart, two different actions.</em>
      </p>

      {!chart ? (
        <Info>No aspects show a negative shift to classify yet.</Info>
      ) : (
        <>
          <Plot
            height={520}
            data={chart.traces}
            layout={{
              xaxis: { title: "share of properties affected", tickformat: ".0%", range: [-0.05, 1.05] },
              yaxis: { title: "share of reviews negative", tickformat: ".0%" },
              shapes: chart.shapes,
            }}
          />
          <p className="caption">
            Dotted lines: half the cluster (vertical) and the cluster&apos;s average negative rate
            (horizontal). Top-right = broad and severe (market-wide); left = property-specific.{" "}
            <code>undetermined</code> = too few properties review the aspect to tell.
          </p>

          <h2>Scope by aspect</h2>
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
