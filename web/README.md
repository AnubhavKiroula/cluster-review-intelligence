# Cluster Review Intelligence — Next.js frontend

A static Next.js (App Router + TypeScript) app, and the project's only UI. The review
intelligence pages read a **static JSON snapshot** exported from the Python `cri.api`
core, so they work as plain static files. The travel pages (`/explore`, `/plan`,
`/provider`, `/region`) and *Try your own review* call the Python API (`cri.server`)
at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`, read at build time;
see `.env.example`).

The interface is organised as a decision workspace: a property scorecard for operational
action, a cluster benchmark for comparison, a market diagnosis for scope, a destination view
for tourism boards, and an evidence explorer for auditability. Shared navigation, signal tiles,
chart panels, and responsive layouts keep the experience consistent across every route.

> All numbers come from the audited Python core: the snapshot from `cri.api`, the
> travel pages from `cri.travel` through the API (CLAUDE.md rule 1). Data is clearly
> SYNTHETIC (`*.synthetic.json`, banners on every page; rule 2).

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
# from the repo root, with the project installed (pip install -e .)
python web/scripts/export_snapshot.py
```

## Develop

```bash
uvicorn cri.server:app --port 8000   # from the repo root (pip install -e ".[api]")
cd web
npm ci
npm run dev          # http://localhost:3000
npx tsc --noEmit     # type-check (CI runs this and npm run build)
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
