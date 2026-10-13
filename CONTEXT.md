# CONTEXT

Living project state. Update at meaningful milestones.

## What is being built

**G5 "Cluster Review Intelligence & Competitive Benchmarking"** (AI–Tourism
Hackathon 2026), for **one user: the hotel or homestay owner**. It answers one
question, before a fix and after it: *when my reviews get worse on some aspect, is it
my problem or the whole market's?* Only the cluster can answer that; one hotel's own
reviews cannot. That is the moat.

**Positioning:** MakeMyTrip, Goibibo and Booking.com are demand side (they help a
traveller find a hotel). We are supply side: we sell to the properties listed on those
platforms and do not compete with them. The same analysis also gives a tourism board a
destination view (one line in the pitch, not a second product).

**Real market (since 2026-10-13, PR `feat/real-kausani-cluster`):** home, `/property`
and `/market` show **Kausani** (Bageshwar, Uttarakhand): 25 real hotels, 2,751 real
reviews from the Kaggle hill corpus, anonymised (Property A–Y) and published as
aggregates only. The corpus has **no review dates**, so the time axis is a labelled
SYNTHETIC method demo (`?source=demo`, `/fix-check`).

Repo: `PxA-Labs/cluster-review-intelligence`. Team **The Imposters**: Archit Mittal
(team lead; data, eval, ops), Purvansh Joshi (web), Anubhav Kiroula (analytics core). Plan and ownership map:
`docs/HACKATHON_PLAN.md`.

## The focus cut (2026-10-13)

- **Why:** mentors said the USP was unfocused. We were building for travellers,
  hotels, tourism boards and local sellers at once.
- **What went:**
  - the travel layer (`cri.travel`: demand index, alternatives, stays, sellers,
    planner, region view) and its two resource files;
  - its 9 API routes and `/meta`;
  - six web routes (`/plan`, `/explore`, `/region`, `/provider`, `/destination`,
    `/cluster`).
- **Where it is:** everything is recoverable at the git tag **`travel-layer-v1`**
  (commit `56aaa79`, main before the cut). That tag also answers "what else could
  this do?"
- **What was added:** `priority_actions.whose_problem` (`yours alone` | `everyone's`
  | `not tested`) with `whose_detail`, shown on `/property`. It is derived per
  property, never joined from `market_scope` by aspect.
- **Branch / PR:** `feat/focus-one-question` (#41, merged).

## Current objective

Submit tonight:

- merge the real-cluster PR (`feat/real-kausani-cluster`; it needs explicit
  maintainer approval) and redeploy;
- rehearse `docs/DEMO.md` (now built around Kausani).

After that, label a clause-level gold set from Kausani reviews.

## Architecture / state

| Layer | Contents |
|---|---|
| `src/cri/` review core | schema → loader / sources → normalize → classify (`rule` default; `learned`, `transformer` opt-in) → pipeline → benchmark / changepoint → insights (priorities + whose problem) / intervention → **`api.py`** |
| `src/cri/server.py` | FastAPI, only `/health` and `POST /reviews/classify` (the explorer's live classify). Loads no data at startup. |
| `web/` | Next.js static export, the only UI: `/property`, `/market`, `/fix-check`, `/explorer` plus home. Home, property and market read `public/data/cluster.real.json` (real Kausani aggregates); the method demo, fix check and explorer texts read `*.synthetic.json`. A provenance chip on every page says which. Only live classify calls the API. |
| Real data path (local only) | Kaggle hill reviews → `scripts/prepare_region_reviews.py` → `scripts/prepare_real_cluster.py --town Kausani` → `web/scripts/export_snapshot.py` → `cluster.real.json`. Inputs and the hotel-name map stay under the gitignored `data/raw/external/`. |

No database. Streamlit was removed earlier the same day.

## Completed (implemented + verified)

- **G5 build:** MVP, the Day-1 integration, the Next.js frontend, and "Did my fix
  work?" (#14–#18, #24–#26, #28, #31).
- **Before the cut (2026-10-13):**
  - the travel layer, API and learned sentiment backend (#32, now tagged);
  - the professional README (#39).
- **The focus cut, this branch:**
  - A: `whose_problem` plus the `/property` card and column;
  - D: `/market` names the worst market-wide aspect (`market_headline` in the
    snapshot);
  - B: 4 routes, an exact-match nav fix, home rebuilt;
  - C: the travel backend deleted;
  - E: README and the single 3-minute demo `docs/DEMO.md`;
  - F: the docs moved to the single user;
  - plus the fix "`not tested` below 3 properties".

## Verified (2026-10-13, local, Python 3.12.10, Node 22)

- **Python checks:**
  - `python -m pytest`: 289 passed, 2 skipped (opt-in real-model tests), on the real-cluster branch.
  - `python -m ruff check .`: clean.
- **Calibration:** `python -m cri.calibration --seeds 1-20` reproduces the documented
  numbers:
  - food decline 15/20 (0.53–0.89);
  - December Room market-wide 20/20 (0.84–1.00);
  - null seeds with any false alarm 1/20.
- **Web build:** `npm run build` gives home plus the 4 routes.
- **Headless Edge walk:**
  - every kept page renders, with one active nav link;
  - removed routes return 404, and there are no dead internal links;
  - every number in `docs/DEMO.md` is on screen;
  - live classify works.

  The only console error is `/favicon.ico` 404, which already happens on `main`.
- **Not verified:** deployment (needs accounts). `whose_problem` on real clusters is
  `TBD`.

## Next tasks

1. Get approval for the focus-cut PR and merge it.
2. PR #40 (Cloudflare deploy) must be rebased onto this. Its docs cite
   `/demand/trip`, which is gone, and its `/health` example still shows
   `is_synthetic`.
3. Deploy the static site (it is the whole product); the API is optional.
4. Label about 300 hill-destination clauses (two annotators). Score rules vs learned
   at clause level.
5. Pilot with real owners: do they agree with the `whose_problem` verdicts?

## Important decisions

- **Review statistics** (unchanged):
  - the unit is (review, aspect);
  - FDR q = 0.05;
  - effect floors: 0.4 for a property change, 0.3 for market participation;
  - "market-wide" needs ≥ 60% of properties.
- **`whose_problem`:**
  - A market-adjusted decline is `yours alone`.
  - A lag is re-tested with the market-wide patterns the property takes part in set
    aside. It is `everyone's` only if the lag disappears.
  - Below 3 properties it is `not tested`.
  - Why not join `market_scope`: Property D's Room gap is real outside December
    (still 0.36 below the market), so labelling it `everyone's` would be false.
- **Platform:** Next.js static export plus a small FastAPI service, used only for live
  classify.
- **Learned backend:** opt-in. Rules stay the default until a clause-level gold set
  says otherwise. The Kaggle-trained `region` model stays local.

- **Real cluster (2026-10-13):**
  - Kausani was chosen for cluster density: 41 hotels and 2,877 reviews in town, 16
    hotels with ≥ 50 reviews. The runner-up was Lansdowne (36 hotels, 1,972 reviews).
  - A hotel joins with ≥ 20 reviews (2 × `MIN_REVIEWS_FOR_FLAG`), giving 25 hotels
    and 2,751 reviews.
  - Dates are never invented. Without them, scope is level-based only: lag flags,
    plus `shared_weak_spots` on complaint share (not mean sentiment, because neutral
    check-in mentions made Booking Experience look weak).
  - Aggregates are published; review text, clause text and hotel names never are.

## Known issues / honest caveats

- The review data is SYNTHETIC. Clause-level accuracy on real data is `TBD`.
- Every `whose_problem` validation so far is SYNTHETIC (`tests/test_insights.py`).
- The `everyone's` re-test reuses the lag test on a subset. It is not a separate FDR
  family.
- `python -m cri.calibration` always uses the rules (pass `classifier=` to calibrate
  another backend).
- There is no authentication, so the app is not ready for real owner data.
- **Kausani results:**
  - There is no shared weak spot, so the "market opportunity" framing shows only on
    the method demo.
  - The 9 lags depend on the inclusion rule: 4 remain at ≥ 30 reviews per hotel.
- **Hinglish is near zero in the real corpus:** 4 of 2,877 Kausani reviews and 80 of
  80,827 overall. The Hinglish claim rests on the classifier and the public test
  sets.
- **Licence:** the corpus is TripAdvisor-derived, so we publish derived statistics
  only. No legal review of that position has been done.

## Commands

| Task | Command |
|---|---|
| Install | `pip install -e ".[dev,api]"` |
| Test and lint | `pytest` · `ruff check .` |
| Web app | `cd web && npm ci && npm run dev` |
| Live classify API (optional) | `uvicorn cri.server:app --port 8000` |
| Check the web app | `npx tsc --noEmit` · `npm run build` |
| Demo numbers and calibration | `python scripts/demo.py` · `python -m cri.calibration --seeds 1-20` |
| Re-export the snapshot | `python web/scripts/export_snapshot.py` (`--skip-fix-check` skips the slow grid) |
| Train (needs `pip install -e ".[train]"`) | `python scripts/prepare_region_reviews.py` · `python scripts/train_sentiment.py --model open\|region` |
| Screenshots | `python scripts/capture_screenshots.py` |
| Rebuild the real cluster (needs the local Kaggle data) | `python scripts/prepare_region_reviews.py` · `python scripts/prepare_real_cluster.py --town Kausani` · `python web/scripts/export_snapshot.py --skip-fix-check` |
| Recover the travel layer | `git checkout travel-layer-v1 -- <path>` |
