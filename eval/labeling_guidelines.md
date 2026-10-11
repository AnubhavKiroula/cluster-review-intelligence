# Review labelling guide

Use this guide for the hand-labelled evaluation set. The goal is a reproducible
measurement of the shipped rule baseline, not a favourable result. Label the text
you receive; do not infer a label from the star rating or property.

## 1. Before labelling

- Work only on an assigned slice from `eval/split_manifest.csv`.
- Keep `review_id` unchanged and never add reviewer names, IDs, contact details, or
  unredacted platform exports.
- Use the taxonomy in `src/cri/resources/aspects.yaml`; do not invent new aspects.
- A review may have zero, one, or several aspects.

## 2. Aspect rules

Mark an aspect when the text makes a claim about it, including an indirect but clear
reference (for example, "room was freezing" is **Room**). Label every mentioned
aspect, even when the sentiment is neutral or ambiguous. Do not label an aspect
from a generic sentence with no aspect cue (for example, "we enjoyed the stay").

For mixed sentences, split the claims conceptually: `Food;Room` is valid when both
are discussed. Preserve taxonomy spelling and order is not significant.

## 3. Sentiment rules

Use one value for every labelled aspect:

- `1` positive: praise, satisfaction, or a clearly beneficial comparison.
- `-1` negative: complaint, failure, dissatisfaction, or a clearly harmful comparison.
- `0` neutral/unclear: factual mention with no polarity, balanced pros and cons where
  no single direction is defensible, or sarcasm whose intended polarity is unclear.

Handle Hinglish and Devanagari by meaning, not by language. Negation changes the
polarity when it clearly scopes the aspect (for example, "accha nahi" is negative).
Do not guess when a phrase is genuinely unclear; use `0` and explain it in `notes`.

## 4. Notes and quality flags

Add a short note when a row has `sarcasm`, `mixed aspects`, `very short review`, or
an adjudication question. The scorer uses these flags for error analysis. Keep notes
descriptive, not outcome-seeking.

## 5. Disagreement protocol

Each annotator labels only their assigned slice. If a second pass is commissioned,
use a separate file and keep both versions. Resolve disagreements by recording the
decision and reason in `notes`; never silently overwrite a prior label. Record the
number of independently double-labelled rows and the agreement statistic in
`docs/TODO_RESULTS.md` only after it has actually been calculated.

## 6. Output check

Before scoring, verify every non-empty `gold_aspects` entry has a corresponding
`Aspect=sentiment` entry, every sentiment is `-1`, `0`, or `1`, and there are no
duplicate `review_id` values. Run `python eval/score.py ...` only after this check.
