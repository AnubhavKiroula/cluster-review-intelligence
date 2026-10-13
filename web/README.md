# Cluster Review Intelligence — Next.js frontend

A static Next.js (App Router + TypeScript) app, and the project's only UI. It serves
one user, the hotel or homestay owner, with four pages plus home:

| Route | Answers |
|---|---|
| `/property/` | What to fix first, and whether each problem is yours alone or everyone's |
| `/market/` | Which declines are market-wide and which belong to one property |
| `/fix-check/` | Did my fix work, relative to the market? |
| `/explorer/` | Which review clause each label came from; *Try your own review* |

Every page reads **static JSON snapshots** exported from the Python `cri.api` core,
so the site works as plain static files:

| Snapshot | Contents | Used by |
|---|---|---|
| `cluster.real.json` | The **real** Kausani cluster (25 hotels, 2,751 reviews): aggregates only, no review text, no dates | home, `/property`, `/market` (default) |
| `cluster.synthetic.json` | The **SYNTHETIC** cluster: the simulated timeline and the explorer's illustrative texts | `/property` and `/market` with `?source=demo` (the *Method demo* switch), `/fix-check` (trend), `/explorer` |
| `fixcheck.synthetic.json` | Every fix-check result, precomputed | `/fix-check` |

Each page header carries a **provenance chip** (`SourceChip` in
`components/ui.tsx`): `Kausani · 25 hotels · 2,751 real reviews · TripAdvisor`,
`Method demo · simulated timeline`, or `Illustrative examples · SYNTHETIC reviews`
(hover for the source details). Figures drawn from SYNTHETIC data carry a
`SYNTHETIC` mark. Only *Try your own review* in the explorer
calls the Python API (`cri.server`, through `lib/api.ts`) at
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`, read at build time; see
`.env.example`). Without the API, that box shows an error and everything else works.

> All numbers come from the audited Python core (CLAUDE.md rule 1). SYNTHETIC data is
> labelled in its filenames, chips and figures (rule 2); real properties are
> anonymised (rule 4).

## Data flow

```
data/raw/external (local) ─ scripts/prepare_real_cluster.py ─┐
                                                             ├─ cri.api ─ web/scripts/export_snapshot.py ─▶ web/public/data/*.json ─▶ Next.js (client fetch)
SYNTHETIC generator (cri.generate) ──────────────────────────┘
```

The real input lives only on the machine of whoever downloaded the dataset; without
it the exporter keeps the committed `cluster.real.json` and regenerates the rest.

The **Did my fix work?** page needs a result for every property × aspect × month the
user can pick, and there is no backend to compute one on demand. So the exporter also
writes `web/public/data/fixcheck.synthetic.json` with every combination precomputed
(2,208 checks on the sample; a few minutes). Only that page fetches it. Deep link for
the demo: `/fix-check/?property=Property%20A&aspect=Room&month=2025-12`.

Regenerate the snapshots whenever the analytics change:

```bash
# from the repo root, with the project installed (pip install -e .)
python scripts/prepare_real_cluster.py --town Kausani   # local only, needs the Kaggle data
python web/scripts/export_snapshot.py                   # all snapshots
python web/scripts/export_snapshot.py --skip-fix-check  # skip the slow fix-check grid
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

The real snapshot has no review dates, so trends and the fix check run on the
SYNTHETIC timeline, which is labelled in its filename, chip and figures. It is
fictional data for demonstrating the time method, not a claim about real properties.

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
