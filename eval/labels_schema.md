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

The source review columns (`text`, `property_id`, `date`, `language_hint`) and
`notes` are optional but recommended. `notes` may mark `sarcasm`, `mixed
aspects`, or `very short review` for targeted error analysis. The scorer also
derives mixed-aspect cases from multiple gold aspects and very-short cases from
three or fewer whitespace-separated tokens.

## Prediction file

Pass a second CSV with the same `review_id` values and use `pred_aspects` and
`pred_sentiment_per_aspect` instead of the `gold_*` columns. Extra or missing IDs
are reported in the aggregate review count; no missing label is treated as a
neutral sentiment.

## Reproducible scoring

```bash
python eval/score.py gold.csv --predictions predictions.csv
```

The JSON output includes macro and per-aspect precision/recall/F1, a sentiment
confusion matrix for matched aspect labels, and error counts for sarcasm, mixed
aspects, and very short reviews. It contains only metrics calculated from the
provided files; unknown benchmark results remain unknown until labels exist.
