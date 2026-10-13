"use client";

import { useMemo } from "react";
import Plot from "@/components/Plot";
import { fmtPct, useData } from "@/lib/data";
import {
  DownloadCsv,
  ErrorState,
  Info,
  Loading,
  PageHeader,
  SectionHeading,
  Table,
} from "@/components/ui";
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
        marker: { size: 14, color: SCOPE_COLORS[sc] ?? COLORS.stone, line: { width: 1.5, color: COLORS.paper } },
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
        { type: "line", x0: 0.5, x1: 0.5, yref: "paper", y0: 0, y1: 1, line: { color: COLORS.stone, dash: "dot", width: 1 } },
        { type: "line", xref: "paper", x0: 0, x1: 1, y0: avgNeg, y1: avgNeg, line: { color: COLORS.stone, dash: "dot", width: 1 } },
      ] as any[],
    };
  }, [data]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading />;

  const headline = data.market_headline;
  const count = (scope: string) => data.market_scope.filter((row) => row.scope === scope).length;

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
            <span>{fmtPct(headline.pct_negative)}</span> of {headline.aspect.toLowerCase()} mentions
            are negative across {headline.n_properties_reviewed} properties.
          </p>
          <p>Pattern: {headline.pattern}.</p>
        </section>
      )}

      <dl className="counts">
        <div>
          <dt>Shared across the market</dt>
          <dd style={{ color: SCOPE_COLORS["market-wide"] }}>{count("market-wide")}</dd>
        </div>
        <div>
          <dt>Belong to one property</dt>
          <dd style={{ color: SCOPE_COLORS["property-specific"] }}>{count("property-specific")}</dd>
        </div>
        <div>
          <dt>Too few properties to tell</dt>
          <dd>{count("undetermined")}</dd>
        </div>
      </dl>

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
                  <span className="scope" style={{ "--tone": SCOPE_COLORS[r.scope] ?? COLORS.stone } as React.CSSProperties}>
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
