# Deploying the app

Two pieces, neither needing secrets:

1. **The Next.js site in `web/`** (the only UI): fully static. `next build` emits
   plain HTML/JS plus two JSON snapshots exported from the Python `cri.api` core.
   The G5 pages work from these alone.
2. **The Python API (`cri.server`)**: needed by the travel pages and *Try your own
   review*.

The site finds the API through `NEXT_PUBLIC_API_BASE_URL`, read **at build time**, and
the API allows the site's origin through `CRI_API_CORS_ORIGINS`.

**Primary target: Cloudflare.**

| Piece | Cloudflare product | Plan | Config |
|---|---|---|---|
| Web app (`cri-web`) | Workers Static Assets | Free: requests to static assets are free and unlimited | `web/wrangler.jsonc` |
| API (`cri-api`) | Cloudflare Containers: a Worker in front of a Docker container | Workers Paid ($5/month) | `Dockerfile`, `deploy/cloudflare/api/` |

Why Containers for the API: a Python Worker cannot run it. Workers allow 10 ms of CPU
per request on the Free plan and 128 MB of memory on any plan, and the API needs
seconds of CPU to start. Containers run `cri.server` unchanged.

Alternatives (Vercel or any static host for the site; any Python host for the API)
are at the end.

## 1. Prerequisites

- A Cloudflare account. For the API, the **Workers Paid** plan. You subscribe in the
  Cloudflare dashboard; this repo cannot do it for you.
- Node.js 22 and, for the API only, **Docker running locally** (Docker Desktop on
  Windows or macOS). `wrangler deploy` builds the `linux/amd64` image locally and pushes
  it to Cloudflare.
- Log in once, interactively. In Claude Code, type `! npx wrangler login`. No API
  token goes into git.
- Choose the names first. Workers are served at
  `https://<name>.<your-account-subdomain>.workers.dev`, so the URLs are known before
  deploying: `cri-api` and `cri-web` are the names used below.

## 2. API on Cloudflare Containers

Files:
- `Dockerfile` (repo root): `python:3.12-slim` pinned by digest, non-root user,
  `pip install ".[api]"`, `uvicorn cri.server:app` on port 8080. `.dockerignore`
  keeps `data/`, `.env*`, `web/` and the rest of the repo out of the image.
- `deploy/cloudflare/api/src/index.ts`: the Worker. Class `CriApi` extends
  `Container`. Every request goes to **one named instance** (`"main"`), so the API's
  in-memory state is shared.
- `deploy/cloudflare/api/wrangler.jsonc`: the container (instance type `basic`:
  1/4 vCPU, 1 GiB memory, 4 GB disk; `max_instances: 1`), its Durable Object binding,
  and the variables below.

| Variable | Default | Meaning |
|---|---|---|
| `CRI_API_CORS_ORIGINS` | placeholder `https://cri-web.example.workers.dev` | The web app's origin(s), comma-separated. **Must be set** to the real `cri-web` URL. |
| `CRI_MODEL_BACKEND` | `rule` | Classifier backend (`rule`, `learned`, `transformer`). The image installs only `[api]`, so `transformer` is not available in it. |
| `CONTAINER_SLEEP_AFTER` | `1h` | Idle time before the container sleeps. |

Deploy:

```bash
cd deploy/cloudflare/api
npm ci
npx wrangler deploy --var CRI_API_CORS_ORIGINS:https://cri-web.<subdomain>.workers.dev
```

The first deploy is the slowest (the image is built and pushed). Cloudflare's docs warn
that calls into the container can fail for several minutes after the first deploy,
while it is provisioned. Then:

```bash
curl https://cri-api.<subdomain>.workers.dev/health
# {"status":"ok","is_synthetic":true,"source_name":"SYNTHETIC sample (seed 42)","classifier":"rule",...}
```

### Sleep, cold starts and cost

The container sleeps after `CONTAINER_SLEEP_AFTER` without requests. The next request
starts it again and waits for the API to load (a cold start). Trade-off:

- **Longer sleep time:** fewer cold starts, more billed time. Memory and disk are
  billed on the provisioned instance while it is awake.
- **Workers Paid includes** 25 GiB-hours of memory, 375 vCPU-minutes and 200 GB-hours
  of disk per month (Cloudflare Containers pricing page). Usage beyond that is billed
  per second.
- **Estimate, not a quote:** keeping one `basic` instance awake all month uses about
  730 GiB-hours of memory, which is roughly $6 per month beyond the allowance at the
  published rate, plus under $1 of disk and some CPU, on top of the $5 plan. Check the
  bill after the demo.
- **Demo day:** open `/health` a few minutes before presenting, so the container is
  awake. The review pages keep working from the snapshots even while the API sleeps.

## 3. Web app on Cloudflare (static assets)

The host only serves what you upload, so build locally with the API URL baked in:

```bash
# from the repo root, only if the analytics changed (then commit the result)
python web/scripts/export_snapshot.py   # writes web/public/data/*.synthetic.json

cd web
npm ci
NEXT_PUBLIC_API_BASE_URL=https://cri-api.<subdomain>.workers.dev npm run build
npx wrangler@4.143.0 deploy
```

PowerShell: `$env:NEXT_PUBLIC_API_BASE_URL="https://cri-api.<subdomain>.workers.dev"; npm run build`.

`web/wrangler.jsonc` has no Worker script, only assets:
- `html_handling: auto-trailing-slash` matches `trailingSlash: true` in
  `next.config.mjs`, so `/property` redirects to `/property/`;
- `not_found_handling: 404-page` serves Next's `404.html`.

Limits: 25 MiB per file and 20,000 files per version on the Free plan. The build has
fewer than 100 files; the largest is a JavaScript chunk of about 4.7 MB (Plotly),
then `cluster.synthetic.json` (about 2.5 MB).

## 4. Check it

- `https://cri-api.<subdomain>.workers.dev/health` returns `"status": "ok"`.
- Every page shows the **SYNTHETIC DATA** banner.
- `<site>/property/?property=Property%20F` opens directly (deep links) and shows
  *Fix this first* = **Food**, started around **2025-06**.
- `<site>/fix-check/?property=Property%20A&aspect=Room&month=2025-12` shows
  −1.38 plain, −0.95 market, −0.43 vs the market, *No detectable change*.
- `<site>/explore/?destination=mussoorie&start=2026-12-25&nights=2` shows **Very
  High · 87** with its factors (no "API not reachable" error).
- `<site>/explorer/` → *Try your own review* → `Khana accha tha lekin kamra ganda
  tha.` shows Food +1, Room −1, Cleanliness −1.
- CORS: `curl -sI -H "Origin: https://example.org" <api>/health` returns **no**
  `access-control-allow-origin` header.

Then record the URLs in `README.md`, `docs/DEMO.md` and `docs/TODO_RESULTS.md`
(replacing `TBD`), and fill in the measurements below.

## 5. What has been verified

On 2026-10-13, locally, without a Cloudflare account:

- **Worker:** `npm run check` (TypeScript) passes. `wrangler deploy --dry-run` accepts
  the configuration and lists the `CriApi` Durable Object binding, the variables and
  the container image `Dockerfile`.
- **Web:** `npm run build` passes, and `wrangler deploy --dry-run` reads the assets.
  Served by `wrangler dev`, pages open directly, `/property` redirects to `/property/`,
  and unknown paths return 404.
- **API:** installed exactly as the image does it (`pip install ".[api]"`, not
  editable) in a clean Python 3.12 environment and started with the image's command.
  - `/health`, `/demand/trip` (Very High · 87) and `/reviews/classify` (Food +1,
    Room −1, Cleanliness −1) answered.
  - A listed origin got `access-control-allow-origin`; an unlisted one did not.
- **End to end:** the site served by `wrangler dev` called that API across origins.
  The explore deep link rendered Very High · 87, the property page Food since
  2025-06, and the fix check −1.38 / −0.95 / −0.43 (headless Edge).
- **Not verified here:** the Docker build itself (Docker was not available on the
  machine). CI's `deploy-config` job builds the image for `linux/amd64` and checks
  `/health` inside it on every pull request.

Measurements (fill in after deploying):

| Measure | Local laptop (not Cloudflare) | Cloudflare |
|---|---|---|
| API ready after start (process start to first `/health`) | 7.0 s | `TBD` (cold start after sleep) |
| Warm `/demand/trip` round trip | about 0.21 s | `TBD` |
| Monthly Cloudflare cost | — | `TBD` |

## 6. Alternatives

### Web app on Vercel or another static host

1. On <https://vercel.com>, **Add New → Project** and import
   `PxA-Labs/cluster-review-intelligence`.
2. **Root Directory: `web`.** Framework preset: Next.js (detected). Leave the build
   command and output at their defaults. Environment variable:
   `NEXT_PUBLIC_API_BASE_URL` = the API's public URL.
3. **Deploy.** Every push to `main` then redeploys, and pull requests get preview URLs.

Check Vercel's plan terms for your use; the free Hobby plan is meant for
non-commercial use. **Other static hosts** (Netlify, Cloudflare Pages): build command
`npm run build`, base directory `web`, publish directory `web/out`. GitHub Pages serves
a project site under `/<repo>/`, which needs `basePath` in `next.config.mjs` first (the
data URLs are root-relative).

### API on any Python or Docker host

Any host that runs a long-lived web process (for example Render, Railway, Fly.io, a
small VM) or a Docker image built from `Dockerfile`.

- Python **3.12** (the pinned `numpy==1.26.2` has no Python 3.13 wheels).
- Install: `pip install ".[api]"` from the repo root.
- Start: `uvicorn cri.server:app --host 0.0.0.0 --port $PORT`.
- Environment: `CRI_API_CORS_ORIGINS=https://<your-site>` (comma-separate several).
  Optional `CRI_MODEL_BACKEND` (default `rule`).
- Health check: `GET /health`.
- Free tiers that sleep when idle (for example Render's) add a wake-up delay to the
  first request after a quiet period.

## Never on the public app

- **No real review data.** Snapshots and the API use the SYNTHETIC sample; real
  partner data and anything under `data/raw/` (gitignored, and excluded from the
  Docker image) stay on team machines (CLAUDE.md rules 3-4). The locally trained
  hill-review model is never deployed.
- No secrets in the repo or the host settings (none are needed). Wrangler logs in
  interactively; do not commit API tokens or `.dev.vars` files.

## Plan B / Plan C on demo day

- **Local:** `uvicorn cri.server:app --port 8000`, then
  `cd web && npm run build && python -m http.server 3000 --directory out`
  (port 3000 matches the API's default CORS origin).
- **Video:** the backup demo recording (HACKATHON_PLAN.md, H+18).
