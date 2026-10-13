"use client";

import { useMemo } from "react";
import Plot from "@/components/Plot";
import { fmtNum, fmtPct, useData } from "@/lib/data";
import {
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageIntro,
  SectionHeading,
  SyntheticBanner,
  Table,
} from "@/components/ui";
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
  const negativeCount = dest.filter((row) => row.pct_negative > 0).length;

  return (
    <>
      <PageIntro
        eyebrow="Tourism board view"
        icon="🧭"
        title="Destination view"
        description="See where the whole cluster underperforms and which issues are worth a coordinated destination response."
      />
      <SyntheticBanner />
      <div className="insight-strip">
        <div className="insight-tile">
          <div className="tile-label">Aspects summarised</div>
          <div className="tile-value">{dest.length}</div>
          <div className="tile-note">Destination-level view</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Market-wide issues</div>
          <div className="tile-value">{marketWide.length}</div>
          <div className="tile-note">Shared patterns for intervention</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Negative signal present</div>
          <div className="tile-value">{negativeCount}</div>
          <div className="tile-note">Aspects with negative mentions</div>
        </div>
      </div>

      <SectionHeading
        title="🚩 Top cluster-wide issues"
        description="Prioritised by the share of negative mentions among aspects classified as market-wide."
      />
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

      <SectionHeading
        title="Negative share by aspect"
        description="Use scope colour together with the rate to distinguish severity from breadth."
      />
      <div className="chart-panel">
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
      </div>
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
