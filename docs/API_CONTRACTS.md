# API contracts

Two interfaces:

1. **HTTP API** (`src/cri/server.py`, FastAPI): what the Next.js frontend calls.
   Interactive OpenAPI docs at `http://localhost:8000/docs`.
2. **Python facade** (`cri.api`, G5 review analytics): the frozen contract in
   `docs/HACKATHON_PLAN.md` §3.2, unchanged except the additions noted below.

All examples are real responses from the running API on 2026-10-13 (SYNTHETIC
review cluster, seed 42), trimmed with `…` where long.

## Running

```bash
python -m pip install -e ".[api]"
uvicorn cri.server:app --port 8000
```

| Env var | Default | Effect |
|---|---|---|
| `CRI_API_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Browser origins allowed (comma-separated). GET/POST only, no credentials. |
| `CRI_MODEL_BACKEND` | `rule` | Classifier for `/reviews/classify` and the review cluster: `rule`, `learned`, `transformer` |
| `CRI_LEARNED_MODEL_PATH` | packaged open model | Model file for the `learned` backend |

The server loads the SYNTHETIC review cluster and the travel resources once at
start-up (about 2 s) and keeps them in memory.

## Conventions

- JSON in and out; dates are ISO `YYYY-MM-DD`; money is integer INR.
- Every displayed number of the travel layer is an **Evidence** object:
  `{"label", "value", "basis", "detail"}` where `basis` ∈ `fact | measured | derived |
  synthetic | assumption`.
- `NaN` never reaches JSON: missing statistics are `null`.
- Errors: `404 {"detail": "Unknown destination 'x'; available: …"}` for unknown ids
  (destination, origin, property); `422 {"detail": …}` for invalid input (FastAPI
  validation list, or a message string from the engines).

## Endpoints

| Method + path | Parameters (limits) | Returns |
|---|---|---|
| `GET /health` | — | status, SYNTHETIC flag, classifier backend, demand model |
| `GET /meta` | — | destinations (+ profile), origins, properties, interests, seller categories, holidays with sources, assumed windows, weights, ceilings, costs, road factor, emission factors, sources |
| `GET /demand/calendar` | `destination`, `start`, `days` (1–120, default 30) | list of DemandDay |
| `GET /demand/trip` | `destination`, `start`, `nights` (1–14, default 2) | trip demand, top drivers, quieter dates (±7 days) |
| `GET /demand/overview` | `start`, `days` (1–120) | per destination: mean index, peak day, days per category |
| `GET /alternatives` | `destination`, `start`, `nights` (1–14), `home` (origin id, default `delhi`), `top_n` (1–10, default 3), `w_landscape`, `w_activities`, `w_budget`, `w_travel`, `w_season` (each 0–1, not all 0) | ranked alternatives with components and five explanations; excluded candidates with reasons |
| `GET /stays` | `destination` (optional) | star-free stay profiles |
| `GET /provider/{property_id}/insights` | `start`, `days` (7–120, default 90) | profile + ranked insights |
| `GET /sellers` | `destination`, `category` (optional) | sellers |
| `GET /sellers/opportunities` | `destination`, `start`, `days` (1–120, default 60) | category exposure scores |
| `GET /region` | `start`, `days` (1–120, default 30) | pressure per destination, under-served seller categories, G5 review issues, notes |
| `POST /plan` | PlanRequest (below) | TripPlan |
| `POST /reviews/classify` | `{"text": str}` (1–2,000 chars) | backend name + mentions |

### `GET /demand/calendar?destination=mussoorie&start=2026-12-25&days=1`

```json
[{
  "day": "2026-12-25", "index": 87, "category": "Very High", "borderline": false,
  "factors": [
    {"label": "Popularity tier", "value": 30, "basis": "assumption",
     "detail": "high tier: UTDB 2023: 1,471,913 arrivals (travel_facts.yaml)"},
    {"label": "Season", "value": 22, "basis": "synthetic",
     "detail": "25 x 0.9 (assumed season curve, December)"},
    {"label": "Gazetted holiday", "value": 10, "basis": "fact",
     "detail": "Christmas Day: Gazetted holidays 2026 for Central Government offices in Uttarakhand, CGEWCC Dehradun, as per DoPT O.M. F.No.12/2/2023-JCA dated 03.07.2025"},
    {"label": "Long weekend", "value": 15, "basis": "derived",
     "detail": "3 consecutive days off (Fri 25 Dec - Sun 27 Dec) including Christmas Day"},
    {"label": "Year-end holidays (assumed)", "value": 10, "basis": "assumption",
     "detail": "Christmas to New Year travel peak; an assumption, not an official holiday"}
  ],
  "notes": ["Indicative estimate of relative visitor pressure, not live traffic or bookings."]
}]
```

`index` always equals the sum of `factors[].value`.

### `GET /demand/trip?destination=mussoorie&start=2026-12-25&nights=2`

```json
{
  "trip": {"destination": "mussoorie", "start": "2026-12-25", "nights": 2,
           "mean_index": 87.0, "category": "Very High", "days": ["…DemandDay…"]},
  "drivers": [["Season", 22], ["Long weekend", 15]],
  "quieter": [
    {"start": "2026-12-22", "offset_days": -3, "mean_index": 52.0, "category": "Moderate",
     "drop": 35.0, "avoids": ["Gazetted holiday", "Long weekend", "Weekend", "Year-end holidays (assumed)"]},
    "…"
  ]
}
```

### `GET /alternatives?destination=mussoorie&start=2026-12-25&nights=2&top_n=1`

```json
{
  "origin": "mussoorie", "origin_name": "Mussoorie", "start": "2026-12-25", "nights": 2,
  "origin_demand": {"mean_index": 87.0, "category": "Very High", "…": "…"},
  "alternatives": [{
    "destination": "lansdowne", "name": "Lansdowne", "score": 0.053, "similarity": 0.75,
    "mean_index": 73.0, "category": "High",
    "components": [
      {"label": "Landscape", "value": 0.75, "basis": "derived", "detail": "weight 0.3"},
      "…",
      {"label": "Crowd relief", "value": 0.14, "basis": "derived", "detail": "(87 - 73) / 100"},
      {"label": "Capacity headroom", "value": 0.07, "basis": "assumption", "detail": "(assumed ceiling 80 - 73) / 100"}
    ],
    "explanation": {
      "why_origin_busy": "Mussoorie averages 87/100 (Very High) for these nights: Season (+22/day), Long weekend (+15/day), on top of a high-popularity baseline.",
      "why_similar": "Shares colonial-heritage, forest, heritage, nature, ridge, trekking, walking with Mussoorie; budget level is lower.",
      "expected_crowd": "High (73/100) on the same dates, 14 points below Mussoorie.",
      "trade_off": "About 7.2 h by road from New Delhi (-0.9 h vs Mussoorie; 287 km, estimated distance); budget level 2 vs 3 (1 low - 3 high).",
      "limitations": "Capacity is unknown: the ceiling of 80 for a medium-sensitivity place is an assumption. Season and profile are SYNTHETIC; weather and road status are not modelled. No profiled stays here yet."
    }
  }],
  "excluded": [["nainital", "not clearly quieter (85 vs 87)"], "…",
               ["mcleodganj", "capacity guard: 70 is at or above the assumed ceiling 70 for a high-sensitivity destination"]]
}
```

### `GET /stays?destination=kanatal` (one profile)

```json
{
  "property_id": "Property G", "destination": "kanatal", "destination_name": "Kanatal",
  "kind": "resort", "price_from": 4800, "price_to": 9500, "price_band": "premium",
  "rooms": [{"category": "standard", "count": 12, "price": 4800}, "…"], "total_rooms": 20,
  "amenities": ["hot water", "kids play area", "meals", "parking", "power backup", "room heating", "wifi"],
  "practices": [{"practice": "waste segregation", "status": "reported"},
                {"practice": "refill water station", "status": "not reported"}, "…"],
  "suitability": [{"label": "Families", "value": "yes", "basis": "derived", "detail": "6 family room(s) for up to 4"}, "…"],
  "feedback": [{"aspect": "Food", "mean": 0.653, "ci_low": 0.52, "ci_high": 0.776, "n": 144,
                "cluster_mean": 0.416, "flag": "lead"}, "…"],
  "leads": ["Food", "Value for Money", "Cleanliness"], "lags": ["Location"],
  "consistency": {"label": "Significant declines vs the market", "value": 0, "basis": "measured",
                  "detail": "none detected (FDR 5%, methodology section 6)"},
  "note": "Amenities and practices are self-reported in SYNTHETIC data; nothing here is verified. Guest feedback is computed from SYNTHETIC review text."
}
```

There is no star-rating field by design.

### `GET /provider/Property%20F/insights?start=2026-10-13&days=90`

```json
{
  "profile": {"…": "same shape as /stays"},
  "insights": [
    {"kind": "review_priority", "priority": "high", "title": "Fix Food first since 2025-06",
     "why": "Food is 1.05 below the cluster since 2025-06 (now -0.70 vs +0.35; a significant decline relative to the market). It appears in 14% of your aspect mentions.",
     "evidence": [{"label": "Gap to reference", "value": 1.05, "basis": "measured", "detail": "cluster"}, "…"],
     "period": null},
    {"kind": "demand_peak", "priority": "high",
     "title": "Expected Very High demand in Dhanaulti, 25 Dec - 27 Dec 2026",
     "why": "Demand index up to 77/100 driven by Gazetted holiday, Long weekend, Weekend, Year-end holidays (assumed). Note: family rooms are only 11% of your inventory during a family-travel period; budget rooms are 0% of inventory when students travel. An estimate, not a booking forecast.",
     "evidence": ["…"], "period": "25 Dec - 27 Dec 2026"},
    "…"
  ]
}
```

`kind` ∈ `review_priority | amenity_gap | demand_peak | offer_window | sustainability`;
`priority` ∈ `high | medium | low` (sorted in that order).

### `GET /sellers?destination=kanatal`

```json
[{"id": "S06", "name": "Kitchen Garden Collective", "destination": "kanatal",
  "category": "local produce", "offering": "Rajma, pahadi dal, herbal tea",
  "price": "INR 120-450", "verification": "unverified (SYNTHETIC)"}, "…"]
```

### `GET /region?start=2026-12-15&days=30` (one destination shown)

```json
{
  "start": "2026-12-15", "days": 30,
  "pressure": [{
    "destination": "shimla", "name": "Shimla", "region": "Himachal Pradesh", "mean_index": 62.1,
    "peak_day": "2026-12-25", "peak_index": 87, "peak_category": "Very High",
    "days_by_category": {"Low": 0, "Moderate": 7, "High": 20, "Very High": 3},
    "sensitivity": "high",
    "ceiling": {"label": "Assumed ceiling", "value": 70, "basis": "assumption",
                "detail": "high sensitivity; official carrying capacity unknown"},
    "days_at_or_over_ceiling": 3,
    "peaks": [{"start": "2026-12-24", "end": "2027-01-13", "days": 21, "max_index": 87,
               "drivers": ["Gazetted holiday", "Long weekend", "School winter break (assumed)", "Weekend", "Year-end holidays (assumed)"]}, "…"],
    "redistribution": {"date": "2026-12-25", "alternatives": [{"destination": "chakrata", "name": "Chakrata", "mean_index": 60.0}, "…"]},
    "profiled_rooms": 0, "sellers_listed": 1, "official_arrivals": null
  }, "…"],
  "under_served_categories": [{"destination": "shimla", "name": "Shimla", "category": "Woollen garments and shawls", "score": 62, "sellers_listed": 0}, "…"],
  "review_issues": [{"aspect": "Room", "scope": "market-wide", "pattern": "seasonal dip in December (12/12 properties, average drop 1.10)", "…": "…"}, "…"],
  "notes": ["Demand index: indicative estimate of relative visitor pressure, not live traffic.", "…"]
}
```

### `POST /plan`

Request (PlanRequest):

```json
{"origin": "delhi", "destination": "kanatal", "start": "2026-12-25", "nights": 2,
 "travellers": 2, "budget": 15000, "interests": ["nature"], "stay_pref": "any",
 "transport": "bus", "sustainability": false}
```

| Field | Rule |
|---|---|
| `origin` | `delhi`, `dehradun` or `chandigarh` (default `delhi`) |
| `destination` | a destination id from `/meta` |
| `nights` | 1–14 (default 2) |
| `travellers` | 1–12 (default 2) |
| `budget` | total INR, > 0 and ≤ 10,000,000 |
| `interests` | up to 10, each one of `/meta.interests` |
| `stay_pref` | `any`, `budget`, `standard`, `family` |
| `transport` | `car` or `bus` |
| `sustainability` | prefer stays reporting more practices |

Response (trimmed):

```json
{
  "destination_name": "Kanatal", "end": "2026-12-27",
  "demand": {"mean_index": 77.0, "category": "Very High", "drivers": [["Season", 22], ["Long weekend", 15]]},
  "stay": {"property_id": "Property I", "kind": "homestay", "category": "standard", "rooms": 1, "price_per_night": 2600},
  "itinerary": [{"day": "2026-12-25", "demand": "Very High",
                 "items": ["Travel from New Delhi (~8.3 h by road)", "Guided forest trek (half day) (INR 800 pp)",
                           "Visit Kitchen Garden Collective: Rajma, pahadi dal, herbal tea (INR 120-450)"]}, "…"],
  "costs": [
    {"label": "Transport (bus, return)", "value": 2656, "basis": "synthetic",
     "detail": "2 x 332 km x INR 2.0/passenger-km x 2; 332 km each way (estimated: straight line 227 km x 1.46 (median road/straight-line ratio of the 14 official distances))"},
    {"label": "Stay", "value": 5200, "basis": "synthetic", "detail": "Property I (homestay), 1 x standard room at INR 2,600/night x 2 night(s)"},
    {"label": "Activities", "value": 1600, "basis": "synthetic", "detail": "Guided forest trek (half day) INR 800 per person x 2"},
    {"label": "Food", "value": 4800, "basis": "synthetic", "detail": "INR 800/person/day (budget level 2) x 2 x 3 day(s)"}
  ],
  "total": 14256, "per_person": 7128, "within_budget": true,
  "carbon": [
    {"label": "Travel emissions by car", "value": 86.3, "basis": "derived", "detail": "2 x 332 km x 0.13 kg CO2/vehicle-km x 1 car(s). Factor: India GHG Program …"},
    {"label": "Travel emissions by bus (your choice)", "value": 52.4, "basis": "derived", "detail": "2 x 332 km x 0.03948 kg CO2e/passenger-km x 2 traveller(s). Factor: UK DESNZ … 2026 …"}
  ],
  "sellers": ["…"], "variants": ["…Lower budget…", "…Lower crowd…"],
  "notes": ["Illustrative SYNTHETIC prices and inventory: not a quote, booking or live availability. Demand is an indicative estimate, not live traffic."]
}
```

`total` always equals the sum of `costs[].value`.

### `POST /reviews/classify`

```json
// request
{"text": "Khana accha tha lekin kamra ganda tha."}
// response
{"backend": "rule",
 "mentions": [{"aspect": "Food", "sentiment": 1, "sentence": "khana accha tha"},
              {"aspect": "Room", "sentiment": -1, "sentence": "kamra ganda tha"},
              {"aspect": "Cleanliness", "sentiment": -1, "sentence": "kamra ganda tha"}]}
```

## Python facade changes (`cri.api` and friends)

- `classify.BACKENDS` adds `"learned"`; `get_classifier("learned")` returns the
  hybrid classifier with the trained model (`cri.learned_backend`).
- The classifier cache in `cri.api` is keyed by backend, aspects file **and** learned
  model path.
- New package `cri.travel` (demand, alternatives, stays, region, planner) consumes
  `cri.api`; nothing in the frozen contract changed.
