# Implementation plan and status

Branch `feat/anubhav-travel-intelligence` builds on PR #31 ("Did my fix work?" on
the web) and on `main` at `8b8dffe`. Status as of 2026-10-13.

## Roadmap and status

| Priority | Item | Status |
|---|---|---|
| P0 | Repo moved to `PxA-Labs/cluster-review-intelligence`; local `main` synced | ✅ done |
| P0 | Sourced facts: gazetted holidays 2026–27, coordinates, official distances, UTDB arrivals, emission factors | ✅ done (`travel_facts.yaml`) |
| P0 | SYNTHETIC profiles: destinations, stays for Properties A–L, sellers, costs | ✅ done (`travel_synthetic.yaml`) |
| P0 | Demand index, long weekends, quieter dates, overview | ✅ done + tests |
| P0 | Crowd-aware alternatives with capacity guard and explanations | ✅ done + tests |
| P0 | Star-free stay profiles and provider insights | ✅ done + tests |
| P0 | Local sellers + opportunity; tourism-board region view | ✅ done + tests |
| P0 | Trip planner with traced costs, carbon, variants | ✅ done + tests |
| P0 | FastAPI service (`cri.server`) | ✅ done + tests |
| P0 | Next.js pages `/explore /plan /provider /region`; live classify in the explorer | ✅ done; type-check, build and headless-browser run pass |
| P0 | Remove Streamlit (after porting its unique features) | ✅ done |
| P0 | CI: Python (`.[dev,api]`) + web job (tsc + build) | ✅ configured; runs on the PR |
| P0 | Docs: PRD, SRS, SYSTEM_DESIGN, AI_MODEL, BUSINESS_MODEL, DATA_SOURCES, API_CONTRACTS, this plan, DEMO_SCRIPT; README and others updated | ✅ done |
| P1 | Learned sentiment model (open data, shipped; hill reviews, local) | ✅ done; opt-in, measured (AI_MODEL.md) |
| P1 | Web screenshots captured from the real app | ✅ done (`docs/screenshots/`) |
| P1 | Deploy: static site (Vercel/Netlify) + API host | ⏳ needs accounts; URLs `TBD` |
| P1 | Clause-level gold set (~300 hill-destination clauses) and real accuracy | ⏳ `TBD`, needs people to label |
| P1 | GPU fine-tuned transformer on the same splits | ⏳ not started |
| P2 | Real provider and seller onboarding with verification; database; authentication | roadmap |
| P2 | Monthly arrivals or occupancy to validate or train the demand model | roadmap |
| P2 | Weather and road-status integrations (labelled live only when live) | roadmap |
| P2 | Booking/referral with real inventory | roadmap |

## Verification performed

- **Python:** `python -m pytest` and `python -m ruff check .`. Results are in the PR
  description and `CONTEXT.md`.
- **Web:** `npx tsc --noEmit` and `npm run build` (static export, 14 routes).
- **End to end:** API (`uvicorn cri.server:app`) plus the built site, driven with
  headless Edge (Playwright, a one-off tool).
  - Checked: all travel and G5 pages render with data, with no error states and no
    console errors.
  - Checked: planning a trip returns a result.
  - Checked: classifying the Hinglish demo sentence returns Food +1, Room −1,
    Cleanliness −1.
  - `scripts/capture_screenshots.py` reproduces the screenshots.
- **ML:** `scripts/prepare_region_reviews.py` then
  `scripts/train_sentiment.py --model open|region`.
  - Metrics are pasted into AI_MODEL.md from the generated metrics JSON.
  - 20-seed calibration was run with each learned model.

## Critical dependencies

| Dependency | Why it matters |
|---|---|
| PR #31 merged before or with this PR | This branch is stacked on it (fix-check page, root-relative data URLs) |
| API reachable from the static site | Travel pages need `NEXT_PUBLIC_API_BASE_URL` at build time and the site's origin in `CRI_API_CORS_ORIGINS` |
| Kaggle hill-review dataset (local) | Only for re-training the local region model; not needed to run the app |

## Known limitations

- Demand is a heuristic on assumed weights and season curves. There is no validation
  data.
- State holidays are not included; school windows are assumptions.
- Capacity ceilings are assumptions. No official carrying capacity exists.
- Stays, prices and sellers are SYNTHETIC. Amenities and practices are
  self-reported.
- Estimated road distances underestimate short hill hops.
- The learned sentiment models are trained on whole texts. Clause-level accuracy is
  `TBD`, and the default stays `rule`.
- No authentication, so not ready for real provider data.

## Recommended next steps after the hackathon

1. **Label the gold set** (two annotators, kappa) and evaluate rules vs learned at
   the clause level.
2. **Get one real dated review export** from a partner cluster and run the G5
   analytics on it.
3. **Pilot with 10–15 homestays** in one belt. Measure whether insights are acted
   on, and use the fix check.
4. **Obtain monthly arrivals** (UTDB / HP Tourism) and run the demand-index
   validation plan.
5. **Add accounts, a database and verification** before any real provider or seller
   data.
