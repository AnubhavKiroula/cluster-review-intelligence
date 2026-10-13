"use client";

import { useMemo, useState } from "react";
import Plot from "@/components/Plot";
import { fmtDay, isoDate, query, useApi, type RegionResponse } from "@/lib/api";
import { fmtNum } from "@/lib/data";
import { DownloadCsv, Info, Loading, PageIntro, SectionHeading, Table } from "@/components/ui";
import { ApiErrorState, ApiStatusBanner, CategoryPill, travelStyles as s } from "@/components/travel";
import { COLORS } from "@/lib/theme";

export default function RegionPage() {
  const [start, setStart] = useState(() => isoDate(new Date()));
  const [days, setDays] = useState(90);
  const res = useApi<RegionResponse>(`/region?${query({ start, days })}`);

  const chart = useMemo(() => {
    if (!res.data) return null;
    const rows = res.data.pressure;
    return {
      data: [
        {
          type: "bar",
          name: "Average demand index",
          x: rows.map((r) => r.name),
          y: rows.map((r) => r.mean_index),
          marker: { color: COLORS.navy },
          hovertemplate: "%{x}: %{y:.0f}/100 average<extra></extra>",
        },
        {
          type: "scatter",
          mode: "markers",
          name: "Peak day",
          x: rows.map((r) => r.name),
          y: rows.map((r) => r.peak_index),
          marker: { color: COLORS.amber, size: 11, symbol: "diamond" },
          hovertemplate: "%{x}: peak %{y}/100<extra></extra>",
        },
        {
          type: "scatter",
          mode: "markers",
          name: "Assumed ceiling",
          x: rows.map((r) => r.name),
          y: rows.map((r) => Number(r.ceiling.value)),
          marker: { color: COLORS.negative, size: 14, symbol: "line-ew-open", line: { width: 3 } },
          hovertemplate: "%{x}: assumed ceiling %{y}<extra></extra>",
        },
      ],
      layout: { yaxis: { title: "demand index (0–100)", range: [0, 100] }, bargap: 0.35 },
    };
  }, [res.data]);

  return (
    <>
      <PageIntro
        eyebrow="Tourism board · destination manager"
        icon="🏔️"
        title="Regional pressure and the local economy"
        description="Where visitor pressure is expected, where there is headroom, which local-business categories are under-served, and which review issues are destination-wide."
      />
      <ApiStatusBanner />

      <div className="controls">
        <div className="field">
          <label htmlFor="rg-start">From</label>
          <input
            id="rg-start"
            className={s.controlsInput}
            type="date"
            value={start}
            onChange={(e) => e.target.value && setStart(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="rg-days">Window</label>
          <select id="rg-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[14, 30, 60, 90, 120].map((d) => (
              <option key={d} value={d}>
                {d} days
              </option>
            ))}
          </select>
        </div>
      </div>

      {res.error ? (
        <ApiErrorState error={res.error} />
      ) : !res.data || !chart ? (
        <Loading />
      ) : (
        <>
          <SectionHeading
            title="📊 Expected pressure vs assumed ceilings"
            description="Bars: average index over the window; diamonds: the busiest day; red ticks: the assumed ceiling for each place's environmental sensitivity (no official carrying capacity exists)."
          />
          <div className="chart-panel">
            <Plot data={chart.data} layout={chart.layout} height={400} />
          </div>

          <SectionHeading
            title="🧭 Destinations"
            description="Days at or above the ceiling, peak periods with their drivers, and where demand could be redistributed."
          />
          <Table
            rows={res.data.pressure}
            columns={[
              { key: "name", label: "Destination", render: (r) => <strong>{r.name}</strong> },
              { key: "region", label: "Region" },
              { key: "mean_index", label: "Avg", align: "right", render: (r) => r.mean_index.toFixed(0) },
              {
                key: "peak_day",
                label: "Peak",
                render: (r) => (
                  <>
                    {fmtDay(r.peak_day)} <CategoryPill category={r.peak_category} index={r.peak_index} />
                  </>
                ),
              },
              {
                key: "days_at_or_over_ceiling",
                label: "Days ≥ ceiling",
                align: "right",
                render: (r) => `${r.days_at_or_over_ceiling} (ceiling ${r.ceiling.value}, ${r.sensitivity})`,
              },
              {
                key: "redistribution",
                label: "Redistribute to",
                render: (r) =>
                  r.redistribution && r.redistribution.alternatives.length
                    ? r.redistribution.alternatives.map((a) => a.name).join(", ")
                    : "—",
              },
              {
                key: "official_arrivals",
                label: "Official arrivals",
                render: (r) =>
                  r.official_arrivals
                    ? `${r.official_arrivals.total.toLocaleString("en-IN")} (${r.official_arrivals.year}, UTDB)`
                    : "not published",
              },
              { key: "sellers_listed", label: "Sellers", align: "right" },
            ]}
          />
          <p className="caption">
            Official arrivals are annual totals from the Uttarakhand Tourism Development Board
            (2023); Himachal publishes no destination-level series, and UTDB has no rows for
            Dhanaulti, Kanatal, Chakrata or Lansdowne. They are context only and do not set the
            index.
          </p>

          <SectionHeading
            title="🧶 Under-served local-business categories"
            description="High expected visitor exposure but at most one listed seller: a gap to fill through onboarding. Exposure is an estimate, never sales."
          />
          {res.data.under_served_categories.length === 0 ? (
            <Info>No under-served category in this window.</Info>
          ) : (
            <Table
              rows={res.data.under_served_categories}
              columns={[
                { key: "name", label: "Destination" },
                { key: "category", label: "Category" },
                { key: "score", label: "Exposure score", align: "right" },
                { key: "sellers_listed", label: "Sellers listed", align: "right" },
              ]}
            />
          )}

          <SectionHeading
            title="⭐ Destination-wide review issues"
            description="From the review cluster (Properties A–L): issues that move together across properties are destination problems, not one hotel's."
          />
          <Table
            rows={res.data.review_issues}
            columns={[
              { key: "aspect", label: "Aspect" },
              { key: "scope", label: "Scope" },
              { key: "pattern", label: "Pattern", render: (r) => r.pattern ?? "—" },
              {
                key: "pct_negative",
                label: "% negative",
                align: "right",
                render: (r) => (r.pct_negative == null ? "—" : `${Math.round(r.pct_negative * 100)}%`),
              },
              { key: "cluster_mean", label: "Mean", align: "right", render: (r) => fmtNum(r.cluster_mean) },
            ]}
          />
          <div style={{ marginTop: 10 }}>
            <DownloadCsv
              rows={res.data.pressure.map((r) => ({
                destination: r.name,
                region: r.region,
                mean_index: r.mean_index,
                peak_day: r.peak_day,
                peak_index: r.peak_index,
                days_at_or_over_ceiling: r.days_at_or_over_ceiling,
                assumed_ceiling: r.ceiling.value,
              }))}
              filename={`region_pressure_${start}.csv`}
            />
          </div>
          <ul className="caption">
            {res.data.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
