# Model card: `sentiment_open.npz` (learned clause-sentiment backend)

**What:** multinomial logistic regression over TF-IDF features of normalised text
(word 1–2-grams + within-word character 2–5-grams, sublinear tf, L2 norm; 60,000
features). Labels −1 / 0 / +1. Used by `CRI_MODEL_BACKEND=learned` to score the
sentiment of each *aspect clause*; aspects still come from the rule cue terms.
**Not the default backend** (see "Fit for purpose").

**Format:** compressed NumPy archive read with `allow_pickle=False` (no code runs on
load); `meta` holds the training configuration. Inference: `cri/learned_backend.py`.
Re-train: `python scripts/train_sentiment.py --model open` (seed 42, `[train]` extra).

## Training data (all CC BY 4.0, redistributable with attribution)

| Source | Rows used for training | Licence |
|---|---|---|
| SentiMix Hinglish tweets, SemEval-2020 Task 9 (Patwa et al., 2020), Zenodo [10.5281/zenodo.3974927](https://doi.org/10.5281/zenodo.3974927) | 13,995 (official train split) | CC BY 4.0 |
| Hinglish YouTube comments, [shae2977/hinglish-youtube-sentiments-dataset](https://huggingface.co/datasets/shae2977/hinglish-youtube-sentiments-dataset) @ `84abda5` | 2,545 (stratified 80%) | CC BY 4.0 |

`@mentions` and URLs are stripped; duplicates across splits and the SYNTHETIC
generator templates are removed. C = 1.0 was chosen on the dev splits only.

## Measured results (held-out test sets, 2026-10-13)

Macro-F1 with a 95% bootstrap interval (500 resamples). Full per-class precision /
recall and confusion matrices: `sentiment_open.metrics.json`.

| Test set | n | This model | Rule baseline | Majority class |
|---|---|---|---|---|
| SentiMix official test (tweets) | 2,997 | **0.663** (0.646–0.680) | 0.361 | 0.179 |
| YouTube held-out 10% | 314 | **0.631** (0.573–0.682) | 0.317 (0.367 after the 2026-10-13 rule fix) | 0.209 |
| Hill-destination hotel reviews, hotel-grouped test (weak labels from stars) | 8,388 | 0.390 (0.378–0.402) | **0.557** | 0.311 |

Whole-sentence polarity of the 36 SYNTHETIC generator templates: model 17/36, rules
36/36.

## Fit for purpose (read before using)

- Trained on tweets and YouTube comments: it **loses to the rules on hotel reviews**
  (domain shift). A local variant also trained on hill-destination hotel reviews does
  better on that domain (docs/AI_MODEL.md) but is not distributed.
- Trained on whole texts, applied to short clauses: clause-level accuracy is `TBD`
  until a hand-labelled hill-tourism gold set exists. On the SYNTHETIC cluster it does
  not recover the injected Property F food decline (docs/AI_MODEL.md).
- Hinglish sentiment labels have known noise (SentiMix reports 55% raw agreement
  before filtering).
