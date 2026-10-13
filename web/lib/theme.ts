// Brand palette (docs/HACKATHON_PLAN.md section 4) + shared Plotly layout.

export const COLORS = {
  navy: "#0B2545",
  amber: "#F4A259",
  teal: "#2A9D8F",
  ink: "#13293D",
  muted: "#5B6B7B",
  paper: "#FFFFFF",
  panel: "#F2F5F8",
  grid: "#E6EBF0",
  negative: "#C1443C",
  neutral: "#E9C46A",
  positive: "#2A9D8F",
  untested: "#C9D1D9",
} as const;

export const FLAG_COLORS: Record<string, string> = {
  lead: COLORS.teal,
  lag: COLORS.negative,
  on_par: COLORS.muted,
};

export const SCOPE_COLORS: Record<string, string> = {
  "market-wide": COLORS.navy,
  "property-specific": COLORS.amber,
  undetermined: COLORS.muted,
  stable: COLORS.teal,
};

// "Whose problem is it?" uses the scope colours: yours alone = property-specific.
export const WHOSE_COLORS: Record<string, string> = {
  "yours alone": COLORS.amber,
  "everyone's": COLORS.navy,
  "not tested": COLORS.muted,
};

// CLAUDE.md rule 2: a figure drawn from SYNTHETIC data says so on the figure itself.
export const SYNTHETIC_MARK = {
  text: "SYNTHETIC",
  xref: "paper",
  yref: "paper",
  x: 1,
  y: 1.1,
  xanchor: "right",
  showarrow: false,
  font: { size: 11, color: COLORS.muted },
};

// Diverging scale for the -1..+1 sentiment heatmap.
export const DIVERGING: [number, string][] = [
  [0, COLORS.negative],
  [0.5, "#F4F6F8"],
  [1, COLORS.positive],
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function baseLayout(overrides: Record<string, any> = {}): Record<string, any> {
  return {
    font: { family: "Inter, Segoe UI, sans-serif", color: COLORS.ink, size: 14 },
    colorway: [COLORS.navy, COLORS.amber, COLORS.teal, COLORS.negative, COLORS.muted],
    margin: { l: 64, r: 24, t: 48, b: 48 },
    paper_bgcolor: COLORS.paper,
    plot_bgcolor: COLORS.paper,
    hoverlabel: { font: { size: 13 } },
    legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
    xaxis: { gridcolor: COLORS.grid, zerolinecolor: COLORS.grid },
    yaxis: { gridcolor: COLORS.grid, zerolinecolor: COLORS.grid },
    ...overrides,
  };
}
