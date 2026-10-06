# Project: cluster-review-intelligence

## Purpose
Cluster-level review analytics for Uttarakhand tourism (AI–Tourism Hackathon 2026, problem statement G5).
Pipeline: ingest reviews -> normalise Hinglish text -> aspect + sentiment -> cluster benchmark ->
trend/changepoint -> dashboard. Users: property managers; tourism boards (destination view).

## Non-negotiable rules
1. NEVER fabricate results. No invented accuracy, F1, dataset sizes, quotes, or statistics anywhere
   (code, README, docs). Unknown values are written as `TBD` and listed in docs/TODO_RESULTS.md.
2. Synthetic data must be labelled "SYNTHETIC" in filenames, figures, and README captions.
3. Do not scrape platforms or bypass blocks/rate limits/logins. Ingestion reads CSV/JSON files the team provides.
4. No personal data: drop reviewer names/IDs at ingestion. Real properties are anonymised (Property A, B...) in anything public.
5. No secrets in git. Config via environment variables; maintain `.env.example`.
6. No images of real hotels unless licensed; record every asset in docs/CREDITS.md.

## Stack and conventions
- Python 3.11+, `src/` layout, `pyproject.toml`, type hints, ruff + pytest.
- Dashboard: Streamlit + Plotly. Static README figures: matplotlib via `scripts/make_figures.py` (reproducible).
- Pin dependencies. GitHub Actions pinned to full commit SHAs (look up from official action repos; do not guess).
- Small commits, Conventional Commits messages, work on feature branches, never push to main directly.

## Definition of done (per task)
Tests pass, ruff clean, README/docs updated, no TBD silently replaced by a made-up number.
