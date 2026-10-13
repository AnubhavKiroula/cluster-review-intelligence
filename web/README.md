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

> All numbers come from the audited Python core (CLAUDE.md rule 1). Data is clearly
> SYNTHETIC (`*.synthetic.json`, banners on every page; rule 2).

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

Point a static host at this folder. On Vercel: set the project root to `web/`, framework
preset **Next.js**; `output: "export"` produces a static deployment. The snapshot JSON ships
in `public/`, so no build-time Python is needed. See `docs/DEPLOYMENT.md`.

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
