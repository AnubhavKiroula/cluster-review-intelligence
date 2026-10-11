"use client";

import { useMemo } from "react";
import Plot from "@/components/Plot";
import { fmtNum, fmtPct, useData } from "@/lib/data";
import { DownloadCsv, ErrorState, Info, Loading, SyntheticBanner, Table } from "@/components/ui";
import { COLORS, SCOPE_COLORS } from "@/lib/theme";

export default function DestinationPage() {
  const { data, error } = useData();

  const ordered = useMemo(
    () => (data ? [...data.destination_summary].sort((a, b) => a.pct_negative - b.pct_negative) : []),
    [data],
  );

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  const dest = data.destination_summary;
  const marketWide = dest
    .filter((d) => d.scope === "market-wide")
    .sort((a, b) => b.pct_negative - a.pct_negative);
  const worst = marketWide[0];

  return (
    <>
      <h1>🧭 Destination view</h1>
      <SyntheticBanner />
      <p className="lede">
        For a tourism board, not a single hotel: where does the <strong>whole cluster</strong>{" "}
        underperform? Issues flagged <strong>market-wide</strong> are destination problems — worth
        coordinated action.
      </p>

      <h2>🚩 Top cluster-wide issues</h2>
      {marketWide.length === 0 ? (
        <Info>
          No aspect is flagged market-wide — problems look property-specific, not destination-wide.
        </Info>
      ) : (
        <>
          <div className="callout">
            <strong>{worst.aspect}</strong> is the biggest cluster-wide issue:{" "}
            {fmtPct(worst.pct_negative)} of its mentions are negative across{" "}
            {worst.n_properties_reviewed} properties.
          </div>
          <Table
            rows={marketWide}
            columns={[
              { key: "aspect", label: "Aspect" },
              { key: "pct_negative", label: "Negative", align: "right", render: (r) => fmtPct(r.pct_negative) },
              { key: "cluster_mean", label: "Cluster mean", align: "right", render: (r) => fmtNum(r.cluster_mean) },
              { key: "n", label: "n", align: "right" },
              { key: "n_properties_reviewed", label: "# props", align: "right" },
            ]}
          />
        </>
      )}

      <h2>Negative share by aspect</h2>
      <Plot
        height={Math.max(320, 60 + 38 * ordered.length)}
        data={[
          {
            type: "bar",
            orientation: "h",
            x: ordered.map((d) => d.pct_negative),
            y: ordered.map((d) => d.aspect),
            marker: { color: ordered.map((d) => SCOPE_COLORS[d.scope] ?? COLORS.muted) },
            customdata: ordered.map((d) => [d.scope, d.n]),
            hovertemplate: "%{y}<br>negative %{x:.0%}<br>%{customdata[0]} · n=%{customdata[1]}<extra></extra>",
          },
        ]}
        layout={{ xaxis: { title: "share of reviews negative", tickformat: ".0%" }, yaxis: { title: "" } }}
      />
      <p className="caption">
        Bar colour encodes scope: navy = market-wide, amber = property-specific, grey = undetermined,
        teal = stable.
      </p>

      <div style={{ marginTop: 10 }}>
        <DownloadCsv rows={dest} filename="destination_summary.csv" />
      </div>
    </>
  );
}
