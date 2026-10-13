# Web app screenshots (SYNTHETIC data)

Real screenshots of the Next.js app (`web/`) with the API (`cri.server`) running on the
**SYNTHETIC** review sample (seed 42) and the travel resources; the SYNTHETIC / prototype
banner is visible on every page. Captured 2026-10-13.

| File | Page |
|---|---|
| `property_view_SYNTHETIC.png` | Property F: fix-this-first, scorecard vs cluster with 95% intervals, trend with the detected changepoint |
| `market_quadrant_SYNTHETIC.png` | Market-wide vs property-specific quadrant |
| `explore_SYNTHETIC.png` | Traveller: Mussoorie over the Christmas 2026 long weekend, demand calendar, quieter dates, alternatives, star-free stays |
| `plan_SYNTHETIC.png` | Trip planner: Delhi to Kanatal, traced costs, car vs bus carbon, sellers, variants |
| `provider_SYNTHETIC.png` | Provider insights for Property F |
| `region_SYNTHETIC.png` | Tourism-board view: pressure vs assumed ceilings, review issues |
| `review_explorer_SYNTHETIC.png` | "Try your own review" on a Hinglish example |

Re-capture after UI changes (needs `pip install playwright==1.58.0`, not a project
dependency, and an installed Edge or Chrome):

```bash
uvicorn cri.server:app --port 8000
cd web && npm run build && python -m http.server 3000 --directory out
python scripts/capture_screenshots.py
```
