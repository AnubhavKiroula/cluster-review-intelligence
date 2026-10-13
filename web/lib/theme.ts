"use client";

// Palette drawn from the Uttarakhand hills, in a light and a dark variant.
//   deodar  = better / leads the cluster        buransh = worse / yours alone
//   slate   = the market, everyone's            stone   = neutral, on par, not tested
//   marigold = your neighbourhood's (a decline shared by nearby properties)
// HTML takes colours from the CSS variables in globals.css; Plotly needs literal
// colours, so charts read the matching palette here through usePalette(). Keep the two
// in step; contrast is documented in web/README.md.
//
// Which of the two applies is the *resolved* scheme: the reader's explicit choice if
// they made one (stored under THEME_KEY and mirrored onto <html data-theme>), else the
// device setting. CSS and charts resolve it the same way, so they can never disagree.
import { useCallback, useSyncExternalStore } from "react";
import { THEME_KEY } from "@/lib/theme-boot";

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

/** "system" follows the device; the other two are the reader's explicit choice. */
export type ThemeMode = "system" | "light" | "dark";
export type Scheme = "light" | "dark";

// The key lives in lib/theme-boot.ts, which the pre-paint script also reads; see the
// note there for why it cannot live in this ("use client") module.
export { THEME_KEY } from "@/lib/theme-boot";

const isMode = (v: unknown): v is ThemeMode => v === "system" || v === "light" || v === "dark";

function storedMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    return isMode(v) ? v : "system";
  } catch {
    // Private mode or blocked storage: fall back to the device setting.
    return "system";
  }
}

// One store for the whole page, so the stylesheet, the charts and the toggle button
// always read the same scheme. Subscribers are notified on an explicit choice and on
// a device change.
const listeners = new Set<() => void>();
const announce = () => listeners.forEach((l) => l());

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const mq = typeof window === "undefined" ? null : window.matchMedia(DARK_QUERY);
  mq?.addEventListener("change", announce);
  return () => {
    listeners.delete(listener);
    mq?.removeEventListener("change", announce);
  };
}

/** The scheme actually in force, as CSS resolves it. */
function resolved(): Scheme {
  if (typeof window === "undefined") return "light";
  const mode = storedMode();
  if (mode !== "system") return mode;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

// The server renders no theme, so both snapshots start light and the first client
// render corrects them. The inline script has already set <html data-theme>, so the
// painted colours are right before React runs either way.
const serverScheme = (): Scheme => "light";
const serverMode = (): ThemeMode => "system";

export function useScheme(): Scheme {
  return useSyncExternalStore(subscribe, resolved, serverScheme);
}

/** The reader's choice, and a setter that persists it and repaints the page. */
export function useThemeMode(): { mode: ThemeMode; scheme: Scheme; setMode: (m: ThemeMode) => void } {
  const mode = useSyncExternalStore(subscribe, storedMode, serverMode);
  const scheme = useScheme();
  const setMode = useCallback((next: ThemeMode) => {
    try {
      if (next === "system") window.localStorage.removeItem(THEME_KEY);
      else window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Unstorable choice still applies to this page view.
    }
    applyMode(next);
    announce();
  }, []);
  return { mode, scheme, setMode };
}

/** Mirror the mode onto <html> for CSS, and onto the browser chrome colour.
 *
 * app/layout.tsx emits one theme-color meta per scheme, so a reader without
 * JavaScript still gets a matching browser chrome. An explicit choice appends a
 * single unconditional meta, which browsers prefer because it comes last; choosing
 * "Auto" removes it and hands the two media metas back. */
export function applyMode(mode: ThemeMode): void {
  const root = document.documentElement;
  if (mode === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", mode);

  const OVERRIDE = "data-cri-theme-color";
  document.querySelector(`meta[${OVERRIDE}]`)?.remove();
  if (mode === "system") return;
  const meta = document.createElement("meta");
  meta.name = "theme-color";
  meta.content = mode === "dark" ? DARK.paper : LIGHT.paper;
  meta.setAttribute(OVERRIDE, "");
  document.head.append(meta);
}

/** The chart palette for the scheme in force; follows changes live. */
export function usePalette(): Palette {
  return useScheme() === "dark" ? DARK : LIGHT;
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
