# Contributing

Thanks for your interest. This is a hackathon MVP; contributions should keep the
project honest and reproducible.

## Ground rules (from `CLAUDE.md`)

1. **Never fabricate results.** No invented accuracy/F1/dataset sizes/quotes/stats
   anywhere. Unknown values are written as `TBD` and tracked in
   [`docs/TODO_RESULTS.md`](docs/TODO_RESULTS.md).
2. **Label synthetic data** as `SYNTHETIC` in filenames, figures, and captions.
3. **No scraping.** Ingestion reads CSV/JSON files the team provides.
4. **No personal data.** Reviewer identity is dropped at ingestion; real properties
   are anonymised in anything public.
5. **No secrets in git.** Use environment variables; keep `.env.example` current.

## Dev setup

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

## Workflow

- Branch off `main`; do not push to `main` directly.
- Keep commits small and use [Conventional Commits](https://www.conventionalcommits.org/)
  messages (e.g. `feat:`, `fix:`, `docs:`, `test:`).
- A change is "done" only when: tests pass, `ruff` is clean, docs are updated, and no
  `TBD` was silently replaced by a made-up number.
- Open a PR using the template; link any related issue.

## Adding a classifier backend

Implement the `Classifier` interface in `src/cri/classify.py` behind a flag. Do not
add large model downloads or paid-API calls to the default path.
