# Demo script: full product (~5 min)

The G5 segment (steps 2–3) reuses the rehearsed, test-pinned numbers in
[`DEMO.md`](DEMO.md). The other numbers on this page come from the running API on
the packaged data (SYNTHETIC review cluster, seed 42; travel resources as committed)
and were checked on 2026-10-13. Say "SYNTHETIC" and "estimate" out loud: the banners
say it on every page.

## Before you go on stage

```bash
uvicorn cri.server:app --port 8000                                     # terminal 1
cd web && npm run build && python -m http.server 3000 --directory out   # terminal 2
```

- Open `http://localhost:3000`. If you use the deployed site, check that
  `NEXT_PUBLIC_API_BASE_URL` and the API's CORS origin match.
- `python -m pytest tests/test_demo.py` passes.
- Plan B: `npm run dev` in `web/`. Plan C: the backup video and the screenshots in
  `docs/screenshots/`.

## Script

1. **Problem (30 s).**
   - "Hill destinations are crowded on long weekends while similar places nearby sit
     half-empty."
   - "Star averages hide what is actually wrong, and little of the money reaches
     local artisans."
   - "We start from guest reviews and work outwards."

2. **Review intelligence, the core (60 s).** Use `DEMO.md` steps 1–3.
   - Property F: *Fix Food first since 2025-06*.
   - `/market`: Food is property-specific, Room is market-wide in December.

3. **Traveller (60 s).** Open `/explore/?destination=mussoorie&start=2026-12-25&nights=2`.
   - **Crowd:** "Christmas weekend in Mussoorie: **Very High, 87/100**." Expand
     *Why 87?*:
     - 30 popularity tier (informed by UTDB's 1,471,913 arrivals in 2023);
     - 22 season;
     - 10 Christmas (DoPT gazetted holiday);
     - 15 long weekend (Fri–Sun);
     - 10 assumed year-end window.
     - "Every point has a source, and none of it is live traffic."
   - **Quieter dates:** "Arrive Tue 22 Dec instead: Moderate, 35 points quieter."
   - **Alternatives:**
     - Lansdowne (High, 73) and Chakrata (High, 60), each with why it is similar,
       the trade-off and the limitations.
     - Open *Not suggested*: "McLeod Ganj is excluded by the capacity guard. We
       don't just move the crowd to a more fragile place."
   - **Stays:** "No stars. Compare price, rooms, and what guests say about each
     aspect."

4. **Plan on a student budget (45 s).** Click *Plan this trip*, or open
   `/plan/?destination=kanatal&start=2026-12-25&nights=2`.
   - Set 2 travellers, ₹15,000, bus, interest *nature*. Result: **₹14,256** (₹7,128 each), within
     budget.
   - "Every rupee has its formula: bus, homestay, activities, food."
   - **Carbon:** **52 kg CO₂** by bus vs **86 kg** by car, with the factor source shown.
   - **Sellers:** local sellers are on the itinerary.
   - **Variants:** "Lower crowd" shows the quieter option.

5. **Provider (40 s).** Open `/provider/?property=Property%20F`.
   - "Fix Food first, from reviews."
   - "Christmas demand is coming and you have 11% family rooms."
   - "Heating complaints peak in December, but they are market-wide: raise it with
     the tourism board too."
   - Every item has a *why* and the evidence.

6. **Tourism board (30 s).** Open `/region`.
   - Pressure vs assumed ceilings.
   - Redistribution suggestions.
   - Under-served seller categories (woollens before winter).
   - Destination-wide review issues.

7. **AI, honestly (30 s).** Show `docs/AI_MODEL.md`:
   - "We trained a sentiment model on open Hinglish data and on hill-destination
     hotel reviews."
   - "On held-out hill hotels it scores **0.687 macro-F1 vs 0.557** for our rules."
   - "But it is weaker on short clauses, so rules stay the default until a labelled
     gold set says otherwise. Demand is a transparent estimate because no footfall
     data exists to train on."

8. **Business and impact (30 s).**
   - Travellers free; free listings for small providers and sellers.
   - Affordable provider analytics and board dashboards.
   - No commission-driven ranking.
   - "We measure success by pressure moved off over-capacity days and money reaching
     local sellers. Today those are estimates, and we label them that way."

## Lines to avoid

- Do not say "live", "real-time" or "traffic" about the demand index.
- Do not quote the learned model's numbers as clause-level accuracy. They are
  document-level, on held-out data.
- Do not call any stay, price or seller real. They are SYNTHETIC.
