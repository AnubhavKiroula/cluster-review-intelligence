# Product requirements: Cluster Review Intelligence + hill-travel intelligence

## Executive summary

Cluster Review Intelligence (AI–Tourism Hackathon 2026, problem statement G5)
turns a tourism cluster's reviews into aspect-level, market-aware intelligence. It
tells a hotel manager *what* is wrong, *since when*, and whether it is *their*
problem or the *whole market's*.

This release puts that review evidence to work for four groups in Uttarakhand and
Himachal hill destinations:

- **Travellers:** holiday-aware crowd estimates, quieter dates and similar
  less-crowded places, star-free stay comparison, and a budget trip planner with
  local sellers and a carbon estimate.
- **Accommodation providers:** explained improvement priorities, demand peaks against
  their room mix, and quiet windows for offers.
- **Local sellers:** discovery inside trip plans, and category-level opportunity
  estimates.
- **Tourism boards:** expected pressure against assumed capacity ceilings,
  redistribution options, under-served seller categories and destination-wide review
  issues.

Everything is honest about its evidence. Profiles, prices and sellers are SYNTHETIC.
Holidays, distances, arrivals and emission factors are sourced facts. Demand is an
indicative estimate, never live traffic.

## Problem

1. **Uneven demand.** Popular hill stations get overcrowded on long weekends and in
   season, which strains roads, water and waste systems. Similar places nearby stay
   under-used.
2. **Star ratings hide what matters.** A 4.1★ stay can be failing on food or heating.
   Travellers cannot compare on what they care about, and providers cannot see which
   problem is theirs and which is the destination's (G5).
3. **Providers plan blind.** Small hotels and homestays do not see demand peaks or
   their amenity gaps coming.
4. **Little of the spending reaches local businesses.** Visitors rarely find artisans,
   woollen weavers or guides beyond the main market.
5. **Students and budget travellers** lack an easy way to find affordable, quieter,
   lower-carbon options.

## Objectives and success metrics

| Objective | Metric | How it would be measured | Today |
|---|---|---|---|
| Spread visitor pressure | Share of planner trips moved to a quieter date or alternative | Count variant adoptions (needs telemetry) | `TBD` |
| Better stay decisions without stars | Share of users opening aspect feedback before choosing | UI analytics | `TBD` |
| Providers act on evidence | Insights marked "done"; later change relative to the market (fix check) | Provider feedback + G5 intervention check | `TBD` |
| More local-business discovery | Seller profile views and contacts per trip plan | Analytics + seller reports | `TBD` |
| Estimated local spend share | Planner spend lines that go to local sellers and experiences | From plans (an estimate, not sales) | `TBD` |
| Model quality | Clause-level macro-F1 on hand-labelled hill reviews | `eval/score.py` | `TBD` (document-level results in AI_MODEL.md) |

No metric is reported as achieved: there are no real users yet.

## Personas

| Persona | Needs | Main view |
|---|---|---|
| **Riya**, engineering student in Delhi, ₹6–8k per trip | Cheap, safe, not-crowded weekend trips; transparent costs | `/explore`, `/plan` |
| **The Negi family**, Dehradun, travelling in school holidays | Family rooms, quieter dates, heating that works | `/explore` stays, `/plan` |
| **Homestay owner** in Kanatal, 5 rooms | What guests complain about, when demand is coming, whether a fix worked | `/provider`, `/property`, `/fix-check` |
| **Handicraft seller** in Kausani | Being found by visitors in season | listed in `/plan`; gaps in `/region` |
| **District tourism officer** | Where pressure will exceed capacity; what is a destination-wide problem | `/region`, `/destination`, `/market` |

## Core user journeys

1. **Traveller:** choose a destination and dates on `/explore`. See the crowd category
   and why. Pick a quieter date or a similar place. Compare stays on aspect feedback.
   Continue to `/plan`.
2. **Trip planning:** set the budget, travellers, interests and transport. Get an
   itinerary with traced costs, car vs bus carbon, and local sellers. Switch to a
   cheaper or quieter variant.
3. **Provider:** choose a property on `/provider`. See review priorities, amenity
   gaps, peaks against room mix and offer windows. Open `/property` for the full
   scorecard and `/fix-check` after making a change.
4. **Tourism board:** choose a window on `/region`. See pressure against ceilings,
   peaks and their drivers, redistribution options, under-served seller categories
   and destination-wide review issues.

## Scope

**MVP (built, see IMPLEMENTATION_PLAN.md):**

- **G5 review analytics:** benchmark, changepoints, market scope, priorities, fix
  check, explorer, live classify.
- **Demand calendar:** gazetted holidays 2026–27, long weekends, assumed school and
  year-end windows, demand index with factors, quieter dates, regional overview.
- **Alternatives:** similarity, capacity guard and five-part explanations.
- **Stays and providers:** star-free stay profiles; provider insights.
- **Sellers:** local sellers (no restaurants) and seller opportunity.
- **Planner:** itinerary, costs, carbon and variants.
- **Learned sentiment:** an opt-in model trained on open Hinglish data, plus a local
  model on hill-destination reviews.
- **Platform:** FastAPI service; Next.js as the only UI; CI for Python and web.

**Roadmap (not built):**

- Real data:
  - partner review exports with dates;
  - monthly arrivals;
  - provider and seller onboarding with verification.
- Learning and forecasting:
  - a clause-level gold set;
  - a trained demand model once footfall exists.
- Live context: weather and road-status integrations, labelled as live only when they
  are.
- Provider and seller accounts with authentication.
- Booking and referral, only with real inventory and transparent fees.

**Out of scope:** live traffic claims, payments, scraping, restaurant marketplace.

## Business and sustainability goals

See [BUSINESS_MODEL.md](BUSINESS_MODEL.md):

- free listings for small providers and sellers;
- affordable provider analytics subscriptions;
- dashboards for tourism boards and associations;
- capped, disclosed referral fees only once real transactions exist.

## Assumptions, constraints and risks

| Item | Note |
|---|---|
| No real demand data | Demand is a transparent heuristic, and the app says so. Validation plan in AI_MODEL.md. |
| SYNTHETIC profiles | All stays, prices and sellers are illustrative. Real onboarding is needed. |
| Capacity unknown | Ceilings are assumptions. |
| Review data provenance | The hill-review model stays local. The shipped model uses CC BY data only. |
| Two-process deployment | API + static site. The G5 pages work without the API. |
| Hackathon time | Vertical slices; cut lines in IMPLEMENTATION_PLAN.md. |

## Acceptance criteria (MVP)

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | A traveller selects destination and dates and sees a 0–100 index, a category, every factor with its source, and a "not live traffic" note. | `tests/test_travel.py`, `tests/test_server.py`, headless browser run |
| AC-2 | The calendar marks gazetted holidays and long weekends from the official lists, with coverage stated. | tests (weekday check, Christmas long weekend) |
| AC-3 | Alternatives are ranked by implemented logic: the origin is excluded, the capacity guard applies, and weights change the ranking. | `test_alternatives_*`, `test_weights_change_the_ranking` |
| AC-4 | Stay profiles have no star rating. Amenities and practices are labelled self-reported. | `test_stay_profiles_have_no_star_rating` |
| AC-5 | Providers see insights, each with a reason and evidence, including review priorities and demand gaps. | `test_heating_insight_*`, `test_property_f_*` |
| AC-6 | Local sellers (no restaurants) are listed and discoverable in plans. | `test_sellers_*`, `/plan` |
| AC-7 | The planner returns an itinerary whose costs add up, carbon from sourced factors, and cheaper/quieter variants. | `test_plan_*` |
| AC-8 | Estimates disclose their limitations in the UI and API. | banners, notes, Evidence basis |
| AC-9 | No secrets exposed; CORS restricted; inputs validated. | `test_server.py`, `.env.example` |
| AC-10 | README and docs match the code; CI runs Python tests and the web build. | `.github/workflows/ci.yml` |
