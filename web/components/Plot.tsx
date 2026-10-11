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
}

export default function Plot({ data, layout = {}, height = 420 }: PlotProps) {
  return (
    <Plotly
      data={data}
      layout={{ ...baseLayout(), height, ...layout }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%", height }}
      useResizeHandler
    />
  );
}
