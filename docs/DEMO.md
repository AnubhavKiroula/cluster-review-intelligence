# Demo script (judge-facing, ~3 min)

Every number below is true for the **SYNTHETIC** sample (seed 42, the web app's
data) and is printed by:

```bash
python scripts/demo.py
```

`tests/test_demo.py` fails CI if any of these claims stops being true (e.g. after a
lexicon edit), so re-run the command and update this page if you change the data.
Say "synthetic" out loud: the banner is on every page.

## Before you go on stage

1. `python -m pytest tests/test_demo.py` passes.
2. The web app is open: deployed URL (`TBD`, see `docs/DEPLOYMENT.md`) **or**
   locally (`uvicorn cri.server:app --port 8000` + `cd web && npm run dev`; plan B,
   rehearsed). The full-product demo around this G5 segment: `docs/DEMO_SCRIPT.md`.
3. Plan C: the backup demo video (recorded at H+18).

## The script

1. **Hook (20 s)** - "Property F averages **3.28** stars. Property I averages
   **3.33**. One of them has a serious, recent problem. A star average can't tell you
   which."
2. **Property view (40 s)** - open **🏨 Property → Property F** (deep link:
   `<app-url>/property/?property=Property%20F`). *Fix this first* says
   **Food**, 1.05 below the cluster **since 2025-06**, a significant decline relative
   to the market. The trend line drops at the dashed June marker. (Property I:
   nothing flagged.)
3. **The differentiator (40 s)** - "But is that *them*, or the whole market?" Open
   **⚖️ Market**. Food = **property-specific** (only Property F) → a competitive gap
   they own. Room = **market-wide**: a seasonal dip every **December** at 12/12
   properties. **"Same chart, two completely different actions."**
   *Optional (30 s):* **🔧 Did my fix work? → Property A, Room, 2025-12**: "Say they
   renovated rooms in December." The plain before/after says **−1.38**, but the market
   fell **−0.95** over the same months; relative to the market it is **−0.43**, *no
   detectable change*. "A plain before/after would have blamed the renovation for
   the weather."
4. **Hinglish (20 s)** - **🔍 Explorer → Try your own review**. Type one of the
   rehearsed examples below; point at the *clause it came from* column.
5. **Destination view (20 s)** - **🧭 Destination**: "For a tourism board, Room is a
   destination problem, not a hotel problem."
6. **Honesty (20 s)** - show the README evaluation table and limitations: every
   number is reproducible; real-data accuracy is `TBD` until the labelled set exists
   (or the real measured number, if it exists by then - never an estimate).
7. **Close (10 s)** - one line on what we'd build next.

## Rehearsed live examples

Typed into *Try your own review*; output as of this commit (pinned by
`tests/test_demo.py`):

| Type this | Shows |
|---|---|
| `Khana accha tha lekin kamra ganda tha.` | Food +1, Room −1, Cleanliness −1 |
| `Khaana bahut swadisht tha but room thanda tha.` | Food +1, Room −1 |
| `कमरा साफ़ था और view zabardast tha.` | Room +1, Location +1, Cleanliness +1 |
| `Heater kaam nahi kar raha tha, raat bhar thand lagi.` | Room −1 |
| `Staff bahut helpful tha, paisa vasool.` | Staff +1, Value for Money +1 |

**Do not type these live** - known misses of the rule baseline (good material for
the honesty slide):

| Text | Rule output | Why |
|---|---|---|
| `Khaana accha nahi tha.` | Food +1 (should be −1) | Hindi negation comes *after* the word |
| `Wah kya staff hai, ek ghanta wait karaya.` | Staff 0 (should be −1) | sarcasm |
| `The bathroom was spotless.` | Cleanliness 0 (should be +1) | word not in the lexicon |
