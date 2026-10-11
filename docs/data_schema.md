# Data schema

The pipeline ingests one row per review. Reviewer identity is **never** part of
the schema and is stripped at load time (see `src/cri/loader.py`).

## Required columns

| Column          | Type            | Description                                                        |
|-----------------|-----------------|--------------------------------------------------------------------|
| `property_id`   | string          | Anonymised property label (e.g. `Property A`). No real hotel names.|
| `platform`      | string          | Source platform label (e.g. `GoogleMaps`, `Booking`).              |
| `date`          | date (ISO 8601) | Review date, `YYYY-MM-DD`.                                          |
| `rating`        | integer 1–5     | Star rating.                                                       |
| `text`          | string          | Review text (English / Hinglish / Devanagari). Must be non-empty.  |
| `language_hint` | string          | `en`, `hinglish`, or `hi`. Advisory only; the lexicon is multilingual. |

## Dropped at ingestion (PII)

Any column named (case-insensitively) `reviewer_name`, `reviewer_id`, `reviewer`,
`user`, `username`, `user_id`, `author`, `name`, `email`, `phone`, or
`profile_url` is removed before validation. See `IDENTITY_COLUMNS` in
`src/cri/schema.py`.

## Validation rules

- All required columns present (clear error listing any missing).
- `date` parseable as a date.
- Missing dates are rejected; mixed timezone offsets are normalised safely at
  validation and converted to Asia/Kolkata by the API facade.
- `rating` numeric and within `[1, 5]`.
- `text` non-empty after stripping whitespace.

## Formats

- CSV (`.csv`), JSON array (`.json`), or newline-delimited JSON (`.jsonl`).
- Place team-provided files in `data/raw/` (gitignored). The committed example is
  `data/sample/synthetic_reviews.csv` (SYNTHETIC).

## Mapping a partner export

For a CSV/JSON export whose headers differ, use `cri.sources.load_source` with a
canonical-to-source mapping, for example:

```python
from cri.sources import load_source

reviews = load_source(
    "data/raw/partner_export.csv",
    {"property_id": "hotel_code", "text": "review_body", "rating": "stars"},
)
```

The adapter still drops identity columns and runs the normal schema validation. For
repeatable loading, pass the same file through `mapping_file="data/source_mapping.example.yaml"`
instead of constructing the dictionary in application code.
Conservative aliases are available when no mapping is supplied; ambiguous matches
are rejected rather than guessed. Exact duplicate rows from overlapping files are
removed by `load_dir`.
