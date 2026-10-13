# AI / ML components

Three components, each documented the same way: purpose, method, evaluation,
limitations and how users see the explanation. Only the classifier is *trained*;
the other two are statistical tests over its output. Every number on this page was
measured or is a stated configuration value; unmeasured results are `TBD` (tracked
in docs/TODO_RESULTS.md).

| # | Component | Kind | Code |
|---|---|---|---|
| 1 | Review aspect + sentiment classifier | rules (default) or trained model | `cri.classify`, `cri.learned_backend` |
| 2 | Cluster benchmark, changepoints, market scope, fix check | statistical tests | `cri.benchmark`, `cri.intervention` (see `methodology.md`) |
| 3 | "Whose problem is it?" per priority | re-test of a lag with market patterns set aside | `cri.insights` |

The travel engines removed on 2026-10-13 (demand index, alternatives, stays,
planner, seller opportunity) are documented at the git tag `travel-layer-v1`.

---

## 1. Review sentiment: rules (default) and the learned model

**Purpose.** Label each aspect clause of a review −1 / 0 / +1 so the review analytics can
benchmark properties per aspect. Aspects always come from the transparent cue terms
in `aspects.yaml`; the backend only decides clause sentiment.

**Backends.** `rule` (lexicon + negation, default), `learned` (this section),
`transformer` (pretrained multilingual model, opt-in; methodology §9).

### Learned model

- **Features:** `featurize()` in `cri/learned_backend.py`: the text is normalised
  (`cri.normalize`: lowercase, emoji → good/bad, Hinglish spelling variants), then
  word 1–2-grams and within-word character 2–5-grams. Character n-grams let
  spelling variants (accha / acha / achha) share evidence.
- **Model:** TF-IDF (sublinear tf, L2 norm, min_df 3, 60,000 features) →
  multinomial logistic regression, balanced class weights, equal total weight per
  data source, C ∈ {0.5, 1, 2, 4} chosen on the dev splits only (mean of
  per-source dev macro-F1), seed 42.
- **Inference:** numpy only; the model file is an `.npz` loaded with
  `allow_pickle=False`; a test checks numerical parity with scikit-learn.
- **Data and splits** (details and licences: DATA_SOURCES.md):

| Source | Train | Dev | Test | Split |
|---|---|---|---|---|
| SentiMix Hinglish tweets (CC BY 4.0) | 13,995 | 2,998 | 2,997 | official |
| Hinglish YouTube comments (CC BY 4.0) | 2,545 | 318 | 314 | stratified 80/10/10 |
| Hill-destination hotel reviews, weak labels from stars (local only) | 59,406 | 13,033 | 8,388 | 80/10/10 **grouped by hotel** |

  Duplicates (normalised text) never cross splits; the 36 SYNTHETIC generator
  templates are excluded from training so the template probe stays fair.

- **Two models:**
  - `open` (SentiMix + YouTube): redistributable, committed as
    `src/cri/resources/models/sentiment_open.npz` (0.95 MB) with a model card.
  - `region` (open + hill reviews): better on the target domain, but trained on data
    of uncertain provenance, so it stays local
    (`data/raw/external/models/sentiment_region.npz`, loaded via
    `CRI_LEARNED_MODEL_PATH`).

### Results (held-out test sets, measured 2026-10-13)

Macro-F1, 95% bootstrap interval (500 resamples) for the models. Reproduce:
`python scripts/train_sentiment.py --model open|region` (metrics JSON next to the
model).

| Test set | n | `open` model | `region` model | Rules | Majority |
|---|---|---|---|---|---|
| SentiMix official test (tweets) | 2,997 | **0.663** (0.646–0.680) | 0.629 (0.613–0.646) | 0.361 | 0.179 |
| YouTube held-out | 314 | **0.631** (0.573–0.682) | 0.609 (0.555–0.655) | 0.317 | 0.209 |
| Hill hotel reviews, hotel-grouped (weak labels) | 8,388 | 0.390 (0.378–0.402) | **0.687** (0.669–0.706) | 0.557 | 0.311 |
| — Uttarakhand | 5,097 | 0.392 | **0.685** | 0.554 | — |
| — Himachal Pradesh | 2,403 | 0.394 | **0.673** | 0.559 | — |
| — Ladakh | 888 | 0.346 | **0.708** | 0.552 | — |

Per high-tourism hill town (towns with ≥ 1,000 reviews in the data, test reviews
only; small n are noisy), `region` vs rules: Nainital 0.695 vs 0.544 (n=1,707),
Tapovan 0.674 vs 0.559 (901), Shimla 0.661 vs 0.585 (827), Leh 0.720 vs 0.567 (690),
Kufri 0.689 vs 0.522 (469), Kausani 0.706 vs 0.619 (387), Shivpuri 0.691 vs 0.582
(338), Kaza 0.594 vs 0.529 (235), Sangla 0.797 vs 0.378 (227). Manali, Dalhousie and
Mashobra have no hotel in the test split.

On the hill reviews the `region` model's neutral class is weak (F1 0.42): 3★
reviews are mixed, and the weak label calls them all neutral.

**Ablation: 3★ reviews in training.** Keeping them as neutral (chosen) vs dropping
them from training only: best mean dev macro-F1 0.627 vs 0.580; on the hill-review
test 0.687 vs 0.551 (`--neutral drop`). Decided on dev, confirmed on test.

**Probes.** The seed calibration runs `cri.calibration.calibrate(range(1, 21), classifier=get_classifier("learned"))` with `CRI_LEARNED_MODEL_PATH` set (the CLI `python -m cri.calibration` always uses the rules).

| Probe | Rules | `open` | `region` |
|---|---|---|---|
| Whole-sentence polarity of the 36 SYNTHETIC templates | 36/36 | 17/36 | 24/36 |
| SYNTHETIC cluster seed 42: Property F food decline (injected 2025-06) | found, 2025-06 | not found | found, 2025-04 |
| SYNTHETIC cluster seed 42: December Room market-wide | found (12/12) | found (8/12) | not found |
| "Khaana accha nahi tha." (post-negation; rules' known miss) | +1 (wrong) | −1 | 0 |
| 20 SYNTHETIC seeds: food decline found (±1 month) | 15/20 | 5/20 (Wilson 0.11–0.47) | 4/20 (0.08–0.42) |
| 20 SYNTHETIC seeds: December Room market-wide | 20/20 | 20/20 | 14/20 (0.48–0.85) |
| 20 pattern-free seeds with any false alarm | 1/20 | 0/20 | 1/20 |

### Interpretation and decision

- The trained models clearly beat the rules **on real text of their own domain**:
  the `open` model on Hinglish tweets/comments, the `region` model on hill-destination
  hotel reviews (+0.13 macro-F1 over rules, non-overlapping intervals).
- Tweets do not transfer to hotel reviews: the `open` model is *worse* than the rules
  on hill reviews. Domain data matters more than model choice.
- Both are trained on **whole texts** and applied to **short clauses**, and they do
  not reproduce the injected G5 patterns on the SYNTHETIC cluster as reliably as the
  rules. Clause-level accuracy on real reviews is `TBD` until the hand-labelled gold
  set exists.
- **Decision: `rule` stays the default** (unchanged policy). `learned` is opt-in
  (`CRI_MODEL_BACKEND=learned`). Switch the default only if a model wins on the
  clause-level gold set.

**Failure modes.** Weak labels (stars ≠ sentiment; 89% positive); sentence-level
labels used for clause-level inference; no review dates, so no temporal validation;
sarcasm; Devanagari is rare in all training data; Mussoorie is absent from the
hill-review data.

**Next.** Label ~300 hill-destination clauses (Hinglish + English, two annotators,
Cohen's kappa) with the labelling pack; train on clause-split reviews; try a
fine-tuned multilingual transformer on the local GPU with the same splits.

---

## 2. Review statistics

Bootstrap benchmark, changepoints relative to the market, market-wide patterns and
the intervention check are documented in [`methodology.md`](methodology.md) with
their SYNTHETIC calibration. Unchanged by this work.

---

## 3. "Whose problem is it?" (`priority_actions.whose_problem`)

**Purpose.** Each "fix this first" row on the property page answers the owner's one
question: is this decline mine or the market's? Values: `yours alone`,
`everyone's`, `not tested`; `whose_detail` says why.

**Method.** Derived per property, **never joined from `market_scope.scope` by
aspect** (that label describes the cluster, not each property):

| Case | Verdict |
|---|---|
| The property's own decline relative to the market (a market-adjusted changepoint) | `yours alone` |
| A lag vs the cluster, with no market-wide pattern on the aspect that the property takes part in | `yours alone` |
| A lag, re-tested (same FDR-controlled lag test) with the market-wide patterns the property takes part in set aside: still lags | `yours alone` |
| Same re-test: the lag disappears | `everyone's` |
| Fewer than 3 properties review the aspect, or fewer than 10 reviews remain outside the pattern | `not tested` |

"Set aside" means the pattern's calendar month (seasonal dip) or the months from its
start (step decline), for that aspect only.

**Validation (SYNTHETIC only, `tests/test_insights.py`).** Property F's Food decline
is `yours alone`. Property D's Room lag stays `yours alone` although Room has a
market-wide December dip: D is still 0.36 below the market outside December. A
fixture that adds two extra copies of Property G's December Room reviews makes G lag
on Room purely through the dip, and the verdict becomes `everyone's`. Agreement with
causes confirmed by owners on real clusters is `TBD`.

**Limitations.** It inherits the power limits of the lag test (about 100 reviews per
property-aspect); a property hit harder than average by a market-wide pattern is
`everyone's` if its remaining lag is not significant (the detail shows its drop vs
the average drop).

---

## Responsible use

- SYNTHETIC data is labelled in files, figures and the UI.
- Reviewer identity is dropped at ingestion; the hill-review text and the model
  trained on it never leave the local machine.
- Priorities and verdicts are suggestions with evidence, not proof of cause.
