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
patterns the generator injected on purpose. Reproduce with `python -m pytest` and
`python scripts/make_figures.py`.

| Injected pattern                     | Recovered?            | Note                                  |
|--------------------------------------|-----------------------|---------------------------------------|
| Property F food decline (2025-06)    | Yes (changepoint)     | Strongest negative shift; `seed=42`.  |
| December heating (market-wide, Room) | Yes (seasonal dip)    | Majority of properties; `seed=42`.    |
| Spurious changepoint rate            | TBD (needs sweep)     | Known false positives; see methodology §6. |

## Dashboard

- Streamlit dashboard: **not built in this MVP** (Roadmap). Real screenshots for
  `docs/screenshots/` are `TBD`.

## Deployment / OpenSSF Scorecard

- Scorecard **score**: intentionally not stated. The live badge in the README is
  the source of truth once the repo is public and the workflow has run.
- Branch protection & required reviews: manual GitHub settings (see
  [`hardening.md`](hardening.md)). Status: `TBD`.
