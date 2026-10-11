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
- Missing dates are rejected.
- Timezones: a date **without** an offset is local time (Asia/Kolkata) and is kept
  exactly as written. A date **with** an offset (`Z`, `+05:30`, mixed offsets in one
  file) is converted to Asia/Kolkata local time. Downstream code only ever sees
  naive local datetimes, so a review is counted in the month the guest stayed.
- Numeric dates are Unix epochs (seconds, ms, us or ns, by magnitude) and are UTC
  instants. In JSON, dates are left raw at load time so the same rules apply.
- One date format per file: a mix such as `05/01/2024` next to `13/01/2024` is
  rejected rather than guessed (ISO 8601 shapes such as date-only next to
  date-time with offsets may mix).
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
Fields a mapping does not name resolve to the canonical header itself (any case or
spacing, e.g. `Text`), otherwise to a conservative alias (e.g. `hotel`,
`review_text`, `stars`), so a file already in the standard schema loads unchanged.
A source column is used at most once (aliases never reuse a mapped column), and
two candidates for one field - including two headers that only differ in case or
spacing - are rejected rather than guessed. A mapping (dict or YAML) may only name
canonical columns. A `review_id` column is carried
through when present (mappable too), so labels can be joined back.

`load_dir` drops a review that repeats a row from an **earlier file** (overlapping
exports, compared after combining the files, so `4` and `4.0` match) and warns
with the count. Identical rows inside one file are kept: two
guests can post the same short review on the same day.
