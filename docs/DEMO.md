# Demo script (judge-facing, 3 minutes)

**One user, one question.** The user is a hotel or homestay owner. The question:
*when my reviews get worse on something, is it my problem or the whole market's?*
A single hotel cannot answer that from its own reviews. The cluster can.

**The data is real.** We use 25 real hotels in **Kausani** (Bageshwar, Uttarakhand)
and their 2,751 real reviews (TripAdvisor-derived, anonymised as Property A–Y,
aggregates only). The source has **no review dates**, so the time axis is shown on
a clearly labelled simulated timeline.

Every number below is printed by `python scripts/demo.py`. `tests/test_demo.py`
(plus `tests/test_intervention.py` for the fix check) fails CI if one stops being
true:
- the **real** numbers are checked against the committed snapshot
  `web/public/data/cluster.real.json`;
- the **method-demo** numbers come from the SYNTHETIC sample (seed 42).

## Before you go on stage

1. `python -m pytest tests/test_demo.py` passes.
2. Open the web app:
   - the deployed URL (see `docs/DEPLOYMENT.md`), **or**
   - locally: `cd web && npm run build && python -m http.server 3000 --directory out`.
3. Only step 5 needs the API: `uvicorn cri.server:app --port 8000`. Every other step
   reads static snapshots.
4. Plan B: `npm run dev` in `web/`. Plan C: the backup video and `docs/screenshots/`.

## The script

1. **Hook (20 s).** Point at the chip: *Kausani · 25 hotels · 2,751 real reviews ·
   TripAdvisor*.
   - "These are real hotels in one Uttarakhand town. Property I averages **3.44**
     stars. Property Y averages **3.49**. One of them has two problems the stars
     don't show."
   - "MakeMyTrip and Booking.com help travellers find a hotel. We work for the hotel."
   - Home tile: a hotel here has a median of **66** reviews of its own. We read all
     **2,751**.

2. **`/property` → Property Y (40 s).** Deep link:
   `<app-url>/property/?property=Property%20Y`.
   - **Fix Room first**: Room is **0.42** below the Kausani cluster. Cleanliness is
     **0.68** below. Both say **yours alone**.
   - "The stars said 3.49. The cluster says Room and Cleanliness, and that it's
     theirs, not Kausani's."
   - Property I: nothing flagged.

3. **`/market` (30 s).** "Is any of this the whole town's problem?"
   - **No shared weak spot in Kausani.** Every gap belongs to individual hotels.
   - Room lags at **4** hotels and Location at **3**. **7 of 25** hotels have a
     flagged gap.
   - "If the whole town were weak on something, that would be a **market
     opportunity for whoever fixes it first**. Here, each owner's fix is their own."

4. **The time axis, honestly (40 s).** "The real reviews carry no dates, so we show
   the time method on a simulated timeline." Switch to **Method demo**:
   - Property F: **Fix Food first since 2025-06**, yours alone. "You dropped 1.22
     relative to the market; the market itself moved +0.01."
   - `/market`: Room dips every **December** at **12/12** hotels. That is
     everyone's, a market opportunity.
   - **`/fix-check` → Property A, Room, 2025-12:** the plain before/after says
     **−1.38**, the market fell **−0.95**, and relative to the market the change is
     **−0.43**: *no detectable change*. "A plain before/after would have blamed the
     renovation for the weather."

5. **`/explorer` → Try your own review (20 s).** Type one of the rehearsed examples
   below and point at the *clause it came from* column. The searchable reviews are
   illustrative: real review text is never published.

6. **Honesty (30 s).**
   - The cluster is real, anonymised, and published as aggregates only.
   - The source has no dates, so the time-series method runs on SYNTHETIC data. It is
     calibrated in `docs/methodology.md` §10.
   - The Kausani corpus is almost all English (8 of 2,751 reviews Hinglish or
     Hindi). Our Hinglish handling is tested on public Hinglish sets, not on this
     corpus.
   - Clause-level accuracy on real reviews is `TBD` until the labelled set exists.

## Rehearsed live examples

Typed into *Try your own review*. The output below is as of this commit, pinned by
`tests/test_demo.py`:

| Type this | Shows |
|---|---|
| `Khana accha tha lekin kamra ganda tha.` | Food +1, Room −1, Cleanliness −1 |
| `Khaana bahut swadisht tha but room thanda tha.` | Food +1, Room −1 |
| `कमरा साफ़ था और view zabardast tha.` | Room +1, Location +1, Cleanliness +1 |
| `Heater kaam nahi kar raha tha, raat bhar thand lagi.` | Room −1 |
| `Staff bahut helpful tha, paisa vasool.` | Staff +1, Value for Money +1 |
| `Khaana accha nahi tha.` | Food −1 (Hindi negation comes *after* the word) |

**Do not type these live.** They are known misses of the rule baseline, which makes
them good material for the honesty step:

| Text | Rule output | Why |
|---|---|---|
| `Wah kya staff hai, ek ghanta wait karaya.` | Staff 0 (should be −1) | sarcasm |
| `The bathroom was spotless.` | Cleanliness 0 (should be +1) | word not in the lexicon |

## Lines to avoid

- **Never name the hotel behind a Property id on stage.** The findings are
  critical, and the ids are anonymised on purpose. If a judge asks, offer to show
  the mapping privately.
- Do not call the method-demo numbers real. They are SYNTHETIC, and the chip says so.
- Do not quote the learned model's macro-F1 as clause-level accuracy. It is
  document-level, on held-out data (`docs/AI_MODEL.md`).
- Do not quote a price or revenue figure. They are hypotheses
  (`docs/BUSINESS_MODEL.md`).
