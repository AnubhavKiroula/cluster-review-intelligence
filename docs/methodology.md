# Methodology

This documents the exact rules the pipeline uses so results are reproducible and
auditable. The default classifier is deliberately transparent (rules + lexicon);
an optional multilingual transformer backend is available (§9). Every number in
this file was measured on **SYNTHETIC** data and comes with the command that
reproduces it. Accuracy on real reviews is `TBD` (see [`TODO_RESULTS.md`](TODO_RESULTS.md)).

## 1. Normalisation (`cri.normalize`)

- Lowercase; map a small emoji set to `good`/`bad` tokens, strip the rest.
- Map a few romanised-Hindi spelling variants to canonical forms (e.g. `nhi` → `nahi`).
- Split reviews into clause-like units on `.!?;` and on the connectives `aur`/`or`
  and commas, because a single review often mixes aspects.
- A rough script hint (`hi` / `hinglish` / `en`) is metadata only; it is **not**
  used for classification. Reviews with missing text produce no mentions.

## 2. Aspect assignment (`cri.classify`)

Each clause is matched against the cue terms in `src/cri/resources/aspects.yaml`
(English, Hindi and romanised Hinglish). Single-word Latin cues match whole tokens;
multiword and Devanagari cues match as substrings. A clause can map to several
aspects. `CRI_ASPECTS_PATH` points at an alternative taxonomy file.

Taxonomy: **Food, Room, Housekeeping, Staff, Location, Value for Money,
Cleanliness, Booking Experience.**

## 3. Sentiment (`cri.classify.RuleClassifier`)

The lexicon lives in `src/cri/resources/lexicon.yaml` (positive/negative words,
multiword phrases, negation tokens; English, romanised Hindi and some
Devanagari). It is validated when loaded: entries must be lowercase, non-empty
strings, and no word may be both positive and negative. Multiword negative
phrases (e.g. `not working`, `band tha`) match directly; a negation token
(`not`, `no`, …) flips the sign of the next few sentiment words. Hindi negators
(`nahi`, `नहीं`; `post_negation` in `lexicon.yaml`) follow the word they negate, so
they flip the sentiment word up to 2 tokens *before* them ("accha nahi tha" → −1,
"koi problem nahi" → +1), and act like `not` only when nothing precedes them.
Clause sentiment is the sign of the net score: **−1, 0 or +1**.

Known weaknesses: sarcasm and implicit sentiment. The transformer backend (§9)
exists for such cases.

## 4. The statistical unit: one value per review and aspect

One review can contribute several mentions of the *same* aspect, e.g.
"Khaana badhiya tha aur nashta bhi tasty" yields two Food mentions with the same
sentiment. Treating mentions as independent overstates the evidence: on
pattern-free synthetic data the month-level dispersion index is ≈1.33 for
mentions and ≈0.99 after collapsing. So every significance test uses **one unit
per (review, aspect)** whose value is the mean of that review's clause
sentiments for the aspect (`benchmark.review_units`). Point estimates shown to
users (`mean`, `n`) stay mention-level.

## 5. Cluster benchmark, confidence intervals and flags (`benchmark_vs_cluster`)

- **Cluster mean** for an aspect = unweighted mean of the per-property means, so a
  high-volume property does not dominate.
- **95% CI** for a property-aspect mean = percentile **cluster bootstrap by review**
  (2,000 resamples of reviews; each resample's mean is
  Σ review sentiment totals / Σ review mention counts). Seeds are derived from the
  property and aspect names (CRC32), so a property's CI is identical whether it is
  computed alone or with the whole cluster. Below 10 reviews no CI is shown (NaN):
  a one-review "interval" of zero width would look perfectly certain.
- **Flags are multiple-testing controlled.** Each pair gets a two-sided p-value for
  "mean = cluster mean" from the review-level (cluster-robust) standard error, and
  Benjamini–Hochberg runs across **every** eligible property-aspect pair in the
  cluster (≈100 in the sample). `lead`/`lag` needs ≥ 10 reviews, a gap > 0.05,
  `q_value` ≤ 0.05, **and** a CI that excludes the cluster mean, so a flag never
  contradicts the interval drawn next to it. Without this, a cluster of identical
  properties produced ~6% false flags per pair, and false "lag" items reached
  "fix this first".
- The cluster mean is treated as a fixed reference (it includes the property
  itself, which makes the test slightly conservative).

## 6. "Is it me?" — property changepoints relative to the market (`detect_changepoints`)

1. **Build the market from deviations, not levels.** Every property's own level for
   the aspect is subtracted first; the market for month *t* is the average
   deviation of the **other** properties' reviews from their own levels. A strong
   or weak property entering, leaving, or changing volume therefore does not move
   the market. (Pooling raw levels did: a high-rated hotel appearing in 2025 made
   every other hotel look like it declined, in 20/20 simulated clusters.)
2. **Test one split.** Residual = review value − market. Over month-boundary splits
   leaving ≥ 4 months and ≥ 10 reviews on each side, a pooled-variance two-sample t
   statistic is computed. Its variance includes the error of the market estimate,
   estimated from the **other** properties' pooled within-property variance divided
   by the number of their reviews that month. (Using the focal property's own
   variance under-stated it ~5× next to differently rated competitors.)
3. **p-value.** Exact Student-t tail (regularised incomplete beta, no scipy),
   two-sided, Bonferroni-adjusted for the number of candidate splits.
4. **Across series.** Benjamini–Hochberg at **q = 0.05** over all tested
   property-aspect series, then an effect floor **|Δ| ≥ 0.4** (on the −1…+1 scale,
   roughly 20% of reviews flipping polarity), applied to unrounded values.
5. **Output.** `change_month` = first month of the new level; `delta` = shift
   relative to the market; `raw_delta` = the property's own shift; `market_delta`
   = the part the market shared; `p_value`, `q_value`.
6. **No market to compare with.** Decided **per aspect**: if fewer than 3
   properties review an aspect (or the whole cluster has fewer than 3), that
   aspect's raw series is tested instead and `market_delta` is NaN, so a collapse
   at the only hotel with a spa is still found.

## 7. "Is it the market?" — patterns shared across properties

Here the **properties are the replicates**, which is what "the whole market" means.
Only aspects reviewed at ≥ 3 properties are tested, and the "most properties"
share is relative to the properties that review the aspect.

- **Seasonal dips (`detect_market_patterns`, `detect_seasonal_dips`).** For every
  aspect and **every calendar month** (not just December): within **each year**,
  each property with ≥ 2 reviews in that month and ≥ 5 in the rest of that year
  contributes a gap = rest-of-year mean − month mean. A one-sample t-test asks
  whether the gaps are positive across properties, separately for each year, and
  the dip must hold in **every** observed year (≥ 2 years; the p-value is the
  largest per-year p-value, an intersection-union test). Comparing within a year
  means a one-off decline (e.g. from July) is not mistaken for seasonality; with
  less than two years of data, no month can be called seasonal. Benjamini–Hochberg
  at q = 0.05 over the seasonal tests. A property participates if its average gap
  is ≥ 0.3 and positive in every year; a pattern needs **≥ 60%** participation.
- **Step declines.** For each aspect, every property contributes its own
  after − before shift at each candidate split (≥ 4 months per side, ≥ 5 reviews
  per side per property). The split is placed where the **average decline is
  largest** (this peaks at the true change month for a single step); a one-sided
  t-test across properties at that split is Bonferroni-adjusted for the number
  of splits, then Benjamini–Hochberg across aspects. Same 60% / 0.3 participation
  rule. Months explained by a seasonal pattern are masked first (the month grid is
  kept, so the step's location is unaffected).
- A one-sample t-test was chosen over an exact sign-flip test because the
  sign-flip p-value cannot go below 2⁻ᴾ: with 96 tests it could never declare a
  pattern market-wide in clusters of fewer than ~11 properties.

## 8. Scope, priorities and the destination view

- **`market_wide_summary`** labels each aspect with a negative shift:
  `market-wide` (a §7 pattern exists), `property-specific` (only §6 declines
  relative to the market), or `undetermined` (fewer than 3 properties review the
  aspect). Aspects with no negative shift are omitted; `pattern` explains the call.
- **`priority_actions`** ("fix this first"): for each aspect, the property's
  current level is its mean since its latest significant decline (else its
  all-time mean). It is compared with the cluster mean **over the same months**
  (`basis = "cluster"`), or — when too few properties review the aspect to form a
  market, e.g. a single-hotel upload — with the property's own level before the
  decline (`basis = "own history"`, and the rationale says so). `gap = reference −
  current`; `volume` = the aspect's share of the property's mentions;
  `impact_score = gap × volume`. Only aspects that are worse **and** backed by
  evidence (a significant decline, or an FDR-controlled `lag` flag) are listed.
- **`whose_problem`** on each priority ("is it me or the market?"), derived for that
  property, never copied from `market_scope` by aspect (that label describes the
  cluster, not each property):
  - a significant decline relative to the market (section 6) → `yours alone`; the
    market's own move over the same months is quoted (`market_delta`);
  - a `lag` with no market-wide pattern (section 7) on the aspect that the property
    takes part in → `yours alone`;
  - otherwise the lag test of section 5 is re-run with the reviews those patterns
    cover set aside (a seasonal dip: its calendar month; a step decline: the months
    from its change onward), for that aspect only. Still `lag` → `yours alone`; not
    `lag` → `everyone's` (the property's own drop in the pattern is quoted next to the
    average drop);
  - `not tested` when fewer than 3 properties review the aspect (whatever the
    basis: a lag against a 2-property "cluster" separates nothing) or fewer than 10
    reviews remain outside the pattern.

  The re-test is not a separate FDR family: it reuses section 5's test on a subset,
  so treat `everyone's` as "the market pattern accounts for the gap", not as proof.
  Validation is SYNTHETIC only (`tests/test_insights.py`); real-data validation is
  `TBD`.
- **`destination_summary`** (the cluster-wide view; `/market` uses it): per aspect, the cluster mean,
  volume, share of negative mentions, number of properties reviewing it, and
  scope (`stable` when no shift, `undetermined` when too few properties).

## Input normalisation (`cri.api.load_cluster`)

- `property_id` is converted to text once, so numeric ids (101, 102, …) work
  everywhere and sort naturally.
- Timezone-aware dates (`…Z`, `+05:30`) are converted to naive local time in
  `Asia/Kolkata`, so months are the calendar months guests experienced. Mixing
  offsets within one file is handled on pandas 2.x; on pandas 3 the schema check
  currently rejects it (owner: `schema.py`).

## 9. Optional transformer backend (`CRI_MODEL_BACKEND=transformer`)

Aspects still come from the cue terms; only clause sentiment comes from
`lxyuan/distilbert-base-multilingual-cased-sentiments-student` (Apache-2.0,
revision pinned, safetensors). Each distinct aspect clause is scored once.
Install with `pip install -e ".[model]"`. Its accuracy relative to the rule
baseline on real reviews is `TBD`.

## 10. Calibration on SYNTHETIC data

Two datasets per seed share the same generator mechanics: *injected* (Property F's
food falls from 2025-06; Room dips every December in every property; Location falls
from 2025-03 at four neighbouring properties, §13) and *null*
(`inject_patterns=False`), where any finding is a false alarm. The four
neighbours' own Location declines are injected, so they are not counted as extra.

**Reproduce:** `python -m cri.calibration --seeds 1-20`

| Measure (20 seeds) | Result | Wilson 95% CI |
|---|---|---|
| Property F food decline found (±1 month) | 15/20 | 0.53–0.89 |
| … at exactly 2025-06 | 13/20 | 0.43–0.82 |
| Food correctly called property-specific | 15/20 | 0.53–0.89 |
| Room-December found market-wide | 20/20 | 0.84–1.00 |
| Extra changepoints per injected seed | 0.15 | — |
| Extra market patterns per injected seed | 0 | — |
| Null seeds with any false alarm | 1/20 | — |

**Previous implementation** (fixed thresholds, commit `ef0734d`), same protocol and
seeds: food decline found 13/20; null seeds with any false changepoint **17/20**
(about 2 false changepoints per null seed); and a December dip falsely flagged on
**every** null seed (about 7.7 false dips each).

**Fresh null seeds 21–120** (never used for design or tuning):

| Detector | Seeds with any false alarm | Wilson 95% CI |
|---|---|---|
| Property changepoints (§6) | 5/100 | 2.2–11.2% |
| Market-wide patterns (§7) | 0/100 | 0–3.7% |

During development, the same 100 seeds showed 11/100 before the market-estimate
variance term was added — evidence that §6.2 is needed.

**Lead/lag flags (§5)** on 100 simulated clusters of 12 identical properties ×
4 aspects (every flag false by construction, 3 reviews per property-month): 10/100
clusters had at least one false flag (Wilson 5.5–17.4%), 0.11 false flags per
cluster on average. Without multiple-testing control the same design produced
about 2.8 per cluster. At these low volumes the family-wise rate may sit somewhat
above the nominal 5%.

**Scenarios that once broke the detectors** (all now regression tests in
`tests/test_benchmark.py`, simulated with `tests/sim_helpers.py`):

| Scenario | Before | After |
|---|---|---|
| A strong hotel appears in the data from 2025 (nobody changes) | false declines in 20/20 clusters | none |
| Standout hotel in a 3-hotel null cluster: P(p ≤ 0.05) | 0.11–0.17 | 0.015 |
| One year of data with a market step at 2025-07 | "seasonal dips" in 20/20; step never at 2025-07 | no seasonality; step at exactly 2025-07 in 20/20 |
| Collapse at the only hotel with a spa | silently untested | detected; scope `undetermined` |
| Injected market-wide Location decline from 2025-03 | — | found at 2025-03 in 19/20, labelled market-wide 20/20, 0 false alarms without it |

Why recall is not higher: in several seeds the generator's random baseline makes
the injected food drop small (about −0.6 instead of −1.0 to −1.5). With about 100
reviews per series over 24 months, such drops give p ≈ 10⁻³–10⁻², while testing
96 series at FDR 5% needs about 5×10⁻⁴. Thresholds were **not** loosened to raise
recall.

## 11. Limitations (read before quoting results)

- **Synthetic only.** One true property change and one seasonal pattern; results
  may not transfer to real reviews.
- **Small samples.** 15/20 has a Wilson CI of 0.53–0.89; the clearly demonstrated
  improvement is in false alarms, not recall.
- **FDR, not FWER.** Once a real finding exists, Benjamini–Hochberg admits more
  marginal ones; about 0.15 extra changepoints per injected seed remain (0.10
  before the neighbourhood pattern was added; the difference is the §13 side effect
  on the market reference).
- **One changepoint per series**, located at the best split; the reported |Δ| at
  that split is biased upward (winner's curse). Multiple-changepoint methods (e.g.
  PELT) are not implemented: they need a penalty we cannot calibrate without
  real data.
- **Seasonality needs two years.** A dip must recur within every observed year, so
  shorter data cannot show seasonality (by design: one year cannot separate a
  season from a one-off change).
- **Approximations.** t-tests and normal tails on bounded, three-valued data;
  Benjamini–Hochberg assumes independence or positive dependence across tests,
  which holds only approximately.
- **Displayed means are mention-weighted** (a review with many clauses about one
  aspect counts more), while significance tests use one unit per review.
- **Small clusters.** Market-wide patterns need a consistent shift across
  properties; with ~5 properties only strong, consistent patterns are detectable,
  and below 3 properties the scope is `undetermined`.
- **Classifier.** The rule baseline misses sarcasm and implicit sentiment;
  real-data precision/recall/F1 are `TBD`.

## 12. "Did my fix work?" — market-adjusted before/after (`intervention_check`)

Detection (§6–7) says *what* went wrong. After a manager acts (new cook, heater
replacement, housekeeping training), the next question is whether it worked. A
plain before/after comparison credits the property with everything else that moved
in those months, such as the season, road conditions or a festival. This check makes
the comparison **relative to the market**, using the §6 reference.

1. **Inputs.** Property, aspect, and `start` = the first month after the change.
   The user picks the month, so this is **one pre-specified test**: no search over
   months and no multiple-testing correction. Choosing the month *after* looking at
   the trend makes the p-value optimistic; the dashboard says so.
2. **Effect.** Per review unit: value − market (the other properties' average
   deviation from their own levels that month, §6.1). `effect` = mean after − mean
   before of that residual, i.e. the property's change minus the market's change
   over the same months: a difference-in-differences with the rest of the cluster as
   the comparison group. Two-sample t test with the §6.2 standard error, which
   includes the variance of the market estimate. 95% CI = effect ± t₀.₉₇₅·SE.
   `naive_delta` = the plain change; `market_delta` = naive − effect.
3. **Baseline after a decline.** Managers usually act *because* something
   declined. Comparing with the whole history would then mix the good months before
   the problem with the bad months that prompted the fix, and could hide a real
   recovery. So "before" starts at the latest significant shift relative to the
   market in the months before `start` (the §6 test on that window: p ≤ 0.05,
   |Δ| ≥ 0.4, ≥ 4 months and 10 reviews per side), else at the first month of data.
   `baseline_start` can be overridden.
4. **Timing check.** The same §6 search over the before + after window (≥ 2 months
   and 10 reviews per side, Bonferroni over splits) gives `detected_start`. If a
   significant change begins more than one month before `start`, the summary warns
   that it may not be due to the fix. This covers changes too close to `start` for
   step 3 to make them the baseline.
5. **Placebo.** Every other property with ≥ 10 reviews on each side goes through
   the same calculation at the same months. `placebo_rank` = 1 + the number whose
   |effect| is at least as large. It is reported, not used for the verdict: with 12
   properties a permutation p-value cannot go below 1/12.
6. **Verdict.** `improved` / `worsened` when p ≤ 0.05, else `no detectable change`.
   `too early to tell` below 10 reviews mentioning the aspect after `start`; `no
   data` below 10 before. `mde` = 2.80 × SE, the effect detected with 80% power at
   5%, so "no detectable change" always comes with how large a change could have
   been missed.
7. **No market.** Below 3 properties reviewing the aspect, `basis = "own history"`:
   the test runs on the raw series, `market_delta` and the placebo are None, and the
   summary says the market's own change cannot be removed.

**Calibration (SYNTHETIC; reproduce with `python scripts/calibrate_intervention.py`).**
Simulated 6-property clusters, 15 reviews per property-month, 2024-01 to 2025-12,
change month 2025-06. "Naive" = the same test on the property's own reviews only.

| Scenario (seeds) | Truth | Market-adjusted correct (Wilson 95% CI) | Naive correct |
|---|---|---|---|
| Nothing changed (100) | no change | 94/100 (0.88–0.97) | 95/100 |
| **Whole market improved (100)** | no change | **93/100 (0.86–0.97)** | **0/100** |
| Real fix, +1.0 (50) | improved | 50/50 (0.93–1.00) | 50/50 |
| Small fix, +0.2 (50) | improved | 14/50 (0.17–0.42) | 19/50 |
| Fix after a decline (50) | improved | 50/50 (0.93–1.00) | 50/50 |

In the last scenario `baseline_start` was the true decline month (2025-01) in 48/50
seeds. The cost of removing the market is some power on small effects (14 vs 19
of 50), because the market estimate adds variance. That is what `mde` reports.

**Limitations.**
- **Not proof of cause.** Anything else that changed at the property in the same
  month is mixed in, and the comparison assumes the property would have moved with
  the market otherwise (parallel trends). The timing check and placebo only catch
  some violations.
- **Regression to the mean.** A fix made right after an unusually bad month can
  look like an improvement. Step 3 helps only when the bad period is a sustained
  shift (≥ 4 months).
- **Changing review mix.** If the fix changes *who* reviews or *which* aspects
  they mention, the comparison changes too. Management responses, for example, have
  been found to change who leaves reviews (Proserpio & Zervas, *Marketing Science*
  36(5), 2017, doi:10.1287/mksc.2017.1043).
- **Synthetic only.** The rates above are on simulated data; real-data behaviour
  is `TBD`.

## 13. "Is it my neighbourhood?" — a spatial scan (`cri.neighbourhood`)

"Yours alone" (§6) and "everyone's" (§7) miss a third case: a decline that a few
**nearby** properties share and the rest of the market does not. Road works on one
street, a water or power cut in one ward, a construction site. The right response
is collective (neighbours, the hotel association, the municipality), not an
in-house fix, and not "ignore it, everyone has it".

Such a decline is often invisible property by property. In the SYNTHETIC sample
four neighbours lose Location sentiment from 2025-03, but only one of them has
enough Location reviews for its own decline to pass the §6 test; pooled, the
four are clear.

**Input.** Property positions (`property_id, lat, lon[, zone]`,
`cri.locations`; see `docs/data_schema.md`). Without them nothing in this section
runs and every other result is unchanged.

**Method.**

1. **Candidate neighbourhoods.** For each located property, the properties within
   `NEIGHBOURHOOD_RADIUS_KM` = 1.0 km of it (great-circle distance), kept if there
   are at least `NEIGHBOURHOOD_MIN_PROPERTIES` = 3 and at most
   `NEIGHBOURHOOD_MAX_SHARE` = half of the located properties (a larger group is
   the market, §7).
2. **Group test.** Review values centred on each property's own level (§6.1), pooled
   over the group, minus the market formed by the properties **outside** the group,
   month by month. The best single negative step is found with the §6.2 test
   (Bonferroni over splits; the outside market's variance included). The group's
   score is −log₁₀ p of the **weakest leave-one-out** version of that test: the
   decline must survive dropping any one member, so one strongly declining property
   cannot make a neighbourhood.
3. **Significance.** An in-space permutation test: positions are shuffled between
   properties (null hypothesis: where a property is does not matter) and the whole
   scan is repeated, `NEIGHBOURHOOD_PERMUTATIONS` = 499 times (seeded). The observed
   score is compared with the **maximum over all groups and all aspects** of each
   shuffle, which controls the family-wise error over both. Kept at
   p ≤ `NEIGHBOURHOOD_MAX_P` = 0.05.
4. **Members.** Group members whose own shift relative to the outside market, at the
   detected month, is at least `MARKET_MIN_EFFECT` = 0.3 (as in §7); at least 3 are
   required. `centre` is their mean position and `radius_km` the farthest member's
   distance from it.

**Use.** `market_scope` labels the aspect `neighbourhood-wide` when there is no
market-wide pattern on it (a market-wide pattern takes precedence and the
neighbourhood is mentioned in its `pattern`). For a member,
`priority_actions.whose_problem` is `your neighbourhood's`, with the neighbours, the
month, its own shift, the group's shift and p in `whose_detail`; the aspect is listed
even when the property's own reviews alone would not flag it (`started` = the
detected month). If the property also takes part in a market-wide pattern on that
aspect, the §8 rules apply instead.

**Calibration (SYNTHETIC, `python scripts/calibrate_neighbourhood.py`).** Simulated
12-property clusters, one aspect, 3 reviews per property-month, each property with
its own baseline; positions from `generate_locations`. A decline drops P(positive)
to 0.15 from 2025-03. 100 seeds per scenario, 199 permutations per scan.

| Scenario | Flagged neighbourhood-wide | 95% Wilson CI |
|---|---|---|
| Nothing changed | 3/100 | 1–8% |
| 4 neighbours decline (clustered within 0.4 km) | 100/100 (exactly those 4: 95/100) | 96–100% |
| The same 4 decline, scattered over the town | 1/100 | 0–5% |
| 1 property declines, inside the neighbourhood | 4/100 | 2–10% |
| The whole market declines | 6/100 | 3–12% |

The false-alarm rates are consistent with the nominal 5% of the permutation test.
In the whole-market case `market_scope` and `whose_problem` still report the
market-wide pattern, because it takes precedence.

**Limitations.**

- **Positions are an input, not a finding.** Wrong or approximate positions
  (a property placed at its booking office, say) change the neighbourhoods.
- **One radius.** 1 km suits a compact hill town; a spread-out destination may
  need a larger radius. It is a fixed, documented constant, not tuned on the data.
- **Small clusters.** With fewer than 6 located properties no group can be at most
  half the cluster and hold 3 properties, so nothing is tested.
- **Approximations.** The same t-test approximations as §6; the permutation test is
  exact only under exchangeability of positions.
- **Not a cause.** "Shared by neighbours" says where, not why; the cause still has
  to be found on the ground.
- **The §6 market reference moves with a neighbourhood.** When four neighbours
  decline, the leave-one-out market that every other property is compared with
  dips too, so an unaffected property can look as if it *improved* relative to the
  market. In 20 SYNTHETIC seeds this produced one such false positive changepoint
  (seed 8: Property I, Location, +1.09 from 2025-04). Excluding detected
  neighbourhood members from the market reference would remove it; not done yet.
- **Synthetic only.** Real-data behaviour is `TBD`.
