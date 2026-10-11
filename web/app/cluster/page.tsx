"use client";

import Plot from "@/components/Plot";
import { useData } from "@/lib/data";
import { ErrorState, Info, Loading, SyntheticBanner } from "@/components/ui";
import { DIVERGING } from "@/lib/theme";

export default function ClusterPage() {
  const { data, error } = useData();
  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  const cm = data.cluster_matrix;
  const empty = cm.properties.length === 0 || cm.aspects.length === 0;

  return (
    <>
      <h1>🗺️ Cluster heatmap</h1>
      <SyntheticBanner />
      <p className="lede">
        Mean sentiment per <strong>property × aspect</strong>. Red = negative, teal = positive.
      </p>

      {empty ? (
        <Info>No labelled aspects to display yet.</Info>
      ) : (
        <>
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
          <p className="caption">Blank cells mean the property has no reviews mentioning that aspect.</p>
        </>
      )}
    </>
  );
}
