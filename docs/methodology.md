# Methodology

This documents the exact rules the MVP uses so results are reproducible and
auditable. The baseline is intentionally transparent (rules + lexicon); stronger
model backends are on the Roadmap.

## 1. Normalisation (`cri.normalize`)

- Lowercase; map a small emoji set to `good`/`bad` tokens, strip the rest.
- Map a few romanised-Hindi spelling variants to canonical forms (e.g. `nhi` →
  `nahi`).
- Split reviews into clause-like units on `.!?;` and on the connectives `aur`/`or`
  and commas, because a single review often mixes aspects.
- A rough script hint (`hi` / `hinglish` / `en`) populates/validates metadata but
  is **not** used for classification.

## 2. Aspect assignment (`cri.classify`)

Each clause is matched against the cue-term lists in
`src/cri/resources/aspects.yaml` (English, Hindi, and romanised Hinglish terms).
Single-word Latin cues match on token identity; multiword and Devanagari cues
match as substrings. A clause can map to more than one aspect.

Taxonomy: **Food, Room, Housekeeping, Staff, Location, Value for Money,
Cleanliness, Booking Experience.**

## 3. Sentiment (`cri.classify.RuleClassifier`)

A lexicon of positive/negative terms (English + romanised Hindi + a few
Devanagari terms) scores each clause. Multiword negative phrases (e.g.
`not working`, `band tha`) are matched directly. A negation token (`not`, `nahi`,
`no`, `never`, …) flips the sign of the next few sentiment tokens. The clause
sentiment is the sign of the net score: **−1, 0, or +1**.

## 4. Per property-aspect scores (`cri.benchmark.aspect_scores`)

For each `(property, aspect)` we compute the mean clause sentiment, the count, and
the standard error `std / sqrt(n)`.

## 5. Cluster benchmark (`benchmark_vs_cluster`)

The **cluster mean** for an aspect is the unweighted mean of the per-property
means (so a high-volume property does not dominate). A property-aspect is flagged:

- **lead** if `mean − cluster_mean > 0.05` **and** the normal-approximation 95%
  interval (`mean ± 1.96·se`) lies entirely above the cluster mean;
- **lag** if the symmetric condition holds below the cluster mean;
- **on_par** otherwise.

> Bootstrap confidence intervals (per the original design) are on the Roadmap;
> the MVP uses the normal approximation for transparency.

## 6. Trend & changepoint (`cri.changepoint`, `detect_changepoints`)

For each property-aspect we build a monthly mean-sentiment series and run a single
mean-shift detector: the split maximising `|mean(after) − mean(before)|`, subject
to a minimum segment length of 4 months, reported only if `|delta| ≥ 0.8`.

**Known limitation:** a single-shift detector with a fixed threshold produces
false positives on noisy months. We report changepoints honestly and treat the
largest-magnitude shifts as the reliable signal. A penalised multi-changepoint
method (PELT via `ruptures`) with significance testing is on the Roadmap.

## 7. Market-wide vs property-specific (`market_wide_summary`)

A property-aspect has a **negative shift** if it shows either a negative
changepoint **or** a December seasonal dip (December mean below the rest-of-year
mean by `≥ 0.5`). For each aspect we compute the share of properties with a
negative shift:

- **market-wide** if `share ≥ 0.6`;
- **property-specific** otherwise (with the affected properties listed).

This operationalises the core insight: the same aspect decline means different
things depending on whether the whole cluster moved together (a destination-level
issue) or a single property slipped (a competitive gap).

## Honest recovery on the synthetic data

With `seed=42` the pipeline recovers the two injected patterns:

- **Property F food decline** → changepoint at `2025-06`, the strongest negative
  shift in the dataset; classified **property-specific**.
- **December heating** → a December Room dip in the large majority of properties;
  classified **market-wide**.

A handful of weaker spurious changepoints also appear (see the limitation in §6).
Exact counts are reproducible by running `python scripts/make_figures.py` and the
test suite; measured classifier accuracy on **real** labelled data is `TBD`
(see [`TODO_RESULTS.md`](TODO_RESULTS.md)).
