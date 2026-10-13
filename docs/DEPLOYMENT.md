# Deploying the dashboard

The **Next.js frontend in `web/` is the one we deploy.** It is a fully static site:
`next build` emits plain HTML/JS plus two JSON snapshots exported from the Python
`cri.api` core, so the host never runs Python and needs no secrets. The Streamlit
app below remains the reference implementation and a local fallback.

## Next.js on Vercel (primary)

### Before every deploy: regenerate and commit the snapshots

The host only serves files from git. Whenever the analytics change, run from the repo
root (with `pip install -e ".[dashboard]"`) and commit the result:

```bash
python web/scripts/export_snapshot.py   # writes web/public/data/*.synthetic.json
```

`cluster.synthetic.json` feeds every page; `fixcheck.synthetic.json` holds the
precomputed *Did my fix work?* results (a few minutes to generate).

### Deploy (needs a Vercel account linked to GitHub - ~5 minutes)

1. Merge the work to `main`.
2. On <https://vercel.com>, **Add New → Project** and import
   `AnubhavKiroula/cluster-review-intelligence`.
3. **Root Directory: `web`.** Framework preset: Next.js (detected). Leave the build
   command and output at their defaults: `output: "export"` in `next.config.mjs` makes
   the build static. No environment variables.
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
  *Fix this first* = **Food**, started around **2025-06**.
- `<url>/fix-check/?property=Property%20A&aspect=Room&month=2025-12` shows
  −1.38 plain, −0.95 market, −0.43 vs the market, *No detectable change*.

Then record the URL in `README.md`, `docs/DEMO.md` and `docs/TODO_RESULTS.md`
(replacing `TBD`).

## Alternative: Streamlit Community Cloud

The dashboard runs from `main` on Streamlit Community Cloud's free tier. It needs no
secrets: by default it generates the **SYNTHETIC** sample in memory.

### What is already in the repo

| Cloud needs | Here |
|---|---|
| A dependency file | `requirements.txt` (repo root) installs `.[dashboard]`: this package plus the pinned `streamlit`, `plotly`, `pyarrow` from `pyproject.toml` |
| Theme / server config | `.streamlit/config.toml` at the repo root (Cloud only reads it there) |
| Entry point | `app/Home.py` (pages in `app/pages/`) |
| Python | **3.12** (pinned `numpy==1.26.2` has no Python 3.13 wheels) |

Verified locally from a fresh clone in a clean Python 3.12 virtualenv: both
`pip install -r requirements.txt` and `uv pip install -r requirements.txt` install
the pinned stack, and `streamlit run app/Home.py` serves the app (health check `ok`).
Whether Community Cloud itself accepts the `.[dashboard]` line is only confirmed
once someone deploys - see the fallback below.

### Deploy (needs your GitHub login - ~5 minutes)

1. Merge the work to `main` (Cloud deploys a branch; `main` is the one to demo).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. **Create app** → **Deploy a public app from GitHub**:
   - Repository: `AnubhavKiroula/cluster-review-intelligence`
   - Branch: `main`
   - Main file path: `app/Home.py`
   - App URL: pick a short subdomain.
4. **Advanced settings** → Python version **3.12**. No secrets.
5. **Deploy**. The first build installs the requirements (a few minutes); the first
   page load labels the SYNTHETIC sample (a few seconds), then results are cached.

### Check it

- Every page shows the yellow **SYNTHETIC DATA** banner.
- `<app-url>/Property?property=Property F` opens the demo property; *Fix this
  first* says **Food**, started around **2025-06**.
- Explorer → *Try your own review* → `Khana accha tha lekin kamra ganda tha.` shows
  Food +1, Room −1, Cleanliness −1.

Then record the URL in `README.md`, `docs/DEMO.md` and `docs/TODO_RESULTS.md`
(replacing `TBD`).

### If the build fails on `.[dashboard]`

Replace the line in `requirements.txt` with an editable install plus the same
pins (keep them identical to `pyproject.toml`):

```text
-e .
plotly==5.24.1
pyarrow==25.0.1
streamlit==1.41.1
```

## Never on the public app

- **No real review data.** The *Local data/raw* source reads `data/raw/`, which is
  gitignored and therefore empty on Cloud; the app shows an error, by design. Real
  partner data stays on team machines (CLAUDE.md rules 3-4).
- No secrets in the repo or the Cloud settings (none are needed).

## Plan B / Plan C on demo day

- **Local static site:** `cd web && npm run build && python -m http.server 8787 --directory out`.
- **Local Streamlit:** `python -m pip install -e ".[dashboard]"` then `streamlit run app/Home.py`.
- **Video:** the backup demo recording (HACKATHON_PLAN.md, H+18).
