# Deploying the app

Two pieces, both free of secrets:

1. **The Next.js site in `web/`**: fully static, and **the whole product on its own**.
   `next build` emits plain HTML/JS plus two JSON snapshots exported from the Python
   `cri.api` core. All four pages (`/property`, `/market`, `/fix-check`,
   `/explorer`) and home work from these alone.
2. **The Python API (`cri.server`)**: optional. It powers only the explorer's live
   *Try your own review*. Any host that runs `uvicorn` works.

The site finds the API through `NEXT_PUBLIC_API_BASE_URL`, read **at build time**, and
the API allows the site's origin through `CRI_API_CORS_ORIGINS`.

> Open PR #40 proposes a Cloudflare deployment and also edits this file. This page
> describes what is on `main` plus the focus cut; reconcile when one of them merges.

## Next.js on Vercel (primary)

### Before every deploy: regenerate and commit the snapshots

The host only serves files from git. Whenever the analytics change, run from the repo
root (with `pip install -e .`) and commit the result:

```bash
python web/scripts/export_snapshot.py                   # both snapshots
python web/scripts/export_snapshot.py --skip-fix-check  # main snapshot only (fast)
```

`cluster.synthetic.json` feeds every page; `fixcheck.synthetic.json` holds the
precomputed *Did my fix work?* results (a few minutes to generate).

### Deploy (needs a Vercel account linked to GitHub - ~5 minutes)

1. Merge the work to `main`.
2. On <https://vercel.com>, **Add New → Project** and import
   `PxA-Labs/cluster-review-intelligence`.
3. **Root Directory: `web`.** Framework preset: Next.js (detected). Leave the build
   command and output at their defaults: `output: "export"` in `next.config.mjs` makes
   the build static. Optional environment variable: `NEXT_PUBLIC_API_BASE_URL` = the
   API's public URL (without it, *Try your own review* shows an error; every other
   page works).
4. **Deploy.** Every push to `main` then redeploys, and pull requests get preview URLs.

Not yet verified on Vercel itself (verified locally: `npm run build` in `web/`, then
`python -m http.server 8787 --directory out`, pages rendered in headless Edge). Check
Vercel's plan terms for your use; the free Hobby plan is meant for non-commercial use.

**Other static hosts** (Netlify, Cloudflare Pages): build command `npm run build`,
base directory `web`, publish directory `web/out`. GitHub Pages serves a project site
under `/<repo>/`, which needs `basePath` in `next.config.mjs` first (the data URLs are
root-relative).

### Check it

- Every page shows the **SYNTHETIC DATA** banner.
- `<url>/property/?property=Property%20F` opens directly (deep links) and shows
  **Fix Food first since 2025-06**, whose problem: **yours alone**.
- `<url>/fix-check/?property=Property%20A&aspect=Room&month=2025-12` shows
  −1.38 plain, −0.95 market, −0.43 vs the market, *No detectable change*.

Then record the URL in `README.md`, `docs/DEMO.md` and `docs/TODO_RESULTS.md`
(replacing `TBD`).

## The API (`cri.server`, optional)

Any Python host that can run a long-lived web process (for example Render, Railway,
Fly.io, a small VM). Not yet deployed; URL `TBD`. Verified locally only.

- Python **3.12** (the pinned `numpy==1.26.2` has no Python 3.13 wheels).
- Install: `pip install -e ".[api]"` from the repo root.
- Start: `uvicorn cri.server:app --host 0.0.0.0 --port $PORT`.
- Environment: `CRI_API_CORS_ORIGINS=https://<your-site>` (comma-separate several).
  Optional `CRI_MODEL_BACKEND` (default `rule`).
- Health check: `GET /health` returns `{"status": "ok", "classifier": "rule"}`.
- Start-up loads no review data (the classifier is built on the first request), so
  the process stays small.

After deploying both pieces, `<site>/explorer/` → *Try your own review* →
`Khana accha tha lekin kamra ganda tha.` shows Food +1, Room −1, Cleanliness −1.

## Never on the public app

- **No real review data.** Snapshots use the SYNTHETIC sample; real partner data and
  anything under `data/raw/` (gitignored) stay on team machines (CLAUDE.md rules
  3-4). The locally trained hill-review model is never deployed.
- No secrets in the repo or the host settings (none are needed).

## Plan B / Plan C on demo day

- **Local:** `cd web && npm run build && python -m http.server 3000 --directory out`;
  add `uvicorn cri.server:app --port 8000` only for live classify (port 3000 matches
  the API's default CORS origin).
- **Video:** the backup demo recording (HACKATHON_PLAN.md, H+18).
