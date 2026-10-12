# Archit's data and evaluation status

This is the hand-off checklist for the data/evaluation track. It records what
is already implemented in the repository and the remaining actions that can be
completed without inventing results or committing external review data.

## Completed in the repository

- Source-column adapter and YAML mapping config: `src/cri/sources.py` and
  `data/source_mapping.example.yaml`.
- PII dropping and schema validation at ingestion: `src/cri/schema.py` and
  `src/cri/loader.py`.
- Deterministic, disjoint annotation slices: `eval/split_labels.py`.
- PII-free label-input preparation with generated local IDs:
  `scripts/prepare_label_input.py`.
- Macro/per-aspect aspect metrics, sentiment confusion matrix, and error
  categories: `eval/score.py`.
- Annotation template and guidelines: `docs/labelling_template.csv`,
  `eval/labeling_guidelines.md`, and `eval/labels_schema.md`.
- Dataset research and a no-scraping acquisition plan:
  `docs/dataset_recommendation.md`.

## Remaining Archit-owned actions

### 1. Obtain approved real data

- [ ] Ask the tourism board or a partner property for a written research-use
  export with the fields in `docs/dataset_recommendation.md`.
- [ ] Confirm whether the permission allows model training, internal demo use,
  and publication of aggregate results.
- [ ] Record provenance and restrictions in `docs/CREDITS.md`.
- [ ] Put the export only in gitignored `data/raw/`; never commit it.

### 2. Validate and anonymise the export

```bash
python - <<'PY'
from cri.sources import load_source

reviews = load_source(
    "data/raw/partner_export.csv",
    mapping_file="data/source_mapping.example.yaml",
)
print(reviews.shape)
print(reviews.columns.tolist())
PY
```

Before running this, update the example mapping outside committed files if the
partner's headers differ. Verify that real property names have been replaced by
`Property A`, `Property B`, and so on.

### 3. Create the labelled evaluation set

```bash
python scripts/prepare_label_input.py \
  data/raw/partner_export.csv data/raw/label_input.csv \
  --mapping-file data/source_mapping.example.yaml
python eval/split_labels.py data/raw/label_input.csv data/raw/label_slices \
  --annotators Anubhav Purvansh Archit
```

`scripts/prepare_label_input.py` runs the normal PII drop and schema validation,
then adds stable local `review_id` values and blank gold-label columns. Use
`docs/labelling_template.csv` and `eval/labeling_guidelines.md` while labelling.
Keep the generated files under gitignored `data/raw/` until the team confirms
that the source permission allows their storage and publication. Then score the
agreed gold set with:

```bash
python eval/score.py data/raw/label_slices/gold.csv \
  --predictions data/raw/label_slices/predictions.csv
```

Only measured output from this command may replace a real-data `TBD` in
`docs/TODO_RESULTS.md` or `README.md`.

### 4. Integrate public warm-start data only if legally cleared

The immediate public fallback is SentiMix for code-mixed sentiment adaptation.
It is not a substitute for the partner export, and its OpenRAIL terms must be
reviewed before use in the project. Hotel review data is a secondary,
non-commercial domain-adaptation option. Neither source supplies the gold
cluster labels needed for the final evaluation.

### 5. Operational follow-up

- [ ] Merge the open numpy 2 / pandas 3 Dependabot changes after CI verifies
  them together.
- [ ] Add or verify a real-data smoke run after an approved export arrives.
- [ ] Keep `docs/TODO_RESULTS.md` unchanged until a real labelled evaluation is
  actually run.

## Explicit boundary with the other tracks

The Streamlit/Next.js dashboard and public deployment are Purvansh-owned in
`docs/HACKATHON_PLAN.md`. Archit's next highest-value contribution is therefore
the approved export, provenance record, and measured labelled evaluation that
the dashboard can consume.
