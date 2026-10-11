# Cluster Review Intelligence — Next.js frontend

A static Next.js (App Router + TypeScript) dashboard. It reads a **static JSON snapshot**
exported from the Python `cri.api` core — there is **no backend at runtime**, so the whole
thing deploys as static files (Vercel, Netlify, GitHub Pages, any static host).

> This is an alternative frontend to the Streamlit app in `../app/`, which remains the
> reference implementation. All numbers come from the same audited `cri.api` (CLAUDE.md
> rule 1); the snapshot is clearly SYNTHETIC (`cluster.synthetic.json`, rule 2).

## Data flow

```
cri.api (Python)  ──  web/scripts/export_snapshot.py  ──▶  web/public/data/cluster.synthetic.json  ──▶  Next.js (client fetch)
```

Regenerate the snapshot whenever the analytics change:

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
- Pages are client components; `cluster.synthetic.json` is fetched at runtime from `/data/`.
- `trailingSlash: true` so routes resolve as `/property/` on any static host.
