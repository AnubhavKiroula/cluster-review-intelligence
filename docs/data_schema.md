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
- `rating` numeric and within `[1, 5]`.
- `text` non-empty after stripping whitespace.

## Formats

- CSV (`.csv`), JSON array (`.json`), or newline-delimited JSON (`.jsonl`).
- Place team-provided files in `data/raw/` (gitignored). The committed example is
  `data/sample/synthetic_reviews.csv` (SYNTHETIC).
