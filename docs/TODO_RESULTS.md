# TODO / Results tracker

Every unknown value in this repo is listed here as `TBD`. **No placeholder number
is ever presented as a real measured result** (see `CLAUDE.md` rule 1). When a
real number exists, update it here *and* wherever it is cited.

## Evaluation metrics (need real labelled data)

These require the team to hand-label a set of **real** reviews using
[`docs/labelling_template.csv`](labelling_template.csv). Until then: `TBD`.

| Metric                                   | Baseline (rules) | Model backend | Status |
|------------------------------------------|------------------|---------------|--------|
| Aspect detection — macro precision       | TBD              | TBD           | TBD    |
| Aspect detection — macro recall          | TBD              | TBD           | TBD    |
| Aspect detection — macro F1              | TBD              | TBD           | TBD    |
| Sentiment — macro F1                     | TBD              | TBD           | TBD    |
| Per-aspect F1 (Food/Room/…)              | TBD              | TBD           | TBD    |
| Confusion matrix                         | TBD              | TBD           | TBD    |
| Error analysis (sarcasm, mixed, short)   | TBD              | TBD           | TBD    |
| Labelled set size (reviews)              | TBD              | —             | TBD    |
| Inter-annotator agreement                | TBD              | —             | TBD    |

## Pattern recovery on SYNTHETIC data (reproducible, not a real-world metric)

These are **not** accuracy claims about real reviews — they describe recovery of
patterns the generator injected on purpose, and silence on pattern-free data.
Reproduce with `python -m cri.calibration --seeds 1-20` (details: methodology §10).

| Measure (20 SYNTHETIC seeds)              | Result | Wilson 95% CI | Note |
|-------------------------------------------|--------|---------------|------|
| Property F food decline found (±1 month)  | 15/20  | 0.53–0.89     | misses are seeds whose injected drop is small |
| Room-December found market-wide           | 20/20  | 0.84–1.00     | |
| Pattern-free seeds with any false alarm   | 1/20   | —             | previous fixed-threshold detectors: 20/20 |
| Extra changepoints per injected seed      | 0.10   | —             | FDR (not FWER) control; see methodology §11 |

## "Did my fix work?" check (SYNTHETIC simulations, reproducible)

Reproduce with `python scripts/calibrate_intervention.py` (details: methodology §12).
Simulated 6-property clusters; "naive" = plain before/after on the property alone.

| Scenario (seeds)                          | Market-adjusted correct | Wilson 95% CI | Naive correct |
|-------------------------------------------|-------------------------|---------------|---------------|
| Nothing changed (100)                     | 94/100                  | 0.88–0.97     | 95/100        |
| Whole market improved (100)               | 93/100                  | 0.86–0.97     | 0/100         |
| Real fix, +1.0 (50)                       | 50/50                   | 0.93–1.00     | 50/50         |
| Small fix, +0.2 (50)                      | 14/50                   | 0.17–0.42     | 19/50         |
| Fix after a decline (50)                  | 50/50                   | 0.93–1.00     | 50/50         |
| Behaviour on real reviews with a known, dated change | TBD          | TBD           | TBD           |

## Optional transformer backend (measured, SYNTHETIC + hand-written)

| Measure | Rule baseline | Transformer | Status |
|---|---|---|---|
| Polarity of the 36 unique SYNTHETIC templates | 33/36 | 26/36 | measured; templates favour the rules |
| 12 hand-written probe sentences (illustrative only) | 4/12 | 4/12 | measured; not a benchmark |
| Injected food decline recovered end-to-end (`seed=42`) | yes | no | measured: model misreads Hinglish negatives |
| Precision / recall / F1 on real labelled reviews | TBD | TBD | needs the hand-labelled set |

## Dashboard

- Streamlit dashboard: **built** (`app/`), every page tested headlessly in CI.
  Real screenshots on SYNTHETIC data: `docs/screenshots/*_SYNTHETIC.png`.
- Public deployment URL (Streamlit Community Cloud): `TBD` (steps in
  `docs/DEPLOYMENT.md`).

## Deployment / OpenSSF Scorecard

- Scorecard **score**: intentionally not stated. The live badge in the README is
  the source of truth once the repo is public and the workflow has run.
- Branch protection & required reviews: manual GitHub settings (see
  [`hardening.md`](hardening.md)). Status: `TBD`.
