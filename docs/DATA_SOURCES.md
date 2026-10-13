# Data sources

What every dataset and integration is, where it came from, how fresh it is, and
whether it is **real**, **SYNTHETIC** or an **assumption**. Nothing synthetic is
presented as official anywhere in the app: every number carries a `basis`
(`fact`, `measured`, `derived`, `synthetic`, `assumption`). Facts were read from the
cited documents on **2026-10-13**.

## At a glance

| Data | Status | Where | Used for |
|---|---|---|---|
| Review cluster, 12 properties (Property A–L), 5,124 reviews, 2024-01..2025-12 | **SYNTHETIC** (`cri.generate`, seed 42) | generated in memory; `data/sample/synthetic_reviews.csv` | all G5 review analytics, stay feedback, provider insights |
| Gazetted holidays 2026–2027 | **Real** (official) | `src/cri/resources/travel_facts.yaml` | demand index, long weekends |
| Coordinates, elevations | **Real** (Wikidata, CC0) | `travel_facts.yaml` | distances, map context |
| Road distances (14 pairs) | **Real** (official) | `travel_facts.yaml` | trip costs, travel time, carbon |
| Other road distances | **Derived** estimate | computed | same, labelled "estimated" |
| Annual tourist arrivals 2023 (3 destinations) | **Real** (official) | `travel_facts.yaml` | context in the region view and popularity evidence; does not set the index |
| Emission factors (car, bus) | **Real** (published factors) | `travel_facts.yaml` | carbon estimate |
| Destination profiles (season curves, tags, budget, sensitivity, activity prices) | **SYNTHETIC / assumption** | `src/cri/resources/travel_synthetic.yaml` | demand index, alternatives, planner |
| Stays for Properties A–L (rooms, prices, amenities, practices) | **SYNTHETIC** | `travel_synthetic.yaml` | star-free profiles, planner |
| 22 local sellers and category seasonality | **SYNTHETIC** | `travel_synthetic.yaml` | seller discovery, opportunity estimates |
| School vacation and year-end windows | **Assumption** | `travel_synthetic.yaml` | demand index |
| SentiMix Hinglish tweets | **Real**, CC BY 4.0 | downloaded to `data/raw/external/` (gitignored) | training/testing the learned sentiment model |
| Hinglish YouTube comments | **Real**, CC BY 4.0 | downloaded to `data/raw/external/` | same |
| Hill-destination hotel reviews (Kaggle) | **Real**, provenance uncertain | downloaded by a team member to `data/raw/external/` | training/testing the local region model only |

## Official and open facts (`travel_facts.yaml`)

| Fact | Source | Notes |
|---|---|---|
| Gazetted holidays 2026 (17 dates) | CGEWCC Dehradun list for Central Government offices in Uttarakhand, as per DoPT O.M. F.No.12/2/2023-JCA dated 03.07.2025 ([surveyofindia.gov.in PDF](https://surveyofindia.gov.in/UserFiles/files/List%20of%20Holidays-2026%20(2).pdf)) | Weekday of every date is checked on load |
| Gazetted holidays 2027 (17 dates) | DoPT O.M. F.No.12/2/2023-JCA dated 16.07.2026, Annexure-I, forwarded by the Department of Posts on 08.09.2026 ([PDF](https://utilities.cept.gov.in/dop/pdfbind.ashx?id=15435)); the CGEWCC Dehradun 2027 list is identical | Id-ul-Fitr, Id-ul-Zuha, Muharram and Milad-un-Nabi may move with moon sighting (para 5 of the O.M.); flagged in the app |
| Coordinates (P625) and elevation (P2044) of 12 destinations and 3 origin cities | [Wikidata](https://www.wikidata.org/) (CC0), item ids in the YAML | — |
| Delhi / Chandigarh to Shimla, Manali, Dharamshala, Dalhousie, Kasauli | [HPTDC, Access](https://hptdc.hp.gov.in/index.php/access) | "Delhi - Dharamshala" is used for Dharamshala–McLeod Ganj |
| Delhi and Dehradun to Nainital | [District Nainital (NIC)](https://nainital.nic.in/how-to-reach-nainital-by-road/) | — |
| Dehradun to Mussoorie (38 km), Mussoorie to Dhanaulti (24 km) | [District Dehradun (NIC)](https://dehradun.nic.in/tourist-place/mussoorie/) | — |
| Tourist arrivals 2023: Mussoorie 1,471,913; Nainital 784,497; "Kausani & Bageshwar" 82,563 | [UTDB, Tourists Statistics 2021–2023](https://uttarakhandtourism.gov.in/assets/pdf/Statistic21-23.pdf) | Annual totals only; no separate rows for Dhanaulti, Kanatal, Chakrata, Lansdowne |
| Car: 0.130 kg CO2 per vehicle-km (petrol hatchback < 1400 cc) | [India GHG Program, India Specific Road Transport Emission Factors (2015)](https://indiaghgp.org/sites/default/files/Road%20Transport%20Technical%20Paper.pdf) | The paper also gives 0.140 with a 10% uplift; hill driving likely emits more |
| Bus: 0.03948 kg CO2e per passenger-km (coach) | [UK DESNZ GHG conversion factors 2026](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026), flat file revised July 2026, OGL v3.0 | A UK coach factor: no Indian intercity bus factor was found (the India GHG Program bus factor excludes intercity travel) |

**Estimated distances.** Pairs without an official distance use the straight-line
(haversine) distance × **1.46**, the median road/straight-line ratio of the 14
official pairs above, computed on load. It underestimates short, winding hill hops
(e.g. Dehradun–Mussoorie is 2.4× the straight line), so these are labelled
"estimated" wherever shown.

## Gaps and their effect

| Missing | Effect | What would fix it |
|---|---|---|
| Daily or monthly visitor footfall per destination | The demand index cannot be trained or validated; it is a transparent heuristic and says so | Monthly arrivals from UTDB / HP Tourism, or booking/occupancy feeds from partners |
| Uttarakhand and Himachal **state** holiday lists | Only Central Government gazetted holidays count; state-only holidays are missed | The state notifications in machine-readable form |
| School calendars for 2026-27 | School windows are assumptions modelled on Delhi DoE dates reported in the press | Official academic calendars per board/state |
| Carrying capacity | No numeric caps exist for these places; the capacity guard uses assumed ceilings by environmental sensitivity | Carrying-capacity studies (e.g. the UTDB survey announced for Nainital) |
| Weather, road status, live traffic | Not modelled; the app never claims live conditions | IMD forecasts, PWD/BRO road status APIs |
| Real stay inventory, prices, amenities | Stays and prices are SYNTHETIC | Provider onboarding |
| Real seller records | Sellers are SYNTHETIC and "unverified" | Onboarding with verification |
| Indian intercity bus and rail emission factors | UK coach factor used, labelled | An Indian published factor |

## Review datasets for the learned sentiment model

None of these is committed to git; all live under `data/raw/external/` (gitignored).

### SentiMix (SemEval-2020 Task 9) — CC BY 4.0

- Source: Zenodo record [3974927](https://doi.org/10.5281/zenodo.3974927),
  `Semeval_2020_task9_data.zip`, md5 `4d93553c213b3a966b6d55b7a7c03be7`. (A Hugging
  Face re-upload `RTT1/SentiMix` carries a different licence tag; we use the original.)
- Hinglish code-mixed tweets, CoNLL token format, labels positive / neutral /
  negative: 14,000 train, 3,000 dev, 3,000 test (test labels in a separate file).
- Cite: Patwa et al., *SemEval-2020 Task 9: Overview of Sentiment Analysis of
  Code-Mixed Tweets*, SemEval 2020.

### Hinglish YouTube comments — CC BY 4.0

- Source: [shae2977/hinglish-youtube-sentiments-dataset](https://huggingface.co/datasets/shae2977/hinglish-youtube-sentiments-dataset),
  revision `84abda5e30d082a66c251fc46513cb89ce866cbb`, file sha256
  `07de7acd…f19fc6`. 3,190 comments (entertainment / cooking videos), one annotator.

### Hill-destination hotel reviews (Kaggle) — provenance uncertain, local only

- Source: [orionpax00/uttarakhand-hotel-reviews-india](https://www.kaggle.com/datasets/orionpax00/uttarakhand-hotel-reviews-india),
  downloaded by a team member with their own Kaggle login (we do not bypass logins).
  Uploader-declared CC0, last updated 2020; the reviews appear to come from
  TripAdvisor, whose terms a CC0 tag cannot override. We therefore use it for
  research only and **never commit the text or the model trained on it**.
- Profile (2026-10-13, `scripts/prepare_region_reviews.py`): 1,628 CSVs (one per
  hotel, 20 empty), columns `location, review, name, user_profile, userloc, rating`.
  No review dates. Despite the name it covers Uttarakhand, Himachal Pradesh and
  Ladakh.
- Processing: reviewer columns are never loaded; hotel names become opaque ids;
  the plains districts Haridwar and Udham Singh Nagar are dropped (Dehradun and
  Nainital districts are mixed and kept); duplicate texts are removed before any
  split; 10 files whose names carry no district are skipped.
- Result: 80,827 reviews from 1,306 hotels (Himachal 33,633; Uttarakhand 29,564;
  Ladakh 17,432). Stars: 1★ 1,964 · 2★ 1,544 · 3★ 4,999 · 4★ 18,995 · 5★ 53,325.
  Weak labels: 1–2★ → negative, 3★ → neutral, 4–5★ → positive (89% positive).
- Mussoorie is effectively absent (2 files in Dehradun district).

### Considered and not used

| Dataset | Why not |
|---|---|
| argilla/tripadvisor-hotel-reviews | CC BY-NC 4.0 and English hotels outside India; weights could not ship in this Apache-2.0 repo |
| ai4bharat/IndicSentiment | Translated product reviews; validation/test only (no train split) |
| SemEval-2016 Task 5 ABSA | Hotel data is Arabic only |
| PromptCloud Goibibo / MakeMyTrip listings | No review text |

## Future data acquisition

1. A hand-labelled gold set of ~300 hill-destination clauses (Hinglish + English)
   via the existing labelling pack, to measure clause-level accuracy (`TBD`).
2. A permitted, anonymised review export from the tourism board or partner
   properties (with dates) to run the G5 analytics on real data.
3. Monthly destination arrivals and partner occupancy to validate the demand index
   (validation plan: `docs/AI_MODEL.md`).
