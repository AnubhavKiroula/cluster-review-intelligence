# Data sources

What every dataset is, where it came from, and whether it is **real** or
**SYNTHETIC**. Nothing synthetic is presented as real anywhere in the app.

The sourced facts and SYNTHETIC profiles of the travel layer removed on 2026-10-13
(holidays, coordinates, distances, arrivals, emission factors, stays, sellers) are
documented at the git tag `travel-layer-v1`.

## At a glance

| Data | Status | Where | Used for |
|---|---|---|---|
| **Kausani cluster: 25 hotels (Property A–Y), 2,751 reviews, no dates** | **Real** (Kaggle hill reviews, below) | built locally by `scripts/prepare_real_cluster.py` into `data/raw/external/prepared/` (gitignored); **aggregates only** in `web/public/data/cluster.real.json` | home, `/property` and `/market` (the real view) |
| Review cluster, 12 properties (Property A–L), 5,124 reviews, 2024-01..2025-12 | **SYNTHETIC** (`cri.generate`, seed 42) | generated in memory; `data/sample/synthetic_reviews.csv`; web snapshots `web/public/data/*.synthetic.json` | the time-series method demo (`?source=demo`, `/fix-check`), the explorer's illustrative texts, calibration |
| SentiMix Hinglish tweets | **Real**, CC BY 4.0 | downloaded to `data/raw/external/` (gitignored) | training/testing the learned sentiment model |
| Hinglish YouTube comments | **Real**, CC BY 4.0 | downloaded to `data/raw/external/` | same |
| Hill-destination hotel reviews (Kaggle) | **Real**, provenance uncertain | downloaded by a team member to `data/raw/external/` | the Kausani cluster (aggregates published, text never), and training/testing the local region model |

## Gaps and their effect

| Missing | Effect | What would fix it |
|---|---|---|
| Review dates in the real corpus | On the real Kausani cluster only level-based analysis is possible (lead/lag, shared weak spots, priorities). Trends, changepoints, seasonal dips and the fix check run on the SYNTHETIC timeline only | A permitted, anonymised, **dated** export from partner properties or a tourism board |
| Clause-level labels on real reviews | Real clause-level accuracy is `TBD`; the learned model stays opt-in | The hand-labelled gold set (labelling pack) |

## The real cluster in the demo: Kausani

Built on 2026-10-13 with `python scripts/prepare_real_cluster.py --town Kausani`
from the Kaggle hill reviews (same filters as below). Reported by the script:

| | Value |
|---|---|
| Town | Kausani, Bageshwar district, Uttarakhand |
| Hotels / reviews in the town (after de-duplication) | 41 / 2,877 |
| Inclusion rule | at least 20 reviews per hotel (2 × `MIN_REVIEWS_FOR_FLAG`): the cluster average weighs every hotel equally, so a hotel with a handful of reviews adds noise and can never be tested |
| **In the cluster** | **25 hotels, 2,751 reviews** (median 66 per hotel; 22 to 354) |
| Review dates | **none**: the source has no date field, and none are inferred or invented |
| `property_id` | `Property A`…`Property Y`, stable (ordered by an opaque hash of the file name); the name map stays local (`real_cluster_kausani_MAP.csv`, gitignored) |
| `platform` | `tripadvisor`, **inferred**: the corpus is TripAdvisor-derived, but no row states its platform |
| `rating` | stored as 10–50 in the source, divided by 10 to 1–5 stars |
| `language_hint` | detected by `cri.normalize.detect_language` (whole-word markers): 2,743 English, 5 Hinglish, 3 Hindi |
| Reviewer identity | `name`, `user_profile`, `userloc` are never loaded |

**Why Kausani** (step 1, counted over the prepared corpus; Uttarakhand towns with the
most hotels):

| Town | Hotels | Reviews | Median per hotel | Hotels with ≥ 50 reviews |
|---|---|---|---|---|
| **Kausani** | **41** | **2,877** | **31** | **16** |
| Joshimath–Auli | 37 | 963 | 5 | 7 |
| Lansdowne | 36 | 1,972 | 37.5 | 15 |
| Dhanaulti | 33 | 658 | 5 | 4 |
| Uttarkashi | 32 | 411 | 4 | 2 |
| Tapovan | 26 | 1,809 | 4.5 | 4 |
| Shivpuri | 23 | 1,020 | 17 | 8 |
| Kanatal | 21 | 772 | 11 | 3 |
| Nainital | 7 | 4,556 | 570 | 7 |

Kausani has the most competing hotels with real review volume; Lansdowne is a close
second. Nainital has many reviews but few hotels. Mussoorie is absent.

**Hinglish in this corpus is near zero.** Whole-word Hinglish or Devanagari markers
(`accha`, `bahut`, `nahi`, `sahi`, `thoda`, `kitna`, `khana`, `kamra`, …, or any
Devanagari letter) appear in 4 of the 2,877 Kausani reviews and in 80 of all 80,827
prepared reviews. The product's Hinglish handling therefore rests on the classifier
and its evaluation on SentiMix and YouTube, not on this corpus.

**Licence position.** The uploader declares CC0, over text that appears to be
TripAdvisor-derived. We **analyse** it and publish only **derived statistics**
(means, counts, confidence intervals, scope, priorities, star averages) under
anonymised ids. We **never redistribute** the review text, clause text, hotel names
or reviewer data: the real snapshot carries no text field (`tests/test_demo.py`
checks this), and the inputs stay under the gitignored `data/raw/external/`.

## Review datasets for the learned sentiment model

None of these is committed to git; all live under `data/raw/external/` (gitignored).

### SentiMix (SemEval-2020 Task 9) — CC BY 4.0

- Source: Zenodo record [3974927](https://doi.org/10.5281/zenodo.3974927),
  `Semeval_2020_task9_data.zip`, md5 `4d93553c213b3a966b6d55b7a7c03be7`. (A Hugging
  Face re-upload `RTT1/SentiMix` carries a different licence tag; we use the original.)
- Hinglish code-mixed tweets, CoNLL token format, labels positive / neutral /
  negative: 14,000 train, 3,000 dev, 3,000 test (test labels in a separate file).
- Cite: Patwa et al., *SemEval-2020 Task 9: Overview of Sentiment Analysis of
  Code-Mixed Tweets*, SemEval 2020.

### Hinglish YouTube comments — CC BY 4.0

- Source: [shae2977/hinglish-youtube-sentiments-dataset](https://huggingface.co/datasets/shae2977/hinglish-youtube-sentiments-dataset),
  revision `84abda5e30d082a66c251fc46513cb89ce866cbb`, file sha256
  `07de7acd…f19fc6`. 3,190 comments (entertainment / cooking videos), one annotator.

### Hill-destination hotel reviews (Kaggle) — provenance uncertain, local only

- Source: [orionpax00/uttarakhand-hotel-reviews-india](https://www.kaggle.com/datasets/orionpax00/uttarakhand-hotel-reviews-india),
  downloaded by a team member with their own Kaggle login (we do not bypass logins).
  Uploader-declared CC0, last updated 2020; the reviews appear to come from
  TripAdvisor, whose terms a CC0 tag cannot override. We **never commit the text or
  the model trained on it**; only anonymised aggregate statistics of one town are
  published (see *The real cluster in the demo*).
- Profile (2026-10-13, `scripts/prepare_region_reviews.py`): 1,628 CSVs (one per
  hotel, 20 empty), columns `location, review, name, user_profile, userloc, rating`.
  No review dates. Despite the name it covers Uttarakhand, Himachal Pradesh and
  Ladakh.
- Processing: reviewer columns are never loaded; hotel names become opaque ids;
  the plains districts Haridwar and Udham Singh Nagar are dropped (Dehradun and
  Nainital districts are mixed and kept); duplicate texts are removed before any
  split; 10 files whose names carry no district are skipped.
- Result: 80,827 reviews from 1,306 hotels (Himachal 33,633; Uttarakhand 29,564;
  Ladakh 17,432). Stars: 1★ 1,964 · 2★ 1,544 · 3★ 4,999 · 4★ 18,995 · 5★ 53,325.
  Weak labels: 1–2★ → negative, 3★ → neutral, 4–5★ → positive (89% positive).
- Mussoorie is effectively absent (2 files in Dehradun district).

### Considered and not used

| Dataset | Why not |
|---|---|
| argilla/tripadvisor-hotel-reviews | CC BY-NC 4.0 and English hotels outside India; weights could not ship in this Apache-2.0 repo |
| ai4bharat/IndicSentiment | Translated product reviews; validation/test only (no train split) |
| SemEval-2016 Task 5 ABSA | Hotel data is Arabic only |
| PromptCloud Goibibo / MakeMyTrip listings | No review text |

## Future data acquisition

1. A hand-labelled gold set of ~300 hill-destination clauses (Hinglish + English)
   via the existing labelling pack, to measure clause-level accuracy (`TBD`).
2. A permitted, anonymised review export from partner properties or the tourism
   board **with dates**, so trends, changepoints and the fix check can run on real
   data too (today they run on the SYNTHETIC timeline).
