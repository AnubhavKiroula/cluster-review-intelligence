"use client";

import Plot from "@/components/Plot";
import { useData } from "@/lib/data";
import { ErrorState, Info, Loading, PageIntro, SectionHeading, SyntheticBanner } from "@/components/ui";
import { DIVERGING } from "@/lib/theme";

export default function ClusterPage() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  const cm = data.cluster_matrix;
  const empty = cm.properties.length === 0 || cm.aspects.length === 0;

  return (
    <>
      <PageIntro
        eyebrow="Cluster benchmark"
        icon="🗺️"
        title="Cluster heatmap"
        description="See how sentiment varies across properties and identify the aspects that create separation in the market."
      />
      <SyntheticBanner />
      <div className="insight-strip">
        <div className="insight-tile">
          <div className="tile-label">Properties compared</div>
          <div className="tile-value">{cm.properties.length}</div>
          <div className="tile-note">Rows in the cluster view</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Aspects tracked</div>
          <div className="tile-value">{cm.aspects.length}</div>
          <div className="tile-note">Columns in the benchmark</div>
        </div>
        <div className="insight-tile">
          <div className="tile-label">Reading the map</div>
          <div className="tile-value">−1 → +1</div>
          <div className="tile-note">Negative to positive sentiment</div>
        </div>
      </div>

      {empty ? (
        <Info>No labelled aspects to display yet.</Info>
      ) : (
        <>
          <SectionHeading
            title="Property × aspect sentiment"
            description="Hover a cell to inspect the mean sentiment for that property and aspect."
          />
          <div className="chart-panel">
            <Plot
              height={Math.max(360, 80 + 34 * cm.properties.length)}
              data={[
                {
                  type: "heatmap",
                  z: cm.z,
                  x: cm.aspects,
                  y: cm.properties,
                  colorscale: DIVERGING,
                  zmid: 0,
                  zmin: -1,
                  zmax: 1,
                  colorbar: { title: "mean" },
                  hovertemplate: "%{y} · %{x}<br>mean %{z:.2f}<extra></extra>",
                  hoverongaps: false,
                },
              ]}
              layout={{
                xaxis: { title: "aspect", side: "top" },
                yaxis: { title: "property", autorange: "reversed" },
              }}
            />
          </div>
          <p className="caption">Blank cells mean the property has no reviews mentioning that aspect.</p>
        </>
      )}
    </>
  );
}
