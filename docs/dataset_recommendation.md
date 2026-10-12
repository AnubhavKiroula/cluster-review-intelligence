# Dataset recommendation

**Research status:** completed 2026-10-12. The links and metadata below were
checked against the public dataset cards or official task pages on that date.

## Decision

There is no single public dataset that satisfies all of CRI's requirements:

- tourism or hospitality reviews;
- Hindi, Hinglish, or Devanagari coverage;
- gold aspect **and** sentiment labels; and
- property identity plus review dates for cluster benchmarking and trend tests.

Use a layered data plan:

1. **Primary production/evaluation data — a legitimately provided Uttarakhand
   export.** This is the only suitable source for the cluster story. Ask a
   tourism board or partner properties for CSV/JSON containing anonymised
   `property_id`, review `date`, `rating`, `text`, `platform`, and
   `language_hint`, with written permission for research use. Do not scrape a
   platform. The existing loader and source adapter are ready for this format.
2. **Best public warm-start corpus — `RTT1/SentiMix`.** It contains
   Hindi-English code-mixed sentiment data with train/validation/test material.
   The Hugging Face repository is tagged OpenRAIL. It is useful for adapting a
   sentiment encoder or checking Hinglish normalization, but it has no tourism
   aspects, properties, or review dates. Its repository is token-level CoNLL
   data, so it needs a parser before use; the converted viewer's token rows
   must not be mistaken for review counts.
3. **Best public tourism-domain corpus —
   [`argilla/tripadvisor-hotel-reviews`](https://huggingface.co/datasets/argilla/tripadvisor-hotel-reviews).**
   The dataset card exposes 20.5k English hotel reviews with 1–5 labels and a
   `CC BY-NC 4.0` license. Use it only for non-commercial domain adaptation,
   vocabulary/error analysis, or weak-label experiments after reviewing the
   license. It is not a CRI gold set: the exposed schema does not provide the
   property/date structure and aspect annotations needed for cluster analytics.
4. **Small Hinglish smoke-test corpus —
   [`shae2977/hinglish-youtube-sentiments-dataset`](https://huggingface.co/datasets/shae2977/hinglish-youtube-sentiments-dataset).**
   It has 3,190 manually labelled Roman-script Hinglish comments, three
   sentiment classes, and a `CC BY 4.0` card. It is useful for a quick
   code-mixed sentiment probe, but it is entertainment/cooking YouTube data,
   not tourism reviews; the card also reports one annotator and no dates.

## Candidates not approved as training data yet

| Candidate | What it offers | Blocking issue | Recommended use |
|---|---|---|---|
| [`ai4bharat/IndicSentiment`](https://huggingface.co/datasets/ai4bharat/IndicSentiment) | Hindi and other Indic-language review translations; fields include aspects, aspect combinations, and sentiment labels | The public card/API metadata checked for this project does not declare a usable license or complete citation; its loader is also an executable dataset script | Resolve license/provenance with the dataset authors first; then consider sentiment/aspect warm-start only, not tourism evaluation |
| [SemEval-2016 Task 5 hotel data](http://alt.qcri.org/semeval2016/task5/index.php?id=data-and-tools) | Human-annotated hotel ABSA data with aspect categories and polarity | Arabic rather than Hindi/Hinglish; the data download has its own terms and is not a cluster/time-series corpus | ABSA schema smoke tests or cross-lingual research after checking the download terms |
| [`argilla/tripadvisor-hotel-reviews`](https://huggingface.co/datasets/argilla/tripadvisor-hotel-reviews) | English hotel domain and star labels | No gold aspect labels; no exposed cluster/time fields; `CC BY-NC 4.0` | Non-commercial domain adaptation only |

The `ai4bharat` and SemEval entries are intentionally not presented as cleared
datasets. A dataset being downloadable is not proof that its text may be
redistributed, used in a commercial product, or committed to this repository.

## What to request from the tourism board or partner

Request an export with these fields (the names can differ; use
`data/source_mapping.example.yaml`):

| Field | Requirement | Why |
|---|---|---|
| `property_id` | Stable anonymised label such as `Property A` | Property-vs-market comparison |
| `date` | Review publication date, ISO-parseable | Trend and changepoint analysis |
| `rating` | Numeric 1–5 if available | Audit/context; text remains the model input |
| `text` | Full review body, preserving Hindi/Hinglish/Devanagari | Aspect and sentiment classification |
| `platform` | Source label | Provenance and slice checks |
| `language_hint` | `en`, `hinglish`, or `hi` when known | Error analysis; advisory only |

Do not send reviewer names, usernames, profile URLs, emails, phone numbers, or
reviewer IDs. The ingestion path drops common identity columns, but the safest
practice is to remove them before sharing the export. Keep the raw export in
the gitignored `data/raw/` directory only.

For the current detectors, aim for at least three properties covering the same
aspects. At least two observed years are needed before a seasonal pattern can
be tested under the project's methodology. These are data requirements for the
analysis, not claims about any candidate dataset's size.

## Reproducible acquisition protocol

1. Record the dataset URL, access date, license, citation, source description,
   and any restrictions in `docs/CREDITS.md` before using it.
2. Download the provider's file manually or through its permitted distribution
   mechanism; do not add a network client to the CRI ingestion pipeline.
3. Place the file under `data/raw/` and map it with `cri.sources.load_source`.
4. Validate that identity columns are absent, properties are anonymised, dates
   parse, ratings are in range, and text is non-empty.
5. Run `scripts/prepare_label_input.py` and then `eval/split_labels.py` on a
   copy to create PII-free, disjoint annotation slices.
6. Hand-label the real set with `docs/labelling_template.csv`, run
   `eval/score.py`, and only then replace the real-data `TBD` entries in
   `docs/TODO_RESULTS.md`.

No external review rows are bundled with CRI as a result of this research.
The committed sample remains **SYNTHETIC**.

## Sources

- AI4Bharat, *Indic Sentiment Analysis*, dataset card and repository metadata:
  <https://huggingface.co/datasets/ai4bharat/IndicSentiment>
- Argilla, *tripadvisor-hotel-reviews*, dataset card:
  <https://huggingface.co/datasets/argilla/tripadvisor-hotel-reviews>
- RTT1, *SentiMix*, dataset repository:
  <https://huggingface.co/datasets/RTT1/SentiMix>
- shae2977, *Hinglish YouTube Sentiments Dataset*, dataset card:
  <https://huggingface.co/datasets/shae2977/hinglish-youtube-sentiments-dataset>
- Pontiki et al., *SemEval-2016 Task 5: Aspect Based Sentiment Analysis*:
  <https://aclanthology.org/S16-1002/> and the official data/tools page:
  <http://alt.qcri.org/semeval2016/task5/index.php?id=data-and-tools>
