# CONTEXT

Living project state. Update at meaningful milestones.

## What is being built
G5 "Cluster Review Intelligence & Competitive Benchmarking": turn a tourism
cluster's reviews into aspect-level, competitive, time-aware intelligence, and
separate market-wide issues from property-specific ones. AI–Tourism Hackathon 2026.
Team: Anubhav (analytics core), Purvansh (dashboard), Archit (data, eval, ops):
see `docs/HACKATHON_PLAN.md` for the plan and file-ownership map.

## Current objective
Day-1 integration merged (#18, review follow-ups #19): the dashboard runs end to end on
SYNTHETIC data on the pinned stack, the demo is scripted with true numbers, and the
eval harness can score the shipped classifier. Next: deploy, real data, labelling.

## Architecture / state
`src/cri/`: schema (dates → naive Asia/Kolkata) → loader (PII dropped; cross-file
repeats dropped with a warning) / sources (aliases or YAML mapping) → normalize
(clauses split on punctuation, aur/or and contrastive conjunctions) → classify
(rules by default, optional transformer via `CRI_MODEL_BACKEND`) → pipeline →
benchmark (bootstrap CIs; "is it me?" vs the leave-one-out market; "is it the
market?" across properties) → insights → **api.py** (the only module `app/`
imports). `app/`: Streamlit, 5 pages. `eval/`: predict.py → score.py.

## Completed (implemented + verified)
- MVP; Anubhav's analytics core (PR #14); Purvansh's dashboard (PR #15); Archit's
  eval/sources/schema (PR #16) and labelling pack (PR #17, brought to main here:
  it had merged into its stacked base branch, not main).
- Day-1 integration (this branch): ingestion date/duplicate/alias fixes; eval
  predict + sentiment metrics; dashboard fixed on the pinned stack (pyarrow pin,
  plotly datetime crash on Property F, invisible quadrant guides, honest labels,
  caching); "Try your own review"; contrastive-clause splitting; demo pack;
  CodeQL; CI runs the dashboard; Streamlit Cloud prep; screenshots.

## Verified
- Pinned stack + dashboard extra (= CI): 241 passed, 2 skipped (opt-in real-model
  tests). pandas 3.0.6 / numpy 2.4.6, warnings as errors: 225 passed (all but the
  dashboard tests, whose pinned streamlit needs pandas<3). ruff clean.
- Independent review of #18 found 2 regressions (day/month guessing, missed
  cross-file repeats) and 4 risks; all fixed with regression tests (#19).
- Every dashboard page runs headlessly (AppTest), Property page for all 12
  properties; no zero-width chart lines.
- Fresh clone, clean Python 3.12: `pip install -r requirements.txt` and `uv pip
  install -r requirements.txt` both work; `streamlit run app/Home.py` health `ok`.
- SYNTHETIC calibration (`--seeds 1-20`) reproduces the documented numbers exactly
  after the classifier change (food decline 15/20, Room-December 20/20, null
  seeds with any false alarm 1/20). Rules vs transformer probes unchanged
  (4/12 vs 4/12; templates 33/36 vs 26/36).

## Next tasks
1. Deploy to Streamlit Community Cloud from `main` (docs/DEPLOYMENT.md; needs a
   GitHub login), record the URL.
2. Enable branch protection on `main` (repo admin; docs/hardening.md).
3. Real data (legitimate sources only, §8 of the plan) and the labelling sprint;
   run `eval/predict.py` + `eval/score.py`; replace `TBD`s with measured values.
4. Demo rehearsal with `docs/DEMO.md`; record the backup video.

## Important decisions
- Statistical unit = (review, aspect); FDR q = 0.05; effect floors 0.4 (property
  change) and 0.3 (market participation); market-wide needs ≥ 60% of properties.
- Dates: naive = local time, kept as written; offsets converted to Asia/Kolkata
  (in the schema, once).
- Clauses split on contrastive conjunctions (not on "par", which also means "on").
- Eval scores only human-labelled rows (blank gold = not labelled; `none` = no
  aspect); sentiment metrics on aspects both sides found.
- Dependency stack kept at pandas 2.1.3 / numpy 1.26.2 / streamlit 1.41.1 /
  pyarrow 25.0.1 through the hackathon; Dependabot groups them for later.
- Transformer backend is opt-in, NOT default (measured weaker on Hinglish).
- PELT not implemented (penalty cannot be calibrated without real data).

## Known issues / honest caveats
- Validation is SYNTHETIC only; real-data accuracy is `TBD`.
- Rule baseline misses Hindi post-negation ("accha nahi"), sarcasm and
  out-of-lexicon words (see docs/DEMO.md "do not type these live").
- Detector recall is limited by sample size (15/20); thresholds not loosened.
- Streamlit Cloud acceptance of `.[dashboard]` in requirements.txt is unverified
  until the first deploy (fallback documented).

## Commands
`pip install -e ".[dev,dashboard]"` · `pytest` · `ruff check .` ·
`streamlit run app/Home.py` · `python scripts/demo.py` ·
`python -m cri.calibration --seeds 1-20` · `python eval/predict.py …` ·
`python eval/score.py …` · optional: `pip install -e ".[model]"`.
