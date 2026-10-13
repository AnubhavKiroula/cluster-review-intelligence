# CONTEXT

Living project state. Update at meaningful milestones.

## What is being built

**G5 "Cluster Review Intelligence & Competitive Benchmarking"** (AI–Tourism
Hackathon 2026) turns a tourism cluster's reviews into aspect-level, competitive,
time-aware intelligence, and separates market-wide issues from property-specific
ones.

Since 2026-10-13 the same review evidence also drives a **travel-intelligence layer**
for Uttarakhand and Himachal hill destinations:

- a holiday-aware demand index;
- crowd-aware alternatives with a capacity guard;
- star-free stay profiles and provider insights;
- local sellers;
- a budget trip planner;
- a tourism-board region view.

Repo: `PxA-Labs/cluster-review-intelligence`.

Team: Anubhav (analytics core), Purvansh (web), Archit (data, eval, ops). The plan
and ownership map are in `docs/HACKATHON_PLAN.md`.

## Current objective

Merge `feat/anubhav-travel-intelligence`. It is stacked on PR #31, so #31 merges
first. Then:

- deploy the static site and the API;
- label a clause-level gold set;
- rehearse `docs/DEMO_SCRIPT.md`.

## Architecture / state

| Layer | Contents |
|---|---|
| `src/cri/` review core | schema → loader / sources → normalize → classify (`rule` default; `learned`, `transformer` opt-in) → pipeline → benchmark / changepoint → insights / intervention → **`api.py`** |
| `src/cri/travel/` | `data`, `demand`, `alternatives`, `stays`, `region`, `planner`, on `resources/travel_facts.yaml` (sourced) and `resources/travel_synthetic.yaml` (SYNTHETIC) |
| `src/cri/server.py` | FastAPI over both |
| `web/` | Next.js static export, the **only UI**. G5 pages read `public/data/*.synthetic.json`; the travel pages and live classify call the API (`NEXT_PUBLIC_API_BASE_URL`). |

Streamlit (`app/`) was removed on 2026-10-13. No database.

## Completed (implemented + verified)

- **G5 build:** MVP and the Day-1 integration (#14–#18, #24); the Next.js frontend
  (#25, #26); "Did my fix work?" (#28, plus the web page in #31).
- **2026-10-13, this branch:**
  - repo moved to PxA-Labs;
  - travel layer, API and four web pages;
  - live classify in the explorer;
  - Streamlit removed;
  - CI web job;
  - learned sentiment backend: the open model is shipped, the hill-review model is
    local;
  - the nine product docs: PRD, SRS, SYSTEM_DESIGN, AI_MODEL, BUSINESS_MODEL,
    DATA_SOURCES, API_CONTRACTS, IMPLEMENTATION_PLAN, DEMO_SCRIPT.

## Verified (2026-10-13, local, Python 3.12.10, Node 22)

- **Python:** `python -m pytest` gives 297 passed, 2 skipped (opt-in real-model tests).
  `python -m ruff check .` is clean.
- **Web:** `npx tsc --noEmit` is clean. `npm run build` produces 14 static routes.
- **Headless browser:** with the API running, headless Edge (Playwright, one-off) loaded
  every G5 and travel page. There were no error states and no console errors. The trip
  planner and live classify both work. Screenshots are in `docs/screenshots/`.
- **Learned model** (held-out, document-level macro-F1):

  | Test set | `open` | `region` | Rules |
  |---|---|---|---|
  | SentiMix Hinglish tweets | 0.663 | — | 0.361 |
  | Hill hotel reviews (hotel-grouped) | — | 0.687 | 0.557 |

  On the SYNTHETIC clause-level patterns the models trail the rules: food decline
  found in 5/20 and 4/20 seeds, against 15/20 for the rules. **Rules stay the
  default.** Full results are in `docs/AI_MODEL.md`.
- **Facts:** every fact in `travel_facts.yaml` was read from its cited source on
  2026-10-13, and holiday weekdays are checked on load.
- **Not verified:** deployment of either piece (needs accounts); CI on the PR (runs
  on push).

## Next tasks

1. Merge #31, then this PR. Watch the first CI run of the new web job.
2. Deploy the static site (Vercel; set `NEXT_PUBLIC_API_BASE_URL`) and the API (set
   `CRI_API_CORS_ORIGINS`). Record the URLs.
3. Label about 300 hill-destination clauses (two annotators) and score rules vs
   learned at clause level.
4. Get monthly arrivals or partner occupancy to validate the demand index.
5. Rehearse `docs/DEMO_SCRIPT.md` and record the backup video.

## Important decisions

- **Review statistics** (unchanged):
  - The statistical unit is (review, aspect).
  - FDR q = 0.05.
  - Effect floors: 0.4 for a property change, 0.3 for market participation.
  - "Market-wide" needs ≥ 60% of properties.
- **Platform:** Next.js + FastAPI, with Streamlit removed (reversal of HACKATHON_PLAN
  §1, recorded there). The G5 pages keep the static snapshot, so they work without
  the API.
- **Provenance:** every travel number is an `Evidence` with a basis (fact / measured
  / derived / synthetic / assumption). Synthetic and sourced data live in separate
  files.
- **Demand index:** a transparent points model, not trained, because no footfall data
  exists. It is never called live traffic.
- **Capacity guard:** uses assumed ceilings (90/80/70 by sensitivity). No official
  carrying capacity exists.
- **Learned backend:**
  - It is opt-in. The default changes only if it wins on a clause-level gold set.
  - The CC BY model is shipped as a no-pickle `.npz`.
  - The model trained on Kaggle hill reviews stays local, because of their provenance.
- **Hill filter for training:** the plains districts Haridwar and Udham Singh Nagar
  are dropped. Splits are grouped by hotel.

## Known issues / honest caveats

- **SYNTHETIC data:** the review data and all stays, prices and sellers are
  SYNTHETIC. Real-data accuracy at clause level is `TBD`.
- **Calendar coverage:** state holidays are not included, and school windows are
  assumptions.
- **Distance estimates:** they underestimate short hill hops (factor 1.46, derived
  from 14 official pairs).
- **Calibration CLI:** `python -m cri.calibration` always uses the rules. To calibrate
  another backend, pass `classifier=get_classifier(...)` (see `docs/AI_MODEL.md`).
- **Authentication:** none. The app is not ready for real provider data.

## Commands

| Task | Command |
|---|---|
| Install | `pip install -e ".[dev,api]"` |
| Test and lint | `pytest` · `ruff check .` |
| Run the API | `uvicorn cri.server:app --port 8000` |
| Run the web app | `cd web && npm ci && npm run dev` |
| Check the web app | `npx tsc --noEmit` · `npm run build` |
| G5 demo and calibration | `python scripts/demo.py` · `python -m cri.calibration --seeds 1-20` |
| Re-export the snapshot | `python web/scripts/export_snapshot.py` |
| Train (needs `pip install -e ".[train]"`) | `python scripts/prepare_region_reviews.py` · `python scripts/train_sentiment.py --model open\|region` |
| Screenshots | `python scripts/capture_screenshots.py` |
