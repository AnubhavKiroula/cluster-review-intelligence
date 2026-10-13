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
| Extra changepoints per injected seed      | 0.15   | —             | FDR (not FWER) control; one is a side effect of the neighbourhood pattern on the market reference (methodology §13) |

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

## Learned sentiment backend (measured 2026-10-13, `scripts/train_sentiment.py`)

Document-level macro-F1 on held-out test sets (95% bootstrap CI). Details and probes:
`docs/AI_MODEL.md`. The "templates" row here is *whole-sentence* polarity, a different
probe from the clause-level one in the transformer table above.

| Measure | Rules | `open` model | `region` model (local) | Status |
|---|---|---|---|---|
| SentiMix Hinglish test (n=2,997) | 0.361 | 0.663 (0.646–0.680) | 0.629 (0.613–0.646) | measured |
| YouTube Hinglish test (n=314) | 0.367 (0.317 before the 2026-10-13 negation fix) | 0.631 (0.573–0.682) | 0.609 (0.555–0.655) | measured |
| Hill hotel reviews, hotel-grouped, weak labels (n=8,388) | 0.557 (0.539–0.574) | 0.390 | 0.687 (0.669–0.706) | measured |
| Whole-sentence polarity, 36 SYNTHETIC templates | 36/36 | 17/36 | 24/36 | measured |
| Food decline found, 20 SYNTHETIC seeds | 15/20 | 5/20 | 4/20 | measured |
| December Room market-wide, 20 SYNTHETIC seeds | 20/20 | 20/20 | 14/20 | measured |
| **Clause-level** F1 on hand-labelled hill-destination reviews | TBD | TBD | TBD | needs the gold set |

## "Whose problem is it?" (`priority_actions.whose_problem`)

Validated on SYNTHETIC data only (`tests/test_insights.py`; method: `docs/AI_MODEL.md`
§3). The travel-layer TBDs (demand validation, occupancy, capacity, impact) were
dropped with the layer on 2026-10-13; they are at the git tag `travel-layer-v1`.

| Measure | Status |
|---|---|
| Agreement of verdicts with owner-confirmed causes, on real clusters | TBD: needs a real dated export and owner feedback |
| Share of priorities owners act on (pilot) | TBD: no users yet |

## Neighbourhood scan (SYNTHETIC simulations, reproducible)

Reproduce with `python scripts/calibrate_neighbourhood.py` (details: methodology §13).
Simulated 12-property clusters, 100 seeds per scenario, 199 permutations per scan.

| Scenario                                          | Flagged neighbourhood-wide | Wilson 95% CI |
|---------------------------------------------------|----------------------------|---------------|
| Nothing changed                                   | 3/100                      | 0.01–0.08     |
| 4 clustered neighbours decline                    | 100/100 (exact 4: 95/100)  | 0.96–1.00     |
| The same 4 decline, scattered                     | 1/100                      | 0.00–0.05     |
| 1 property declines inside the neighbourhood      | 4/100                      | 0.02–0.10     |
| The whole market declines                         | 6/100                      | 0.03–0.12     |
| Real neighbourhood-level declines (e.g. dated road works) | TBD                | TBD           |

## Web app and API

- Next.js app (the only UI): four pages plus home, all on the static snapshot;
  type-checked and built in CI. Screenshots on SYNTHETIC data:
  `docs/screenshots/*_SYNTHETIC.png`.
- API: `/health` and `POST /reviews/classify` only (live classify in the explorer).
- Public URLs: web app <https://cluster-review-intelligence.vercel.app> (Vercel), API <https://cri-api.onrender.com> (Render free plan).
  Verified 2026-10-13 (`docs/DEPLOYMENT.md`).
- API wake-up time after Render's free plan sleeps: `TBD` (not measured).
- **On-page SYNTHETIC banner: hidden for now** (team decision, 2026-10-13). The site
  still shows the SYNTHETIC sample, so CLAUDE.md rule 2 / SRS NFR-HON-2 are not met in
  the UI until it is restored: render `<SyntheticBanner />` above `<Header />` in
  `web/app/layout.tsx`. Recommended: restore it before a public deployment, unless the
  sample has been replaced with real, anonymised data.

## Deployment / OpenSSF Scorecard

- Scorecard **score**: intentionally not stated. The live badge in the README is
  the source of truth once the repo is public and the workflow has run.
- Branch protection & required reviews: manual GitHub settings (see
  [`hardening.md`](hardening.md)). Status: `TBD`.
