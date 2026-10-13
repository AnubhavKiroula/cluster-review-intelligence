# AI / ML components

Six components, each documented the same way: purpose, inputs, data, method,
evaluation, limitations, fallback and how users see the explanation. Only one of
them is *trained*; the others are transparent scoring engines, because there is no
data to train or validate them on (docs/DATA_SOURCES.md). Every number on this page
was measured or is a stated configuration value; unmeasured results are `TBD`
(tracked in docs/TODO_RESULTS.md).

| # | Component | Kind | Code |
|---|---|---|---|
| 1 | Review aspect + sentiment classifier (G5) | rules (default) or trained model | `cri.classify`, `cri.learned_backend` |
| 2 | Cluster benchmark, changepoints, market scope, fix check (G5) | statistical tests | `cri.benchmark`, `cri.intervention` (see `methodology.md`) |
| 3 | Visitor-demand index | transparent points model | `cri.travel.demand` |
| 4 | Crowd-aware alternatives | weighted similarity + capacity guard | `cri.travel.alternatives` |
| 5 | Stay profiles + provider opportunity engine | rules over review analytics + demand | `cri.travel.stays` |
| 6 | Seller opportunity + trip planner | exposure score; cost/carbon arithmetic | `cri.travel.region`, `cri.travel.planner` |

---

## 1. Review sentiment: rules (default) and the learned model

**Purpose.** Label each aspect clause of a review −1 / 0 / +1 so the G5 analytics can
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

## 2. G5 statistics

Bootstrap benchmark, changepoints relative to the market, market-wide patterns and
the intervention check are documented in [`methodology.md`](methodology.md) with
their SYNTHETIC calibration. Unchanged by this work.

---

## 3. Visitor-demand index (`cri.travel.demand`)

**Purpose.** Estimate *relative visitor pressure* (0–100) per destination and day
so travellers can avoid peaks, providers can prepare, and boards can see pressure
coming. It is **not** live traffic, road congestion or a booking forecast, and the
UI says so.

**Formulation.** A points model whose index is exactly the sum of the factors shown:

| Factor | Points | Basis |
|---|---|---|
| Popularity tier (high / medium / low) | 30 / 20 / 10 | assumption, with the evidence that informed it (UTDB arrivals where published) |
| Season | 25 × season[month] (0–1 curve per destination) | synthetic |
| Weekend (Sat/Sun) | +10 | assumption |
| Gazetted holiday | +10 | fact (DoPT lists) |
| Long weekend: day in a run of ≥ 3 consecutive off-days containing a holiday | +15 | derived |
| Inside an assumed school-vacation or year-end window | +10 each | assumption |

Clipped to 0–100 (a visible "capped" factor keeps the sum exact). Categories:
Low < 30 ≤ Moderate < 55 ≤ High < 75 ≤ Very High; "borderline" within ±3 points of
a cut. Bridge days are not counted (a Tuesday holiday is not a long weekend unless
Monday is also off). Beyond the holiday coverage (2026-01-01 to 2027-12-31) holiday
points are 0 and every such day carries a note.

**Quieter dates.** The same trip shifted by up to ±7 days; options at least 10
points quieter on average are returned with the factors they avoid.

**Why not a trained model.** No daily or monthly destination footfall exists in the
data we could obtain (UTDB publishes annual totals only; Himachal publishes no
destination series). Training a forecaster on invented observations would only
dress up the assumptions. The `DemandModel` protocol lets a trained model replace
the heuristic without touching callers.

**Confidence.** Always "indicative"; shown as a category first, never with a fake
numeric band.

**Validation plan** (`TBD` until data exists): with monthly arrivals per
destination, compare the monthly mean index with arrivals (Spearman rank
correlation per destination), then fit the weights on years ≤ Y and test on Y+1
(time-aware split); with partner occupancy, check that High/Very High days have
higher occupancy than Low days.

**Tests.** Index = sum of factors and within 0–100 for every destination and day;
adding a holiday never lowers any day; Christmas 2026 is a long weekend and
Tuesday Dussehra 2026 is not; beyond-coverage days carry the note; a custom model is
used when injected.

---

## 4. Crowd-aware alternatives (`cri.travel.alternatives`)

**Purpose.** When a destination is busy, suggest similar places with headroom,
without just moving pressure onto a more fragile place.

**Scoring.**

- similarity = weighted mean of: landscape Jaccard (0.30), activity-tag Jaccard
  (0.30), budget closeness 1 − |Δlevel|/2 (0.15), extra travel time from the
  traveller's city max(0, 1 − Δhours/4) (0.15), share of trip days in the place's
  suitable months (0.10). Weights are query parameters.
- relief = (D_origin − D_candidate)/100 on the same dates; headroom =
  (ceiling − D_candidate)/100 with an **assumed** ceiling of 90 / 80 / 70 for low /
  medium / high environmental sensitivity.
- score = similarity × min(relief, headroom). Excluded, with the reason, when relief
  < 0.10 or headroom ≤ 0 (the capacity guard).

**Explanation.** Every suggestion states why the original is busy (its top demand
drivers), why the alternative is similar (shared tags, budget), its expected crowd,
the trade-off (extra hours, budget level, official vs estimated distance) and its
limitations (assumed ceiling, SYNTHETIC profile, weather/roads not modelled).

**Limitations.** No official carrying capacity exists; ceilings and sensitivity
tiers are assumptions. Travel time uses an assumed 40 km/h door-to-door average.

**Tests.** Origin never suggested; every suggestion is ≥ 10 points quieter and under
its ceiling; at least one exclusion by the guard at Christmas; changing weights
changes the ranking; all five explanations present.

---

## 5. Stay profiles and the provider opportunity engine (`cri.travel.stays`)

**Purpose.** Compare stays without star ratings, and give providers explained,
actionable opportunities. Decision support only: no revenue prediction, no automatic
pricing.

**Profile.** Price range and band, room mix, listed amenities and sustainability
practices (self-reported, never labelled verified), rule-based suitability
(students/budget, families, groups, step-free access, remote work, each with its
reason), and guest feedback per aspect from the G5 scorecard (mean, 95% CI, n,
lead/lag vs the cluster) plus significant declines relative to the market.

**Insights** (each with "why" and evidence):

1. G5 priority actions ("Fix Food first since 2025-06").
2. Amenity gaps: negative review clauses matching cue words (heater/heating,
   hot water/geyser, wifi, parking), n ≥ 5 reviews, rate per 100 reviews vs the
   cluster, the peak month, example clauses, and a cross-reference to the G5 market
   scope (December Room complaints are market-wide).
3. Demand peaks in the next N days vs the room mix (flags family rooms < 20% during
   family-travel windows and budget rooms < 20% during weekends).
4. Low-demand windows of ≥ 3 days for offers.
5. Sustainability practices not reported.

**Tests.** No star or rating fields; amenity counts equal a direct
`search_reviews` count; Property F's first insight is the Food decline.

---

## 6. Seller opportunity and trip planner

**Seller opportunity** (`cri.travel.region`): exposure = mean over the window of
(demand index/100 × assumed category seasonality) × 100. A category is
"under-served" when exposure ≥ 40 (an assumption) and at most one seller is listed.
Labelled everywhere as a visitor-exposure estimate, **not sales or income**.

**Trip planner** (`cri.travel.planner`): picks the stay with the preferred room type
and enough rooms (fewest guest-feedback lags, then price; reported practices first if
the traveller asks), up to two interest-matched activities per day, a local seller
per day, and costs as traced lines:

- transport: car 2 × km × ₹12/vehicle-km × cars (4 per car), or bus 2 × km ×
  ₹2/passenger-km × travellers (synthetic rates);
- stay: price × rooms × nights; activities: Σ price × travellers; food:
  ₹500/800/1,200 per person-day by destination budget level (synthetic).

Carbon: 2 × km × factor (car per vehicle, bus per passenger) with the source shown;
stay emissions are not estimated. Variants: *lower budget* (budget rooms + bus) and
*lower crowd* (the quieter of the best ±7-day shift and the top alternative).

**Tests.** Cost lines sum to the total; carbon equals km × sourced factor; the
lower-budget variant is cheaper and the lower-crowd variant quieter; invalid input
is rejected.

---

## Responsible use

- Synthetic profiles, prices and sellers are labelled in files, API responses and
  UI. Facts carry their source.
- No live-traffic, safety or accessibility claims are made without data.
- Reviewer identity is dropped at ingestion; the hill-review text and the model
  trained on it never leave the local machine.
- Provider insights are suggestions with evidence, not guarantees.
