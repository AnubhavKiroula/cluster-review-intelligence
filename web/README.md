# Cluster Review Intelligence — Next.js frontend

A static Next.js (App Router + TypeScript) app, and the project's only UI. It serves
one user, the hotel or homestay owner, with four pages plus home:

| Route | Answers |
|---|---|
| `/property/` | What to fix first, and whether each problem is yours alone or everyone's |
| `/market/` | Which declines are market-wide and which belong to one property |
| `/fix-check/` | Did my fix work, relative to the market? |
| `/explorer/` | Which review clause each label came from; *Try your own review* |

Every page reads a **static JSON snapshot** exported from the Python `cri.api` core,
so the site works as plain static files. Only *Try your own review* in the explorer
calls the Python API (`cri.server`, through `lib/api.ts`) at
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`, read at build time; see
`.env.example`). Without the API, that box shows an error and everything else works.

> All numbers come from the audited Python core (CLAUDE.md rule 1). The data is
> SYNTHETIC and the snapshot files say so (`*.synthetic.json`). The on-page SYNTHETIC
> banner is **hidden for now** (CLAUDE.md rule 2 asks for it; restoring it is one
> line, see `SyntheticBanner` in `components/ui.tsx`).

## Data flow

```
cri.api (Python)  ──  web/scripts/export_snapshot.py  ──▶  web/public/data/cluster.synthetic.json  ──▶  Next.js (client fetch)
```

The **Did my fix work?** page needs a result for every property × aspect × month the
user can pick, and there is no backend to compute one on demand. So the exporter also
writes `web/public/data/fixcheck.synthetic.json` with every combination precomputed
(2,208 checks on the sample; a few minutes). Only that page fetches it. Deep link for
the demo: `/fix-check/?property=Property%20A&aspect=Room&month=2025-12`.

Regenerate the snapshots whenever the analytics change:

```bash
# from the repo root, with the project installed (pip install -e .)
python web/scripts/export_snapshot.py                   # both snapshots
python web/scripts/export_snapshot.py --skip-fix-check  # main snapshot only (fast)
```

## Develop

```bash
cd web
npm ci
npm run dev          # http://localhost:3000
npx tsc --noEmit     # type-check (CI runs this and npm run build)

# optional, for Try your own review (from the repo root, pip install -e ".[api]")
uvicorn cri.server:app --port 8000
```

The default snapshot is labelled **SYNTHETIC** in both the filename and the interface. It is
fictional data for demonstrating the product flow, not a claim about real properties.

## Build a static site

```bash
cd web
npm run build        # emits ./out (fully static)
python -m http.server 8787 --directory out   # preview
```

## Deploy

Point a static host at this folder. On Vercel: import the repository and set the project
root to `web/`; `vercel.json` here sets the framework, install and build commands, the
ignored build step and the response headers, and `package.json` pins Node.js 22.
`output: "export"` produces a static deployment. The snapshot JSON ships in `public/`, so
no build-time Python is needed. See `docs/DEPLOYMENT.md`.

## Design

One stylesheet (`app/globals.css`, no CSS framework) and one palette, mirrored for the
charts in `lib/theme.ts`. Colours carry meaning, and the same meaning on every page:

| Token | Hex | Means |
|---|---|---|
| `--deodar` | `#2E5B4C` | Better, ahead of the cluster, improved |
| `--buransh` (rhododendron) | `#B4235A` | Worse, behind the cluster, *yours alone* |
| `--slate` | `#4A6386` | The market, *everyone's*; also the SYNTHETIC strip |
| `--stone` | `#737F79` | Neutral, on par, not tested |
| `--marigold` | `#9A6608` | *Your neighbourhood's*: a decline nearby properties share |
| `--mist` / `--ink` | `#EEF2F0` / `#1F2D27` | Page background / text |

Light values shown; the dark variant of each is in `globals.css` and `lib/theme.ts`.

Every page is built as **two zones**: the verdict (roomy, set in the serif, the one
place with elevation and load motion) and the evidence for it (dense, flat, tabular),
with a labelled rule between them so a reader always knows which of the two they are
reading (`ZoneRule` in `components/ui.tsx`).

- **Type:** Literata for headings and the figures that carry a verdict, IBM Plex Sans
  for the interface and the numbers, and IBM Plex Sans Devanagari behind it in the same
  stack, all self-hosted by `next/font` at build time (no requests to Google from the
  browser; credits in `docs/CREDITS.md`). The Devanagari face is not decoration: 781 of
  the 5,124 sample reviews contain Devanagari, so Hindi clauses in the explorer resolve
  to a face from the same family instead of a system fallback. Sizes come from the
  `--t-*` scale in `globals.css` rather than ad-hoc values; numbers use tabular figures.
- **Motion** (`lib/motion.ts`, GSAP, loaded dynamically so it never blocks first
  paint): three rules hold everywhere. The DOM already holds the final state, so every
  helper animates *towards* what the markup rendered and a reader with reduced motion,
  without JavaScript or with a failed GSAP chunk still sees the finished figure.
  Motion carries meaning — a bar grows because the quantity grows, a number counts
  because it is a count — and nothing fades in merely to arrive.
  `prefers-reduced-motion: reduce` skips animation rather than shortening it.
  There is one load animation on the site (`components/HeroFigure.tsx`, below) and at
  most one animated element per other view. Scroll triggers use `IntersectionObserver`,
  not GSAP's ScrollTrigger, because Plotly measures its charts after mount and changes
  section heights, which invalidates ScrollTrigger's cached positions.
- **Home figure** (`components/HeroFigure.tsx`): the product's argument in the order it
  makes it. A real property's monthly series draws left to right, the month it broke
  appears, then the change split resolves underneath. Series, month and all three
  deltas are read from the snapshot; only pixel positions are computed in the browser.
- **Colour scheme:** light, dark, or match the device, chosen in the header
  (`components/ThemeToggle.tsx`) and remembered in `localStorage`. CSS and charts
  resolve the same scheme from one store (`useScheme` in `lib/theme.ts`), so they
  cannot disagree. A synchronous inline script applies the stored choice before the
  first paint (`lib/theme-boot.ts`); it has to be a plain `<script>` as the first child
  of `<body>` — inside `<head>` the App Router drops it from the exported HTML, and
  `next/script` with `beforeInteractive` only reaches the flight payload under
  `output: export`, which runs after hydration and so too late to prevent the flash.
- **Change split** (`ChangeSplit` in `components/ui.tsx`): the plain change, the
  market's change over the same months, and what is left for the property alone, on a
  shared zero. It is the product's question in one figure, so it appears on home,
  `/property/` (top priority) and `/fix-check/`.
- **Maps** (`components/ClusterMap.tsx`): Plotly's MapLibre map (`scattermap`, already
  in `plotly.js-dist-min`, so no new dependency) on OpenFreeMap vector tiles
  (Positron, or Dark in dark mode): free, no API key, attribution shown by MapLibre.
  Each point is labelled with its status, not only coloured; a neighbourhood-wide
  decline is a shaded circle; every map has a "Show the numbers" table.
  Zoom: + / − / Reset buttons (keyboard-operable), Ctrl/⌘ + scroll, and a two-finger
  pinch, limited to zoom 10 (town) to 17 (street). MapLibre's cooperative gestures
  leave a plain scroll or one-finger swipe to the page. The buttons move the map with
  `jumpTo` marked as a user move, so Plotly keeps the view (`uirevision`) through
  re-renders and dark-mode switches; `easeTo`/`zoomIn` do nothing in the MapLibre
  build bundled with Plotly 2.35. `/market/?aspect=Location` deep-links the market map.
  Positions are SYNTHETIC in the sample; real ones are grid-snapped by the exporter.
- **SYNTHETIC label:** `SyntheticBanner` is built to be rendered once by
  `app/layout.tsx`, so no page can omit it. It is hidden for now; see above.
- **Shareable views:** `/property/`, `/fix-check/` and `/explorer/` keep their
  selections (and the explorer's search text) in the query string, so the address bar
  is always a deep link to what is on screen. The explorer shows 100 matches at a time
  with *Show 100 more*, marks the searched phrase where it landed in each clause
  (`Highlight` in `components/ui.tsx`, the same literal case-insensitive comparison the
  filter uses), and caps the result table's height so its column names stay in view.
- **Loading:** the snapshot is one JSON file of a few megabytes, so on a hill-town
  connection it is on screen for a while. `Loading` holds the shape of the page that is
  coming instead of showing a line of text that is then replaced by a full page, which
  moved everything under it.
- **Dark palette:** the CSS variables switch in `globals.css` (once for the device
  setting, once for an explicit choice — the two blocks must hold the same values);
  charts get the matching literal colours from `usePalette()` in `lib/theme.ts`, so
  those lists must change together too. The dark palette meets the same targets
  (lowest text pair: the *not tested* tag, 5.6:1; lowest chart mark: the pale
  change-split bar, 3.3:1). The palette itself is unchanged by the 2026-10 redesign.
- **Accessibility:** skip link, visible `:focus-visible` outlines, labelled controls,
  `aria-live` on results, scrollable tables reachable by keyboard, and the scheme
  control as a real `radiogroup` with arrow-key movement. Verified with a headless
  browser: no heading level is skipped on any page, no control other than an inline
  text link is under 24 px tall (WCAG 2.5.8), and no layout is wider than the screen at
  320, 390 or 768 px.
- **Contrast (WCAG 2.2 AA, measured):** text pairs are at least 4.5:1 (the lowest
  is the *not tested* tag, 4.7:1); chart marks, the change-split bars and
  form-control borders are at least 3:1 against white. Re-check when changing a colour.
- **Charts never rely on colour alone:** scorecard bars say *ahead* / *behind* under
  the aspect name, market scopes differ in marker shape, and every chart has a text
  summary for screen readers plus *Show the numbers*, a table of the values it plots.

## Notes

- Dependencies are pinned (CLAUDE.md). Charts use Plotly.js and animation uses GSAP,
  both lazy-loaded client-side; GSAP's licence is not OSI-approved and is spelled out in
  `docs/CREDITS.md`.
- Pages are client components; the snapshots are fetched at runtime from the root-relative
  `/data/` (`dataUrl` in `lib/data.tsx`), so a page opened directly by deep link (e.g.
  `/property/?property=…`) loads. Root-relative URLs assume the site is served at a domain
  root (Vercel, Netlify); a GitHub Pages project site under `/<repo>/` would need
  `basePath` in `next.config.mjs`.
- `trailingSlash: true` so routes resolve as `/property/` on any static host.
- The travel pages (`/explore`, `/plan`, `/provider`, `/region`) and `/cluster`,
  `/destination` were removed on 2026-10-13; they are preserved at the git tag
  `travel-layer-v1`.
