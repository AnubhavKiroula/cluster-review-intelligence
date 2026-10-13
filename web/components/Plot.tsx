"use client";

// Client-only Plotly wrapper (react-plotly.js can't server-render).
import dynamic from "next/dynamic";
import { baseLayout, usePalette } from "@/lib/theme";

const Plotly = dynamic(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => <div className="chart-loading">Loading chart…</div>,
});

interface PlotProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layout?: Record<string, any>;
  height?: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  config?: Record<string, any>;
  /** One-sentence description of what the chart shows, read by screen readers. */
  summary: string;
}

export default function Plot({ data, layout = {}, height = 420, config = {}, summary }: PlotProps) {
  const base = baseLayout(usePalette());
  // Merge the axes rather than replace them: a page that sets an axis title must not
  // drop the themed grid and line colours.
  const merged = {
    ...base,
    height,
    ...layout,
    xaxis: { ...base.xaxis, ...layout.xaxis },
    yaxis: { ...base.yaxis, ...layout.yaxis },
  };
  return (
    // The box keeps the chart's height while Plotly loads, so nothing below it jumps.
    // Plotly's SVG is not readable by assistive technology: the summary stands in for
    // it, and each chart offers its numbers as a table ("Show the numbers").
    <div className="chart-box" style={{ minHeight: height }} role="img" aria-label={summary}>
      <Plotly
        data={data}
        layout={merged}
        config={{ displayModeBar: false, responsive: true, ...config }}
        style={{ width: "100%", height }}
        useResizeHandler
      />
    </div>
  );
}
