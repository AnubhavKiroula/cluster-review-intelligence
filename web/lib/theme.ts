// Palette drawn from the Uttarakhand hills (globals.css holds the same values as CSS
// variables) + shared Plotly layout.
//   deodar  = better / leads the cluster        buransh = worse / yours alone
//   slate   = the market, everyone's            stone   = neutral, on par, not tested

export const COLORS = {
  ink: "#1F2D27",
  muted: "#5E6B64",
  paper: "#FFFFFF",
  mist: "#EEF2F0",
  panel: "#F5F8F6",
  grid: "#E1E7E3",
  line: "#CBD5CF",
  deodar: "#2E5B4C",
  buransh: "#B4235A",
  slate: "#4A6386",
  stone: "#97A39C",
  marigold: "#C98A12",
  // Semantic aliases used by the charts.
  negative: "#B4235A",
  positive: "#2E5B4C",
  untested: "#C9D1CC",
} as const;

export const FLAG_COLORS: Record<string, string> = {
  lead: COLORS.deodar,
  lag: COLORS.buransh,
  on_par: COLORS.stone,
};

export const SCOPE_COLORS: Record<string, string> = {
  "market-wide": COLORS.slate,
  "property-specific": COLORS.buransh,
  undetermined: COLORS.stone,
  stable: COLORS.deodar,
};

// "Whose problem is it?" uses the scope colours: yours alone = property-specific.
export const WHOSE_COLORS: Record<string, string> = {
  "yours alone": COLORS.buransh,
  "everyone's": COLORS.slate,
  "not tested": COLORS.stone,
};

// Diverging scale for the -1..+1 sentiment heatmap.
export const DIVERGING: [number, string][] = [
  [0, COLORS.buransh],
  [0.5, "#F4F6F5"],
  [1, COLORS.deodar],
];

// The CSS variable set by next/font in app/layout.tsx; Plotly renders in the page, so
// it can use the same self-hosted face.
const FONT = "var(--font-sans), 'Segoe UI', system-ui, sans-serif";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function baseLayout(overrides: Record<string, any> = {}): Record<string, any> {
  return {
    font: { family: FONT, color: COLORS.ink, size: 13 },
    colorway: [COLORS.slate, COLORS.buransh, COLORS.deodar, COLORS.marigold, COLORS.stone],
    margin: { l: 56, r: 16, t: 36, b: 44 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    hoverlabel: { font: { family: FONT, size: 13 }, bordercolor: COLORS.line },
    legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
    xaxis: { gridcolor: COLORS.grid, zerolinecolor: COLORS.line, linecolor: COLORS.line },
    yaxis: { gridcolor: COLORS.grid, zerolinecolor: COLORS.line, linecolor: COLORS.line },
    ...overrides,
  };
}
