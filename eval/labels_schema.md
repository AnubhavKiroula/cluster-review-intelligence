# Evaluation labels schema

This directory contains human-created evaluation annotations. Do not place
personal data or scraped platform exports here. `labelled/` is intentionally
empty in the repository; add a reviewed CSV only when it is available.

## Required columns

| Column | Format | Meaning |
| --- | --- | --- |
| `review_id` | non-empty string | Stable identifier joining gold and prediction rows |
| `gold_aspects` | semicolon-separated names | All aspects mentioned in the review |
| `gold_sentiment_per_aspect` | `Aspect=-1\|0\|1;...` | Human sentiment per mentioned aspect |

Blank `gold_*` cells mean **not labelled yet**: the row is skipped and counted
(`n_unlabelled_skipped`). A review a human checked that mentions no aspect gets
`gold_aspects = none`. Aspect names are case-insensitive but must come from
`src/cri/resources/aspects.yaml` (a typo fails loudly instead of scoring 0).
`review_id` values must be unique; `1` and `1.0` (an id read as a number) match.

The source review columns (`text`, `property_id`, `date`, `language_hint`) and
`notes` are optional but recommended. `notes` may mark `sarcasm`, `mixed
aspects`, or `very short review` for targeted error analysis. The scorer also
derives mixed-aspect cases from multiple gold aspects and very-short cases from
three or fewer whitespace-separated tokens.

## Prediction file

`eval/predict.py` writes the shipped classifier's predictions (backend from
`CRI_MODEL_BACKEND`, default `rule`) as a CSV with `review_id`, `pred_aspects`
and `pred_sentiment_per_aspect`. Per review and aspect, the sentiment is the sign
of the mean of that aspect's clause sentiments - the same unit the analytics use.
Only labelled reviews are scored: a labelled review with no prediction counts as
"predicted nothing" (never as neutral), and predictions for unlabelled reviews are
only counted (`n_predictions_without_gold`).

## Reproducible scoring

```bash
python eval/predict.py eval/labelled/gold.csv --out eval/labelled/predictions.csv
python eval/score.py eval/labelled/gold.csv --predictions eval/labelled/predictions.csv
```

The JSON output includes:

- aspect detection: per-aspect and macro precision/recall/F1;
- sentiment, on aspects both the human and the model found: accuracy, per-class
  and macro F1 over `-1/0/1`, and the confusion matrix;
- error counts for sarcasm, mixed aspects, and very short reviews.

Undefined metrics are `null`. It contains only metrics calculated from the
provided files; unknown benchmark results remain `TBD` until labels exist.

`eval/labelled/*.csv` is gitignored: labelled files contain review text, so they
are shared inside the team, never committed.
