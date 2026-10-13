# Software requirements specification

## 1. System overview

The system is a Python analytics library (`src/cri`) used through a static Next.js
frontend (`web/`). It serves one user, the hotel or homestay owner, and one question:
is a decline on some aspect this property's problem or the whole market's?

- **Review intelligence:** ingestion, classification, benchmark, changepoints, market
  scope, priorities with "whose problem", and the fix check (`cri.api`; methodology in
  `docs/methodology.md`).
- **Web app:** four pages (`/property`, `/market`, `/fix-check`, `/explorer`) that read
  a static snapshot exported by `web/scripts/export_snapshot.py`.
- **HTTP API (`cri.server`, optional):** live classification of typed reviews for the
  explorer.

The travel-intelligence layer was removed on 2026-10-13 (git tag `travel-layer-v1`).
Architecture is in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md), endpoints in
[API_CONTRACTS.md](API_CONTRACTS.md) and models in [AI_MODEL.md](AI_MODEL.md).

## 2. User roles and permissions

| Role | Can | Notes |
|---|---|---|
| Owner or manager | Read their property's scorecard, priorities, trends, fix checks and reviews; classify text | MVP: any property selectable (SYNTHETIC data); production needs authentication with one property per account (NFR-SEC-4) |
| Maintainer | Update resources, models and the snapshot through git | Data changes are reviewed in PRs |

## 3. Functional requirements

| ID | Requirement | Implementation | Test |
|---|---|---|---|
| FR-I1 | Ingest CSV/JSON(L) reviews; validate the schema; drop reviewer identity | `loader`, `schema`, `sources` | `test_loader_roundtrip_drops_pii`, `test_explicit_mapping_adapts_and_drops_identity` |
| FR-C1 | Classify free text (English/Hinglish/Devanagari) into aspect, sentiment and clause | `api.classify_text`, `POST /reviews/classify` | `test_classify_text_shows_each_aspect_with_its_clause`, `test_classify_matches_the_core` |
| FR-C2 | Offer a trained sentiment backend behind the same interface | `learned_backend`, `get_classifier("learned")` | `test_learned_backend_is_hybrid_with_packaged_model`, `test_numpy_inference_matches_sklearn` |
| FR-B1 | Score each property-aspect against the cluster with a 95% CI and FDR-controlled lead/lag flags | `benchmark.benchmark_vs_cluster` | `test_flags_never_contradict_the_interval_shown`, `test_lead_lag_flags_are_fdr_controlled_on_a_null_cluster` |
| FR-B2 | Detect changepoints relative to the market, with the month they began | `benchmark.detect_changepoints` | `test_recovers_property_f_food_changepoint`, `test_delta_vs_market_differs_from_raw_delta` |
| FR-B3 | Detect market-wide patterns (seasonal dips, step declines) across properties | `benchmark.detect_market_patterns` | `test_december_room_dip_affects_majority`, `test_market_wide_step_is_market_wide_not_blamed_on_a_property` |
| FR-B4 | Label each aspect's negative shifts `market-wide`, `property-specific` or `undetermined` | `api.market_scope` | `test_same_chart_two_different_actions`, `test_two_property_cluster_is_undetermined` |
| FR-P1 | Rank what to fix first: gap × share of mentions, only for evidenced, worse aspects | `insights.priority_actions` | `test_property_f_should_fix_food_first`, `test_ranking_is_by_impact_and_every_row_is_behind` |
| FR-P2 | Say whose problem each priority is (`yours alone` / `everyone's` / `not tested`), derived **per property**: a market-adjusted decline is the property's own; a lag is re-tested with the market-wide patterns the property takes part in set aside | `insights._whose_problem` | `test_property_f_food_decline_is_its_own`, `test_a_year_round_room_gap_is_not_blamed_on_the_december_dip`, `test_a_lag_that_is_only_the_market_pattern_is_everyones`, `test_two_property_cluster_does_not_claim_a_market_comparison`, `test_a_two_property_cluster_never_claims_whose_problem_it_is` |
| FR-F1 | "Did my fix work?": before/after minus the market's change, with CI, placebo rank and minimum detectable effect | `api.intervention_check` | `test_a_market_wide_change_is_not_credited_to_the_property`, `test_a_real_fix_is_found_with_the_right_size`, `test_demo_numbers` |
| FR-S1 | Search reviews by property, aspect, sentiment, dates and text, with the matched clause | `api.search_reviews` | `test_search_filters_on_classified_clauses` |
| FR-D1 | Destination summary per aspect (used by `/market`) | `api.destination_summary` | `test_destination_summary_labels_each_aspect` |
| FR-W1 | The web app shows these four pages from a static snapshot, without the API | `web/`, `export_snapshot.py` | CI web job (`tsc`, `next build`); headless browser run |

## 4. Inputs, outputs and validation

| Input | Rule | On violation |
|---|---|---|
| `property_id`, `aspect` (Python facade) | Must exist in the data / taxonomy | `ValueError` naming the valid options |
| `top_n` | Positive integer | `ValueError` |
| `start` (fix check) | After the first month of data, no later than the last | `ValueError` |
| `text` (classify) | 1–2,000 characters | 422 |

**Outputs:** DataFrames with documented columns (`cri.api`); JSON over HTTP. There is
no NaN in JSON (it becomes `null`).

## 5. Interfaces and dependencies

- **HTTP API:** `GET /health`, `POST /reviews/classify`; see API_CONTRACTS.md.
- **Web client:** `NEXT_PUBLIC_API_BASE_URL`, fixed at build time; used only for live
  classification.
- **Python:** 3.11–3.12. Pinned dependencies:

  | Group | Pins |
  |---|---|
  | core | numpy 1.26.2, pandas 2.1.3, pyyaml 6.0.3 |
  | `api` | fastapi 0.143.0, uvicorn 0.54.0 |
  | `train` | scikit-learn 1.9.1, scipy 1.16.3 |
  | `dev` | pytest, ruff, matplotlib, httpx |

- **Node:** 22. Next 14.2.15, React 18.3.1, Plotly.js 2.35.2 (pinned in
  `web/package.json`).
- **No runtime calls to external services.**

## 6. Non-functional requirements

| ID | Requirement | How met |
|---|---|---|
| NFR-HON-1 | No fabricated results; unknowns are `TBD` | TODO_RESULTS.md; demo claims pinned by `tests/test_demo.py` |
| NFR-HON-2 | SYNTHETIC data labelled in filenames, figures and UI | `synthetic` in snapshot filenames; banner on every page (**hidden in the web app for now**, see TODO_RESULTS.md); `test_default_load_is_labelled_synthetic` |
| NFR-HON-3 | A market-wide label is never shown as a property's verdict without a per-property test | FR-P2 tests |
| NFR-STAT-1 | False alarms controlled: FDR q = 0.05 per test family | `test_null_data_has_no_changepoints_or_market_patterns`, calibration (1/20 pattern-free seeds with a false alarm) |
| NFR-SEC-1 | No secrets in git; config by env vars | `.env.example`, `.gitignore` |
| NFR-SEC-2 | CORS restricted to configured origins; GET/POST only; no credentials | `cri.server`, `test_cors_allows_only_configured_origins` |
| NFR-SEC-3 | Models load without executing code | `.npz` with `allow_pickle=False`; `test_model_file_round_trip_without_pickle` |
| NFR-SEC-4 | Before real owner data: authentication, per-property authorisation, rate limiting | Roadmap (not in the MVP) |
| NFR-PRIV-1 | No reviewer identity stored or loaded | `schema.drop_identity_columns`; `test_drop_identity_columns` |
| NFR-PRIV-2 | Real hotels anonymised; real review text and models trained on it never committed | gitignored `data/raw/` |
| NFR-REL-1 | Every page works if the API is down; live classify shows a clear error | Snapshot pages; explorer error state |
| NFR-REP-1 | Reproducible results | Seeds; `python -m cri.calibration --seeds 1-20`; `scripts/demo.py` |
| NFR-MAINT-1 | ruff clean, tests in CI for Python and web | `.github/workflows/ci.yml` |
| NFR-A11Y-1 | Labelled form controls, keyboard-usable buttons, colour plus text for verdicts | `<label htmlFor>`; verdict pills carry text |

## 7. Error handling

- **Facade** raises `ValueError` with the valid options for unknown ids or bad
  arguments; empty results are empty frames with the documented columns.
- **API** returns 422 for invalid input.
- **Web client** times out live classification after 15 s and shows the command to
  start the API.

## 8. Acceptance tests

Run with `python -m pytest`; the web app is checked with `npx tsc --noEmit` and
`npm run build`. Traceability is in the table in §3. The headless browser check of
the four pages is described in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
