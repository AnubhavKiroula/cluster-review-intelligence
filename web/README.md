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
| `--mist` / `--ink` | `#EEF2F0` / `#1F2D27` | Page background / text |

Light values shown; the dark variant of each is in `globals.css` and `lib/theme.ts`.

- **Type:** Source Serif 4 for headings, Public Sans for everything else, both
  self-hosted by `next/font` at build time (no requests to Google from the browser;
  credits in `docs/CREDITS.md`). Numbers use tabular figures.
- **Change split** (`ChangeSplit` in `components/ui.tsx`): the plain change, the
  market's change over the same months, and what is left for the property alone, on a
  shared zero. It is the product's question in one figure, so it appears on home,
  `/property/` (top priority) and `/fix-check/`.
- **SYNTHETIC label:** `SyntheticBanner` is built to be rendered once by
  `app/layout.tsx`, so no page can omit it. It is hidden for now; see above.
- **Shareable views:** `/property/`, `/fix-check/` and `/explorer/` keep their
  selections (and the explorer's search text) in the query string, so the address bar
  is always a deep link to what is on screen. The explorer shows 100 matches at a time
  with *Show 100 more*.
- **Dark mode:** follows the device setting (`prefers-color-scheme`). The CSS variables
  switch in `globals.css`; charts get the matching literal colours from `usePalette()`
  in `lib/theme.ts`, so the two lists must change together. The dark palette meets the
  same targets (lowest text pair: the *not tested* tag, 5.6:1; lowest chart mark: the pale
  change-split bar, 3.3:1).
- **Accessibility:** skip link, visible `:focus-visible` outlines, labelled controls,
  `aria-live` on results, scrollable tables reachable by keyboard; no layout wider than
  the screen at 390 px.
- **Contrast (WCAG 2.2 AA, measured):** text pairs are at least 4.5:1 (the lowest
  is the *not tested* tag, 4.7:1); chart marks, the change-split bars and
  form-control borders are at least 3:1 against white. Re-check when changing a colour.
- **Charts never rely on colour alone:** scorecard bars say *ahead* / *behind* under
  the aspect name, market scopes differ in marker shape, and every chart has a text
  summary for screen readers plus *Show the numbers*, a table of the values it plots.

## Notes

- Dependencies are pinned (CLAUDE.md). Charts use Plotly.js (lazy-loaded client-side).
- Pages are client components; the snapshots are fetched at runtime from the root-relative
  `/data/` (`dataUrl` in `lib/data.tsx`), so a page opened directly by deep link (e.g.
  `/property/?property=…`) loads. Root-relative URLs assume the site is served at a domain
  root (Vercel, Netlify); a GitHub Pages project site under `/<repo>/` would need
  `basePath` in `next.config.mjs`.
- `trailingSlash: true` so routes resolve as `/property/` on any static host.
- The travel pages (`/explore`, `/plan`, `/provider`, `/region`) and `/cluster`,
  `/destination` were removed on 2026-10-13; they are preserved at the git tag
  `travel-layer-v1`.
