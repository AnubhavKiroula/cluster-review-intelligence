# Business model

**Status: hypotheses.** Every price, cost and conversion below is an assumption to
be validated with interviews and pilots. None is measured, and market sizes are
`TBD` until sourced.

## One payer, one question

**The payer is the hotel or homestay owner** (or the manager who runs the property).
The product answers one question for them, before a fix and after it: *when my
reviews get worse on some aspect, is that my problem or the whole market's?* A single
hotel cannot answer it from its own reviews; it needs the cluster of nearby
competitors. That is the moat.

**Positioning.** MakeMyTrip, Goibibo and Booking.com are demand side: they help a
traveller find a hotel. We are supply side: we sell to the properties listed on those
platforms and do not compete with them. The same analysis also gives a tourism board
a destination view; that is not a second product.

> **Scope change 2026-10-13.** Revenue from travellers, sellers and tourism boards was
> dropped with the travel-intelligence layer (preserved at the git tag
> `travel-layer-v1`).

## Business Model Canvas

| Block | Content |
|---|---|
| **Customer segment** | Small hotels, homestays and guesthouses in a tourism cluster (a hill town or a belt of nearby towns). |
| **Value proposition** | "What to fix first, since when, and is it you or the market", plus "did my fix work, relative to the market". |
| **Channels** | Hotel and homestay associations; district tourism offices and homestay schemes (for introductions only); word of mouth inside a cluster. |
| **Customer relationship** | Assisted onboarding; a short review call each season. |
| **Revenue stream** | A subscription per property (hypothesis below). |
| **Key resources** | The review-analytics engine and its methodology; enough properties per cluster to form a market; trust. |
| **Key activities** | Onboarding properties with their review exports; model evaluation (gold labelling); support. |
| **Key partners** | Hotel and homestay associations; universities (labelling, evaluation). |
| **Cost structure** | Hosting (static site + small API); onboarding and support time; model evaluation. |

## Revenue (hypothesis)

| Stream | Who pays | Hypothesis | Guardrail |
|---|---|---|---|
| Owner analytics plan | The property owner | ₹499–₹999 per month: priorities with whose problem, market view, fix check, review explorer | Cancel any time; pause in the off-season; first season free during pilots (hypothesis) |

There are no traveller fees, referral fees or paid placements: the product earns from
analytics, so it has no incentive to favour any property.

## Unit economics (illustrative)

Every input is a hypothesis to validate, not a measurement.

| Line | Hypothesis | Notes |
|---|---|---|
| Price | ₹699 per month | Midpoint of the band |
| Gross margin after hosting and support | ~80% | The static site and API are cheap; support time dominates |
| Acquisition cost | ₹1,500 per paying property | Association partnership plus a field visit |
| Payback | 1,500 / (699 × 0.8) ≈ 2.7 months | |
| Annual churn | 30% (seasonal businesses) | |
| 12-month gross profit per property | ≈ ₹6,700 | |

Break-even depends on fixed team cost, which is `TBD`. Formula:
`fixed cost ÷ (paying properties × monthly margin)`.

**Cluster constraint.** The answer needs a market: at least 3 properties reviewing an
aspect, and more for market-wide patterns. A cluster's first customers therefore need
their competitors' public reviews in the analysis (from permitted exports, never
scraping), which is a data-access risk below.

## Onboarding

1. Partner with an association for an introduction session in one cluster.
2. An owner shares their review export (or permitted partner data). No scraping.
3. The first report shows what to fix first and whose problem each item is.
4. After a fix, the owner runs the fix check at the next review.

## Competitive differentiation

| Booking platform or review site | This product |
|---|---|
| Serves the traveller (demand side) | Serves the property (supply side) |
| Star average | Aspect-level scores with confidence intervals |
| Shows a property its own reviews | Separates the property's problem from the market's, tested per property |
| Before/after at best | Fix check relative to the market, with a placebo rank |

Validating this against existing hotel-analytics tools needs a structured competitor
review (`TBD`).

## Impact metrics and how they would be measured

| Metric | Today | How to measure for real |
|---|---|---|
| Owners act on "yours alone" priorities | `TBD` | Pilot feedback per priority |
| Money not spent on market-wide problems | `TBD` | Owner interviews after a season |
| Fixes confirmed relative to the market | `TBD` | Fix-check verdicts in pilots |

## Risks and validation plan

| Risk | Validation |
|---|---|
| Owners will not pay | 10 interviews plus a 2-month free pilot with 15 homestays; target ≥ 30% conversion to paid (hypothesis) |
| Too few properties per cluster to form a market | Start where an association covers most properties of one town |
| Data access (review exports) | MoU with an association; fall back to owner-uploaded exports |
| Trust in the verdicts | Every verdict shows why; methodology published; "was this useful" feedback per priority |
| Seasonality of revenue | Pause-able plans |
| Legal or data provenance | Only permitted data; no scraping; anonymise properties in public views |
