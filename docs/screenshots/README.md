# Web app screenshots (SYNTHETIC data)

Real screenshots of the Next.js app (`web/`) on the **SYNTHETIC** review sample
(seed 42); the SYNTHETIC banner is visible on every page. The explorer shot also needs
the API (`cri.server`) for live classification.

| File | Page |
|---|---|
| `property_view_SYNTHETIC.png` | Property F: "Fix Food first since 2025-06", whose problem it is, scorecard vs cluster with 95% intervals, trend with the detected changepoint |
| `market_quadrant_SYNTHETIC.png` | Market-wide vs property-specific, with the worst market-wide aspect |
| `fix_check_SYNTHETIC.png` | "Did my fix work?" before/after vs the market |
| `review_explorer_SYNTHETIC.png` | "Try your own review" on a Hinglish example |

Re-capture after UI changes (needs `pip install playwright==1.58.0`, not a project
dependency, and an installed Edge or Chrome):

```bash
uvicorn cri.server:app --port 8000
cd web && npm run build && python -m http.server 3000 --directory out
python scripts/capture_screenshots.py
```
