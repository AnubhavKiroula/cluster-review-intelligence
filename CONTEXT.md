# CONTEXT

Living project state. Update at meaningful milestones.

## What is being built
G5 "Cluster Review Intelligence & Competitive Benchmarking" — turn a tourism
cluster's reviews into aspect-level, competitive, time-aware intelligence, and
separate market-wide issues from property-specific ones. README-first MVP for the
AI–Tourism Hackathon 2026.

## Current objective
Polished, honest GitHub repo a judge can run in <5 min. README is the priority
deliverable (judges see the repo link, not the code).

## Architecture / state
`src/cri/`: schema → loader (PII dropped) → normalize → classify (rule/lexicon,
EN/Hinglish/Devanagari) → pipeline (labelled mentions) → benchmark (cluster
lead/lag, market-wide vs property-specific) + changepoint. Config: `aspects.yaml`.
Figures via `scripts/make_figures.py`; judge demo `scripts/demo.py`.

## Completed (implemented + verified)
- Phase 0: src layout, pyproject, ruff/pytest, Makefile, SECURITY/CONTRIBUTING/
  CoC, dependabot, CI + Scorecard workflows (actions pinned by SHA, fetched from
  the GitHub API — not guessed).
- Phase 1: schema + loader; seeded SYNTHETIC generator (12 properties, 5,124
  reviews, 2 injected patterns).
- Phase 2: normalisation + rule/lexicon aspect+sentiment; pluggable `Classifier`
  interface.
- Phase 3: cluster benchmark, market-wide vs property-specific, simple
  changepoint. 23 tests pass (recover both injected patterns). ruff clean.
- Phase 6: full README, 3 Mermaid diagrams, 4 SYNTHETIC figures, SVG banner.
- Phase 7: secret/PII/number scan clean; `docs/hardening.md` checklist.

## Verified
`python -m pytest` → 23 passed. `python -m ruff check .` → clean.
`python scripts/demo.py` recovers: Property F food changepoint @2025-06 (−1.24,
strongest); Room = market-wide (10/12 properties). Figures regenerate from seed=42.

## Not built — Roadmap (intentionally skipped per scope)
Streamlit dashboard; evaluation harness + real metrics (only a labelling template
+ TBD table exist); model backends (transformer/LLM); bootstrap CIs; PELT/
`ruptures`; CodeQL. All listed in README → Roadmap.

## Next tasks (tomorrow)
1. Push branch `feat/mvp-scaffold-readme`, open PR, make repo public so the
   Scorecard badge populates.
2. Enable branch protection + required reviews (see `docs/hardening.md`).
3. (Optional) start Streamlit dashboard; (optional) model backend behind the flag.
4. Hand-label real reviews (`docs/labelling_template.csv`) to replace eval TBDs.

## Known issues / honest caveats
- No real-world accuracy numbers yet (all `TBD` in `docs/TODO_RESULTS.md`).
- Changepoint detector has false positives (fixed threshold); only strongest
  shifts are reliable. See `docs/methodology.md` §6.
- Validation is on SYNTHETIC data only — proves plumbing, not real accuracy.

## Commands
`pip install -e ".[dev]"` · `pytest` · `ruff check .` ·
`python scripts/demo.py` · `python scripts/make_figures.py` ·
`python -m cri.generate --out data/sample/synthetic_reviews.csv`
