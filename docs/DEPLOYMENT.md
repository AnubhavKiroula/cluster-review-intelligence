# Deploying the dashboard (Streamlit Community Cloud)

The dashboard runs from `main` on Streamlit Community Cloud's free tier. It needs no
secrets: by default it generates the **SYNTHETIC** sample in memory.

## What is already in the repo

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

## Deploy (needs your GitHub login - ~5 minutes)

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

## Check it

- Every page shows the yellow **SYNTHETIC DATA** banner.
- `<app-url>/Property?property=Property F` opens the demo property; *Fix this
  first* says **Food**, started around **2025-06**.
- Explorer → *Try your own review* → `Khana accha tha lekin kamra ganda tha.` shows
  Food +1, Room −1, Cleanliness −1.

Then record the URL in `README.md`, `docs/DEMO.md` and `docs/TODO_RESULTS.md`
(replacing `TBD`).

## If the build fails on `.[dashboard]`

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

- **Local:** `python -m pip install -e ".[dashboard]"` then `streamlit run app/Home.py`.
- **Video:** the backup demo recording (HACKATHON_PLAN.md, H+18).
