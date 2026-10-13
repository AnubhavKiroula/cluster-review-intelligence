# Data sources

What every dataset is, where it came from, and whether it is **real** or
**SYNTHETIC**. Nothing synthetic is presented as real anywhere in the app.

The sourced facts and SYNTHETIC profiles of the travel layer removed on 2026-10-13
(holidays, coordinates, distances, arrivals, emission factors, stays, sellers) are
documented at the git tag `travel-layer-v1`.

## At a glance

| Data | Status | Where | Used for |
|---|---|---|---|
| Review cluster, 12 properties (Property A–L), 5,124 reviews, 2024-01..2025-12 | **SYNTHETIC** (`cri.generate`, seed 42) | generated in memory; `data/sample/synthetic_reviews.csv`; web snapshot `web/public/data/*.synthetic.json` | all review analytics and every web page |
| SentiMix Hinglish tweets | **Real**, CC BY 4.0 | downloaded to `data/raw/external/` (gitignored) | training/testing the learned sentiment model |
| Hinglish YouTube comments | **Real**, CC BY 4.0 | downloaded to `data/raw/external/` | same |
| Hill-destination hotel reviews (Kaggle) | **Real**, provenance uncertain | downloaded by a team member to `data/raw/external/` | training/testing the local region model only |

## Gaps and their effect

| Missing | Effect | What would fix it |
|---|---|---|
| A real, dated review export from one cluster | The analytics, including "whose problem", are validated on SYNTHETIC data only | A permitted, anonymised export from partner properties or a tourism board |
| Clause-level labels on real reviews | Real clause-level accuracy is `TBD`; the learned model stays opt-in | The hand-labelled gold set (labelling pack) |

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
  TripAdvisor, whose terms a CC0 tag cannot override. We therefore use it for
  research only and **never commit the text or the model trained on it**.
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
   board (with dates) to run the analytics, including "whose problem", on real data.
