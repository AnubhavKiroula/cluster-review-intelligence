# Software requirements specification

## 1. System overview

The system is a Python analytics library (`src/cri`), served over HTTP by FastAPI
(`cri.server`) and used through a static Next.js frontend (`web/`). It has two
subsystems:

- **Review intelligence (G5):** review ingestion, classification, benchmark,
  changepoints, market scope, priorities and the fix check (`cri.api`; methodology
  in `docs/methodology.md`).
- **Travel intelligence:** demand index, alternatives, stays, provider insights,
  sellers, the region view and the planner (`cri.travel`).

Architecture is in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md), endpoints in
[API_CONTRACTS.md](API_CONTRACTS.md) and models in [AI_MODEL.md](AI_MODEL.md).

## 2. User roles and permissions

| Role | Can | Notes |
|---|---|---|
| Traveller (anonymous) | Read demand, alternatives, stays, sellers; create plans; classify text | No account; no personal data collected |
| Provider | Read their property's insights | MVP: any property selectable (SYNTHETIC data); production needs authentication with one property per account (NFR-SEC-4) |
| Tourism board | Read the region view and review issues | Same |
| Maintainer | Update resources and models through git | Data changes are reviewed in PRs |

## 3. Functional requirements

| ID | Requirement | Implementation | Test |
|---|---|---|---|
| FR-D1 | Compute a demand index 0–100 per destination and day as the sum of explained factors | `travel.demand.HeuristicDemandModel` | `test_index_equals_sum_of_factors_and_is_bounded` |
| FR-D2 | Use gazetted holidays from official lists with source and coverage; flag moon-dependent dates | `travel_facts.yaml`, `data.build` | `test_holiday_weekday_mismatch_is_rejected`, `test_facts_are_sourced_*` |
| FR-D3 | Detect long weekends (≥ 3 consecutive off-days that include a holiday) | `demand.long_weekends` | `test_christmas_2026_is_a_long_weekend_and_dussehra_is_not` |
| FR-D4 | State when a date is beyond holiday coverage | `HeuristicDemandModel.predict` notes | `test_beyond_coverage_*` |
| FR-D5 | Suggest quieter dates within ±7 days that are ≥ 10 points quieter | `demand.quieter_dates` | `test_quieter_dates_*` |
| FR-D6 | Allow a different demand model without changing callers | `DemandModel` protocol | `test_a_custom_demand_model_is_used` |
| FR-D7 | Show a regional overview and peak periods with drivers | `regional_overview`, `peak_periods` | `test_region_dashboard_covers_every_destination` |
| FR-A1 | Rank alternatives by weighted similarity × min(relief, headroom); exclude the origin | `alternatives.find_alternatives` | `test_alternatives_exclude_origin_*` |
| FR-A2 | Never suggest a place at or above its assumed ceiling; list exclusions with reasons | same | same |
| FR-A3 | Explain each suggestion: why busy, why similar, crowd, trade-off, limitations | same | same |
| FR-A4 | Accept similarity weights as input | `Weights`, `/alternatives?w_*` | `test_weights_change_the_ranking` |
| FR-S1 | Profile stays without star ratings: price, rooms, amenities, practices, suitability, aspect feedback, consistency | `stays.stay_profiles` | `test_stay_profiles_have_no_star_rating` |
| FR-S2 | Never label self-reported data as verified | `PROFILE_NOTE`, practice statuses | same |
| FR-P1 | Provider insights with "why" and evidence: review priorities, amenity gaps, demand peaks vs room mix, offer windows, sustainability | `stays.provider_insights` | `test_heating_insight_matches_review_search`, `test_property_f_food_decline_is_the_first_priority` |
| FR-L1 | List local sellers (no restaurants) with verification status | `region.sellers_for` | `test_sellers_exclude_restaurants_and_are_unverified` |
| FR-L2 | Estimate seller-category exposure, labelled "not sales" | `region.seller_opportunities` | `test_seller_opportunity_is_labelled_not_sales` |
| FR-T1 | Plan a trip: itinerary, stay, activities, sellers, traced costs, total and per person | `planner.plan_trip` | `test_plan_lines_add_up` |
| FR-T2 | Estimate travel carbon with sourced factors and show both modes | same | `test_plan_carbon_uses_the_sourced_factors` |
| FR-T3 | Offer lower-budget and lower-crowd variants | same | `test_plan_variants_are_cheaper_or_quieter` |
| FR-R1 | Tourism-board view: pressure vs ceilings, redistribution, under-served categories, G5 review issues | `region.region_dashboard` | `test_region_dashboard_covers_every_destination` |
| FR-C1 | Classify free text (English/Hinglish/Devanagari) into aspect, sentiment and clause | `api.classify_text`, `POST /reviews/classify` | `test_classify_matches_the_core` |
| FR-C2 | Offer a trained sentiment backend behind the same interface | `learned_backend`, `get_classifier("learned")` | `test_learned_backend_*`, `test_numpy_inference_matches_sklearn` |
| FR-G5 | All G5 review features remain available | `cri.api` + web pages | existing tests (`test_api.py`, `test_benchmark.py`, `test_demo.py`, …) |

## 4. Inputs, outputs and validation

| Input | Rule | On violation |
|---|---|---|
| `destination`, `origin`/`home`, `property_id` | Must exist in the resources | 404 with the valid options |
| `start` | ISO date | 422 |
| `days` | 1–120 (provider 7–120) | 422 |
| `nights` | 1–14 | 422 |
| `travellers` | 1–12 | 422 |
| `budget` | 0 < budget ≤ 10,000,000 INR | 422 |
| `interests` | ≤ 10, each a known tag | 422 |
| `stay_pref`, `transport` | Enumerations | 422 |
| `w_*` weights | 0–1 each, not all 0 | 422 |
| `text` (classify) | 1–2,000 characters | 422 |
| Resource files | Source keys exist; holiday weekdays match dates; SYNTHETIC label present; references resolve; season curves have 12 values in 0..1 | Start-up fails with a message |

**Outputs:** JSON, ISO dates, integer INR, and Evidence objects with `basis`. There
is no NaN (it becomes `null`).

## 5. Interfaces and dependencies

- **HTTP API:** see API_CONTRACTS.md.
- **Web client:** `NEXT_PUBLIC_API_BASE_URL`, fixed at build time.
- **Python:** 3.11–3.12. Pinned dependencies:

  | Group | Pins |
  |---|---|
  | core | numpy 1.26.2, pandas 2.1.3, pyyaml 6.0.3 |
  | `api` | fastapi 0.143.0, uvicorn 0.54.0 |
  | `train` | scikit-learn 1.9.1, scipy 1.16.3 |
  | `dev` | pytest, ruff, matplotlib, httpx |

- **Node:** 22. Next 14.2.15, React 18.3.1, Plotly.js 2.35.2 (pinned in
  `web/package.json`).
- **No runtime calls to external services.** Facts are versioned files.

## 6. Non-functional requirements

| ID | Requirement | How met |
|---|---|---|
| NFR-HON-1 | No fabricated results; unknowns are `TBD` | Evidence basis; TODO_RESULTS.md; tests check labels |
| NFR-HON-2 | SYNTHETIC data labelled in filenames, API and UI | `travel_synthetic.yaml` label check; banners |
| NFR-HON-3 | Demand never described as live traffic | Notes on every day; UI banner |
| NFR-SEC-1 | No secrets in git; config by env vars | `.env.example`, `.gitignore` |
| NFR-SEC-2 | CORS restricted to configured origins; GET/POST only; no credentials | `cri.server`, `test_cors_allows_only_configured_origins` |
| NFR-SEC-3 | Models load without executing code | `.npz` with `allow_pickle=False` |
| NFR-SEC-4 | Before real provider data: authentication, per-property authorisation, rate limiting | Roadmap (not in the MVP) |
| NFR-PRIV-1 | No reviewer identity stored or loaded | `schema.drop_identity_columns`; `prepare_region_reviews` reads only text and rating (tested) |
| NFR-PRIV-2 | Real hotels anonymised; real review text and models trained on it never committed | gitignored `data/raw/` |
| NFR-PERF-1 | Typical API calls under 1 s on a laptop | Measured locally (2026-10-13): most endpoints ≤ 0.3 s; `/provider` and `/plan` ≈ 0.6–1.3 s |
| NFR-REL-1 | G5 pages work if the API is down; travel pages show a clear error state | `ApiErrorState`; verified headlessly |
| NFR-REP-1 | Reproducible models and metrics | Seeds, pinned data revisions, `scripts/train_sentiment.py` |
| NFR-MAINT-1 | ruff clean, tests in CI for Python and web | `.github/workflows/ci.yml` |
| NFR-A11Y-1 | Labelled form controls, keyboard-usable buttons, colour plus text for categories | Pages use `<label htmlFor>` and text category names |

## 7. Error handling

- **Engines** raise `UnknownIdError` (→ 404) or `ValueError` (→ 422) with the valid
  options.
- **Web client** times out after 15 s and shows the API URL and the command to start
  it.
- **Resource validation errors** stop start-up rather than serve wrong data.

## 8. Acceptance tests

Run with `python -m pytest`; the web app is checked with `npx tsc --noEmit` and
`npm run build`. Traceability is in the table in §3. The headless browser check of
all pages is described in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
