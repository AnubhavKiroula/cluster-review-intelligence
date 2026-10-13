# Cluster Review Intelligence — Next.js frontend

A static Next.js (App Router + TypeScript) dashboard. It reads a **static JSON snapshot**
exported from the Python `cri.api` core — there is **no backend at runtime**, so the whole
thing deploys as static files (Vercel, Netlify, GitHub Pages, any static host).

The interface is organised as a decision workspace: a property scorecard for operational
action, a cluster benchmark for comparison, a market diagnosis for scope, a destination view
for tourism boards, and an evidence explorer for auditability. Shared navigation, signal tiles,
chart panels, and responsive layouts keep the experience consistent across every route.

> This is an alternative frontend to the Streamlit app in `../app/`, which remains the
> reference implementation. All numbers come from the same audited `cri.api` (CLAUDE.md
> rule 1); the snapshot is clearly SYNTHETIC (`cluster.synthetic.json`, rule 2).

## Data flow

```
cri.api (Python)  ──  web/scripts/export_snapshot.py  ──▶  web/public/data/cluster.synthetic.json  ──▶  Next.js (client fetch)
```

The **Did my fix work?** page (`/fix-check/`) needs a result for every property × aspect ×
month the user can pick, and there is no backend to compute one on demand. So the exporter
also writes `web/public/data/fixcheck.synthetic.json` with every combination precomputed
(2,208 checks on the sample; a few minutes). Only that page fetches it. Deep link for the
demo: `/fix-check/?property=Property%20A&aspect=Room&month=2025-12`.

Regenerate the snapshots whenever the analytics change (`--skip-fix-check` for a quick
re-export of the main snapshot only):

```bash
# from the repo root, with the project installed (pip install -e ".[dashboard]")
python web/scripts/export_snapshot.py
```

## Develop

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

The default snapshot is labelled **SYNTHETIC** in both the filename and the interface. It is
fictional data for demonstrating the product flow, not a claim about real properties.

## Build a static site

```bash
cd web
npm run build        # emits ./out (fully static)
```

Serve `out/` with any static server to preview, e.g.:

```bash
python -m http.server 8787 --directory out
```

## Deploy

Point a static host at this folder. On Vercel: set the project root to `web/`, framework
preset **Next.js**; `output: "export"` produces a static deployment. The snapshot JSON ships
in `public/`, so no build-time Python is needed.

## Notes

- Dependencies are pinned (CLAUDE.md). Charts use Plotly.js (lazy-loaded client-side).
- Pages are client components; the snapshots are fetched at runtime from the root-relative
  `/data/` (`dataUrl` in `lib/data.tsx`). A relative `data/...` URL resolved against the
  current route, so any page opened directly (e.g. `/property/?property=…`) failed to load.
  Root-relative URLs assume the site is served at a domain root (Vercel, Netlify); a GitHub
  Pages project site under `/<repo>/` would need `basePath` in `next.config.mjs`.
- `trailingSlash: true` so routes resolve as `/property/` on any static host.
