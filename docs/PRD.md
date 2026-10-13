# Product requirements: Cluster Review Intelligence

## Executive summary

Cluster Review Intelligence (AI–Tourism Hackathon 2026, problem statement G5) is
review intelligence for **one user: the hotel or homestay owner**. It answers **one
question**, asked before a fix and after it:

> When my reviews get worse on some aspect, is that **my** problem or the **whole
> market's**?

A single hotel cannot answer that from its own reviews. Answering it needs the
cluster of nearby competitors, and that is the moat.

**Positioning.** MakeMyTrip, Goibibo and Booking.com are demand side: they help a
traveller find a hotel. We are supply side: we sell to the properties listed on those
platforms and do not compete with them. Nobody at a booking platform tells a
Dhanaulti homestay owner that their food sentiment fell in June and that it is not the
market.

The same analysis also gives a tourism board a destination view.

> **Scope change 2026-10-13.** Mentors judged the earlier scope (travellers, providers,
> sellers and tourism boards at once) unfocused. The travel-intelligence layer
> (demand index, alternatives, stays, sellers, planner, region view) was removed. It is
> preserved at the git tag `travel-layer-v1`.

## Problem

1. **Star averages hide what is wrong.** Property F averages 3.28★ and Property I
   3.33★ (SYNTHETIC). One of them has a serious, recent food problem; the averages
   cannot say which.
2. **Owners cannot tell their problem from the market's.** A December dip in room
   sentiment may hit every property in the cluster. Renovating for it wastes money,
   and a plain before/after can blame the renovation for the weather.
3. **Owners do not know what to fix first** or since when it went wrong.

## Objectives and success metrics

| Objective | Metric | How it would be measured | Today |
|---|---|---|---|
| Owners act on the right problems | Share of priorities marked "yours alone" that owners act on | Pilot feedback | `TBD` |
| Fixes are judged fairly | Fix checks run per pilot property; verdicts owners agree with | Pilot feedback + `/fix-check` | `TBD` |
| Detectors are trustworthy | Recall on injected patterns; false alarms on pattern-free data | `python -m cri.calibration --seeds 1-20` | Food decline 15/20, December dip 20/20, false alarms 1/20 seeds (SYNTHETIC) |
| Model quality | Clause-level macro-F1 on hand-labelled reviews | `eval/score.py` | `TBD` (document-level results in AI_MODEL.md) |

No product metric is reported as achieved: there are no real users yet.

## Persona

| Persona | Needs | Main view |
|---|---|---|
| **Homestay owner** in Dhanaulti, 5 rooms (or the manager running a small hotel) | What guests complain about, since when, whether it is theirs or the market's, whether a fix worked | `/property`, `/market`, `/fix-check`, `/explorer` |

## Core user journey

1. **`/property`:** choose the property. The card says what to fix first and since
   when, e.g. *Fix Food first since 2025-06*. Each priority says **whose problem** it
   is: `yours alone`, `everyone's` or `not tested`, tested for that property.
2. **`/market`:** see which declines are market-wide and which belong to one
   property, with the worst market-wide aspect called out. Same chart, two opposite
   actions.
3. **`/fix-check`:** after a change, compare before and after **minus the market's
   change**. Example (SYNTHETIC, Property A, Room, 2025-12): plain before/after −1.38,
   market −0.95, relative to the market −0.43, no detectable change.
4. **`/explorer`:** read the reviews and the exact clause behind each label, or type a
   review (English, Hinglish or Devanagari) and classify it live.

## Scope

**MVP (built, see IMPLEMENTATION_PLAN.md):**

- Ingestion with reviewer identity dropped; Hinglish and Devanagari normalisation.
- Rule-based aspect and sentiment classifier (default); opt-in learned and transformer
  backends.
- Cluster benchmark with 95% CIs and FDR-controlled lead/lag flags.
- Changepoints relative to the market; market-wide patterns (seasonal and step).
- Priority actions with `whose_problem` derived per property.
- "Did my fix work?" market-adjusted before/after.
- Next.js static site (four pages) and a FastAPI service for live classification.

**Roadmap (not built):**

- Real partner review exports with dates; a clause-level gold set.
- Owner accounts with authentication and per-property access.
- Upload of a property's own review export.

**Out of scope:** traveller-facing features, bookings, payments, scraping, live
traffic claims.

## Business

See [BUSINESS_MODEL.md](BUSINESS_MODEL.md): one payer, the property owner. Every
price there is a labelled hypothesis.

## Assumptions, constraints and risks

| Item | Note |
|---|---|
| SYNTHETIC data | All bundled reviews are SYNTHETIC. Real-data accuracy is `TBD`. |
| Cluster size | "Whose problem" needs at least 3 properties reviewing the aspect; below that it is `not tested`. |
| Statistical power | Only large shifts are detected at a 5% false-discovery rate. |
| Review data provenance | The hill-review model stays local. The shipped model uses CC BY data only. |
| Deployment | A static site; the API is optional (live classify only). |

## Acceptance criteria (MVP)

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | An owner sees what to fix first, since when, ranked by gap × share of mentions. | `test_property_f_should_fix_food_first`, `test_ranking_is_by_impact_and_every_row_is_behind` |
| AC-2 | Each priority says whose problem it is, derived for that property, never copied from the aspect's market label. | `test_property_f_food_decline_is_its_own`, `test_a_year_round_room_gap_is_not_blamed_on_the_december_dip`, `test_a_lag_that_is_only_the_market_pattern_is_everyones` |
| AC-3 | Market-wide and property-specific declines are separated. | `test_same_chart_two_different_actions`, `test_market_patterns_are_only_the_injected_one` |
| AC-4 | A fix is judged relative to the market. | `test_a_market_wide_change_is_not_credited_to_the_property`, `test_demo_numbers` |
| AC-5 | Every label traces to its clause; typed reviews classify live. | `test_classify_text_shows_each_aspect_with_its_clause`, `test_classify_matches_the_core` |
| AC-6 | No secrets exposed; CORS restricted; input validated. | `test_cors_allows_only_configured_origins`, `test_classify_rejects_empty_and_oversized_text` |
| AC-7 | Every number the demo quotes is test-pinned. | `tests/test_demo.py` |
| AC-8 | README and docs match the code; CI runs Python tests and the web build. | `.github/workflows/ci.yml` |
