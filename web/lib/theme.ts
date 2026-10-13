"use client";

// Palette drawn from the Uttarakhand hills, in a light and a dark variant.
//   deodar  = better / leads the cluster        buransh = worse / yours alone
//   slate   = the market, everyone's            stone   = neutral, on par, not tested
//   marigold = your neighbourhood's (a decline shared by nearby properties)
// HTML takes colours from the CSS variables in globals.css (which switch with
// prefers-color-scheme). Plotly needs literal colours, so charts read the matching
// palette here through usePalette(). Keep the two in step; contrast is documented in
// web/README.md.
import { useEffect, useState } from "react";

const LIGHT = {
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
  stone: "#737F79",
  marigold: "#9A6608",
  // OpenFreeMap vector basemap (free, no key; MapLibre shows its attribution).
  mapStyle: "https://tiles.openfreemap.org/styles/positron",
};

const DARK: Palette = {
  ink: "#E3E9E5",
  muted: "#A4B1AA",
  paper: "#1B2420",
  mist: "#121915",
  panel: "#222D28",
  grid: "#2B3631",
  line: "#3B4842",
  deodar: "#74B8A0",
  buransh: "#F0789F",
  slate: "#93A9CC",
  stone: "#8D9993",
  marigold: "#E2B24E",
  mapStyle: "https://tiles.openfreemap.org/styles/dark",
};

export type Palette = typeof LIGHT;

const DARK_QUERY = "(prefers-color-scheme: dark)";

/** The chart palette for the viewer's colour scheme; follows changes live. */
export function usePalette(): Palette {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(DARK_QUERY);
    const update = () => setDark(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return dark ? DARK : LIGHT;
}

export const flagColors = (c: Palette): Record<string, string> => ({
  lead: c.deodar,
  lag: c.buransh,
  on_par: c.stone,
});

export const scopeColors = (c: Palette): Record<string, string> => ({
  "market-wide": c.slate,
  "neighbourhood-wide": c.marigold,
  "property-specific": c.buransh,
  undetermined: c.stone,
  stable: c.deodar,
});

// The same meanings as CSS variables, for HTML (pills, legend keys, counts).
export const FLAG_VARS: Record<string, string> = {
  lead: "var(--deodar)",
  lag: "var(--buransh)",
  on_par: "var(--stone)",
};

export const SCOPE_VARS: Record<string, string> = {
  "market-wide": "var(--slate)",
  "neighbourhood-wide": "var(--marigold)",
  "property-specific": "var(--buransh)",
  undetermined: "var(--stone)",
  stable: "var(--deodar)",
};

// "Whose problem is it?" uses the scope colours: yours alone = property-specific.
export const WHOSE_VARS: Record<string, string> = {
  "yours alone": "var(--buransh)",
  "your neighbourhood's": "var(--marigold)",
  "everyone's": "var(--slate)",
  "not tested": "var(--stone)",
};

// The CSS variable set by next/font in app/layout.tsx; Plotly renders in the page, so
// it can use the same self-hosted face.
const FONT = "var(--font-sans), 'Segoe UI', system-ui, sans-serif";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function baseLayout(c: Palette, overrides: Record<string, any> = {}): Record<string, any> {
  return {
    font: { family: FONT, color: c.ink, size: 13 },
    colorway: [c.slate, c.buransh, c.deodar, c.marigold, c.stone],
    margin: { l: 56, r: 16, t: 36, b: 44 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    hoverlabel: { font: { family: FONT, size: 13, color: c.ink }, bgcolor: c.paper, bordercolor: c.line },
    legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
    xaxis: { gridcolor: c.grid, zerolinecolor: c.line, linecolor: c.line },
    yaxis: { gridcolor: c.grid, zerolinecolor: c.line, linecolor: c.line },
    ...overrides,
  };
}
