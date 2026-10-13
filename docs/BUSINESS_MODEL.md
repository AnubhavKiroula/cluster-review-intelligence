# Business model

**Status: hypotheses.** Every price, cost and conversion below is an assumption to
be validated with interviews and pilots. None is measured, and market sizes are
`TBD` until sourced. The model is designed to stay affordable for small providers,
sellers and students, and to avoid depending on booking commissions.

## Business Model Canvas

| Block | Content |
|---|---|
| **Customer segments** | (1) Small accommodation providers: homestays, guesthouses, camps, small hotels. (2) Local sellers and experience providers: artisans, weavers, guides. (3) Tourism boards, district administrations and hotel associations. (4) Travellers: students, families, budget and eco-minded visitors (free users). |
| **Value propositions** | Providers: "what to fix, since when, and is it you or the market", plus demand peaks against your room mix, and whether a fix worked. Sellers: being found in trip plans in the right season. Boards: expected pressure against capacity, redistribution, destination-wide review issues. Travellers: quieter dates, similar places, star-free stays, honest cost and carbon estimates. |
| **Channels** | Free traveller web app (SEO for "<destination> long weekend crowd"); district tourism offices and homestay schemes; hotel and homestay associations; college travel clubs; WhatsApp-based onboarding for sellers. |
| **Customer relationships** | Self-serve for travellers and basic listings; assisted onboarding and quarterly review calls for paid providers; dashboards plus a named analyst for boards. |
| **Revenue streams** | Provider analytics subscriptions; tourism-board and association dashboards (B2G/B2B); later, capped and disclosed referral fees on real transactions; clearly labelled promoted listings that never change trust indicators. |
| **Key resources** | Review-analytics engine and its methodology; sourced holiday/distance/emission data; verified provider and seller records (to be built); trust. |
| **Key activities** | Onboarding and verifying providers and sellers; data partnerships (review exports, arrivals); model evaluation (gold labelling); field validation of the demand index. |
| **Key partners** | Uttarakhand Tourism Development Board and HP Tourism (data, distribution); homestay and hotel associations; NGOs and self-help groups working with artisans; universities (labelling, evaluation). |
| **Cost structure** | Hosting (static site + small API); data acquisition and verification field work; onboarding staff; model evaluation; support. |

## Revenue streams (hypotheses)

| Stream | Who pays | Hypothesis | Guardrail |
|---|---|---|---|
| Free basic listing | Nobody | Profile, aspect feedback, appears in plans and alternatives | Ranking never depends on payment |
| Provider Insights plan | Provider | ₹499–₹999 per month: insights, fix check, demand peaks, competitor-neutral benchmark | Cancel any time; first season free during pilots (hypothesis) |
| Association / board dashboard | Board, association | ₹1–3 lakh per year per district or cluster: region view, review issues, exports, analyst support | Aggregates only; no individual reviewer data |
| Referral fee (later) | Provider, on a completed booking | ≤ 5%, capped per booking, shown to the traveller | Only once real inventory and transactions exist |
| Promoted placement (later) | Provider, seller | Fixed monthly fee, marked "Promoted" | Never affects demand index, alternatives ranking, feedback or sustainability labels |

## Unit economics (illustrative)

Every input is a hypothesis to validate, not a measurement.

**Provider plan:**

| Line | Hypothesis | Notes |
|---|---|---|
| Price | ₹699 per month | Midpoint of the band |
| Gross margin after hosting and support | ~80% | API and static site are cheap; support time dominates |
| Acquisition cost | ₹1,500 per paying provider | Association partnership plus a field visit |
| Payback | 1,500 / (699 × 0.8) ≈ 2.7 months | |
| Annual churn | 30% (seasonal businesses) | |
| 12-month gross profit per provider | ≈ ₹6,700 | |

**Region dashboard:**

| Line | Hypothesis |
|---|---|
| Price | ₹2 lakh per year |
| Analyst time | 6 days per year |
| Data refresh | 1 day per quarter |

Gross margin depends mainly on analyst cost (to be measured in a pilot).

Break-even depends on fixed team cost, which is `TBD`. Formula:
`fixed cost ÷ (paying providers × monthly margin + boards × annual margin / 12)`.

## Keeping it affordable

- Travellers never pay. The core traveller features are free.
- Small providers and sellers get a free listing with their review-based profile.
  Paid analytics start below the price of one room-night per month.
- Seasonal pause: a provider can pause the plan in the off-season.
- No commission dependency. The product earns from analytics, so it has no incentive
  to push travellers to the busiest or most expensive places.

## Provider and seller onboarding

1. Partner with an association or district office for an introduction session.
2. A provider claims their listing with phone OTP (to be built) and uploads their
   review export, or connects partner data where permitted. No scraping.
3. Verification of a few items (e.g. a waste-segregation practice) by photo or a
   field visit. Until verified, items show as "self-reported".
4. A seller profile is created in a 10-minute assisted session: category, offering,
   price range, location. It stays "unverified" until a partner NGO or office
   confirms it.

## Competitive differentiation

| Typical OTA or review site | This product |
|---|---|
| Star average | Aspect-level feedback with confidence intervals; "is it you or the market" |
| Pushes popular inventory | Steers away from crowded places and dates, with a capacity guard |
| Commission-driven ranking | Ranking never paid; promoted items labelled |
| Restaurants and big hotels dominate | Local artisans, weavers and guides inside trip plans |
| Opaque | Every number shows its basis (fact / measured / derived / synthetic / assumption) |

Validating this against existing booking platforms and destination apps needs a
structured competitor review (`TBD`).

## Impact metrics and how they would be measured

| Metric | Estimate today | How to measure for real |
|---|---|---|
| Visitor pressure moved away from places at or over their ceiling | Planner variants and alternatives (estimate) | Adoption of variants (telemetry), then partner occupancy on peak days |
| Local-business discovery | Seller impressions in plans (estimate) | Seller-reported enquiries and sales (self-reported, then sampled) |
| Share of trip spend reaching local businesses | Seller and experience lines in plans (estimate) | Traveller survey plus seller reports; never inferred from simulated data |
| Occupancy spread across periods | — | Provider occupancy before and after offers in low-demand windows |
| Sustainability practices adopted | Reported practices per listing | Verified practices per listing over time |

## Risks and validation plan

| Risk | Validation |
|---|---|
| Providers will not pay | 10 interviews plus a 2-month free pilot with 15 homestays; target ≥ 30% conversion to paid (hypothesis) |
| Boards prefer in-house tools | 2 district pilots with an exported report; measure whether decisions cite it |
| Data access (review exports, arrivals) | MoUs with an association and UTDB; fall back to provider-uploaded exports |
| Trust in estimates | Keep Evidence labels; publish methodology; collect "was this useful" feedback per insight |
| Seasonality of revenue | Annual board contracts plus pause-able provider plans |
| Legal or data provenance | Only permitted data; no scraping; anonymise properties in public views |
