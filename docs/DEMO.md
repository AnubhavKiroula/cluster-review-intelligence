# Demo script (judge-facing, 3 minutes)

**One user, one question.** The user is a hotel or homestay owner. The question:
*when my reviews get worse on something, is it my problem or the whole market's?*
A single hotel cannot answer that from its own reviews. The cluster can.

Every number below is true for the **SYNTHETIC** sample (seed 42, the web app's
data). `python scripts/demo.py` prints all of them, and `tests/test_demo.py` (plus
`tests/test_intervention.py` for the fix check) fails CI if one stops being true.
If you change the data, re-run the command and update this page. Say "synthetic" out
loud: the banner is on every page.

## Before you go on stage

1. `python -m pytest tests/test_demo.py` passes.
2. Open the web app:
   - the deployed URL (`TBD`, see `docs/DEPLOYMENT.md`), **or**
   - locally: `cd web && npm run build && python -m http.server 3000 --directory out`.
3. Only step 5 needs the API: `uvicorn cri.server:app --port 8000`. Every other step
   reads the static snapshot.
4. Plan B: `npm run dev` in `web/`. Plan C: the backup video and `docs/screenshots/`.

## The script

1. **Hook (20 s).**
   - "Property F averages **3.28** stars. Property I averages **3.33**."
   - "One of them has a serious, recent problem. A star average can't tell you which."
   - "MakeMyTrip and Booking.com help travellers find a hotel. We work for the hotel."

2. **`/property` → Property F (45 s).** Deep link:
   `<app-url>/property/?property=Property%20F`.
   - The card says **Fix Food first since 2025-06**: Food is 1.05 below the cluster
     over the same months.
   - The **Whose problem** column says **yours alone**: "you dropped 1.22 relative to
     the market from 2025-06; the market itself moved +0.01".
   - The trend line drops at the dashed June marker.
   - Property I: nothing flagged.
   - *Optional (15 s): Property D, Room.* Room has a market-wide December dip, but
     D's row still says **yours alone**: "still 0.36 below the market outside
     December". "We test it for each property. We don't just copy a market label."

3. **`/market` (40 s).** "Is that them, or the whole market?"
   - Food is **property-specific**: only Property F. That is a competitive gap F owns.
   - Room is **market-wide**: a seasonal dip every **December** at **12/12**
     properties. Every property has it, so it is not a gap against competitors.
   - **"Same chart, two opposite actions."**

4. **`/fix-check` → Property A, Room, 2025-12 (30 s).** "Say they renovated rooms in
   December."
   - The plain before/after says **−1.38**.
   - Over the same months the market fell **−0.95**.
   - Relative to the market the change is **−0.43**: *no detectable change*.
   - "A plain before/after would have blamed the renovation for the weather."

5. **`/explorer` → Try your own review (20 s).** Type one of the rehearsed examples
   below and point at the *clause it came from* column.

6. **Honesty (25 s).** Show the README evaluation table and limitations.
   - The data is SYNTHETIC, and every number is reproducible.
   - Real-data accuracy at clause level is `TBD` until the labelled set exists.
     If a measured number exists by then, quote it; never quote an estimate.

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

- Do not call any property, review or number real. The data is SYNTHETIC.
- Do not quote the learned model's macro-F1 as clause-level accuracy. It is
  document-level, on held-out data (`docs/AI_MODEL.md`).
- Do not quote a price or revenue figure. They are hypotheses
  (`docs/BUSINESS_MODEL.md`).
