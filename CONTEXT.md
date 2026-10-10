# CONTEXT

Living project state. Update at meaningful milestones.

## What is being built
G5 "Cluster Review Intelligence & Competitive Benchmarking": turn a tourism
cluster's reviews into aspect-level, competitive, time-aware intelligence, and
separate market-wide issues from property-specific ones. AI–Tourism Hackathon 2026.
Team: Anubhav (analytics core), Purvansh (dashboard), Archit (data, eval, ops):
see `docs/HACKATHON_PLAN.md` for the plan and file-ownership map.

## Current objective
Analytics core done; the dashboard (Purvansh) builds against `src/cri/api.py`.

## Architecture / state
`src/cri/`: schema → loader (PII dropped) → normalize → classify (rules by default,
optional transformer via `CRI_MODEL_BACKEND`) → pipeline (mentions with
`review_id`) → benchmark (review-level bootstrap CIs; "is it me?" changepoints vs
the leave-one-out market; "is it the market?" seasonal/step patterns across
properties; scope) → insights (priority actions, destination view) → **api.py**
(the facade the dashboard imports). Config: `aspects.yaml`, `lexicon.yaml`.
`python -m cri.calibration` reproduces every detector number in the docs.

## Completed (implemented + verified)
- MVP (Phases 0–3, 6–7): scaffold, synthetic generator, rule classifier, README.
- Anubhav's Day-0/Day-1 track (branch `feat/anubhav-analytics-core`):
  - `api.py` contract and `lexicon.yaml` extraction (byte-identical output);
  - bootstrap CIs, significance-tested detectors, market-wide patterns,
    `undetermined` scope for small clusters;
  - `priority_actions`, `destination_summary`, calibration module;
  - optional transformer backend (built and tested; see the known issues below).

## Verified
- Tests: 148 pass, 2 skipped (opt-in real-model tests; they pass with the model
  installed) on pandas 2.1.3/numpy 1.26 AND pandas 3.0.6/numpy 2.4.6 (warnings
  as errors). Every commit on the branch passes on its own.
- SYNTHETIC calibration (`--seeds 1-20`): food decline found 15/20, Room-December
  market-wide 20/20, pattern-free seeds with any false alarm 1/20 (was 20/20).
- Fresh null seeds 21–120: property changepoint false alarms 5/100 (nominal 5%);
  market patterns 0/100. Lead/lag: 0.11 false flags per null cluster (was ~2.8).
- A five-lens adversarial review (statistics, contract, edge cases, pandas 3,
  quality) confirmed 10 problems; all fixed, each with a regression test.
- Every `api` call < 300 ms on the 5,124-review sample; `load_cluster` ≈ 1.8 s.

## Next tasks
1. Purvansh: build the dashboard on `api.py` (handle scope `undetermined`/`stable`,
   `started`/`change_month` may be missing).
2. Archit: real-data sourcing + eval harness; act on the flagged items in the PR
   (schema blank-text bug, merge numpy 2 and pandas 3 Dependabot PRs together).
3. Hackathon: tune on real data; re-run calibration if thresholds change.

## Important decisions
- Statistical unit = (review, aspect); FDR q = 0.05; effect floors 0.4 (property
  change) and 0.3 (market participation); market-wide needs ≥ 60% of properties.
- Market reference = other properties' deviations from their own levels (robust
  to hotels entering/leaving the data); lead/lag flags FDR-controlled.
- Seasonality tested for all 12 months, within each year, must recur every year.
- Ingestion normalised in `api.load_cluster`: ids → text, tz dates → Asia/Kolkata.
- Transformer backend is opt-in, NOT default (measured weaker on Hinglish).
- PELT not implemented (penalty cannot be calibrated without real data).

## Known issues / honest caveats
- Validation is SYNTHETIC only; real-data accuracy is `TBD`.
- Flagged to Archit (his files): `schema.py` blank text / mixed-offset dates on
  pandas 3, duplicate reviews across overlapping exports, numpy 2 + pandas 3
  Dependabot PRs must merge together.
- Detector recall is limited by sample size (15/20); thresholds not loosened.
- The pinned transformer model misreads Hinglish negatives and some English
  out-of-lexicon words; it does not recover the injected decline end-to-end.

## Commands
`pip install -e ".[dev]"` · `pytest` · `ruff check .` · `python scripts/demo.py` ·
`python scripts/make_figures.py` · `python -m cri.calibration --seeds 1-20` ·
optional: `pip install -e ".[model]"` then `CRI_MODEL_BACKEND=transformer`.
