"use client";

// Client-only Plotly wrapper (react-plotly.js can't server-render).
import dynamic from "next/dynamic";
import { baseLayout } from "@/lib/theme";

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
  /** One-sentence description of what the chart shows, read by screen readers. */
  summary: string;
}

export default function Plot({ data, layout = {}, height = 420, summary }: PlotProps) {
  return (
    // The box keeps the chart's height while Plotly loads, so nothing below it jumps.
    // Plotly's SVG is not readable by assistive technology: the summary stands in for
    // it, and each chart offers its numbers as a table ("Show the numbers").
    <div className="chart-box" style={{ minHeight: height }} role="img" aria-label={summary}>
      <Plotly
        data={data}
        layout={{ ...baseLayout(), height, ...layout }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height }}
        useResizeHandler
      />
    </div>
  );
}
