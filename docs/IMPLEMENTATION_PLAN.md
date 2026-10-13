# Implementation plan and status

Status as of 2026-10-13, branch `feat/focus-one-question` (from `main` at `56aaa79`).

## The cut (2026-10-13)

Mentors found the pitch unfocused: it served travellers, hotels, tourism boards and
local sellers at once. The product was cut to **one payer, the hotel or homestay
owner**, and **one question**: when a property's reviews get worse on some aspect,
is that this property's problem or the whole market's? Only the cluster can answer
it.

| Removed | Kept |
|---|---|
| Travel layer `cri.travel` (demand index, alternatives, stays, sellers, planner, region) and its two resource files | Review core: ingestion, classifiers, benchmark, changepoints, market scope, priorities, fix check |
| Pages `/explore /plan /provider /region /destination /cluster` | Pages `/property /market /fix-check /explorer` (plus home) |
| Travel API routes | API: `/health` and `POST /reviews/classify` (the explorer's live classify) |

Everything removed is recoverable from the git tag `travel-layer-v1`.

## Roadmap and status

| Priority | Item | Status |
|---|---|---|
| P0 | `priority_actions.whose_problem` / `whose_detail`, derived per property | ✅ done + tests |
| P0 | `/property` leads with "Fix X first since …" and a Whose problem column | ✅ done |
| P0 | `/market` names the worst market-wide aspect (from the old `/destination`) | ✅ done |
| P0 | Routes 11 → 4; nav active-link fix; home rewritten | ✅ done; build passes |
| P0 | Travel backend and travel API removed | ✅ done |
| P0 | README and one 3-minute demo (`docs/DEMO.md`), every number test-pinned | ✅ done |
| P1 | Learned sentiment model (open data, shipped; hill reviews, local) | ✅ done; opt-in, measured (AI_MODEL.md) |
| P1 | Deploy: static site + API host | ⏳ needs accounts; URLs `TBD` |
| P1 | Clause-level gold set (~300 hill-destination clauses) and real accuracy | ⏳ `TBD`, needs people to label |
| P1 | GPU fine-tuned transformer on the same splits | ⏳ not started |
| P2 | Real, dated review export from one cluster; validate "whose problem" with owners | roadmap |
| P2 | Accounts, database and verification before any real property data | roadmap |

## Verification

- **Python:** `python -m pytest` and `python -m ruff check .`. Results are in the PR
  description and `CONTEXT.md`.
- **Web:** `npx tsc --noEmit` and `npm run build` (static export).
- **Demo:** `python scripts/demo.py` prints every number `docs/DEMO.md` quotes;
  `tests/test_demo.py` and `tests/test_intervention.py` pin them.
- **ML:** `scripts/prepare_region_reviews.py` then
  `scripts/train_sentiment.py --model open|region`; metrics are pasted into
  AI_MODEL.md from the generated metrics JSON.

## Critical dependencies

| Dependency | Why it matters |
|---|---|
| API reachable from the static site | Only for live classify: `NEXT_PUBLIC_API_BASE_URL` at build time and the site's origin in `CRI_API_CORS_ORIGINS` |
| Kaggle hill-review dataset (local) | Only for re-training the local region model; not needed to run the app |

## Known limitations

- All review data is SYNTHETIC; "whose problem" is validated on SYNTHETIC data only.
- The learned sentiment models are trained on whole texts. Clause-level accuracy is
  `TBD`, and the default stays `rule`.
- No authentication, so not ready for real property data.

## Recommended next steps

1. **Label the gold set** (two annotators, kappa) and evaluate rules vs learned at
   the clause level.
2. **Get one real dated review export** from a partner cluster and run the analytics
   on it.
3. **Pilot with 10–15 homestays** in one belt. Measure whether owners agree with the
   "whose problem" verdicts and act on them, and use the fix check.
4. **Deploy** the static site (and the API for live classify); record the URLs.
5. **Add accounts, a database and verification** before any real property data.
