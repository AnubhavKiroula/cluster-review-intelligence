# Web app screenshots

Screenshots of the Next.js app (`web/`). Each page shows its provenance chip: the
real Kausani cluster, or the SYNTHETIC method demo. The explorer shot also needs the
API (`cri.server`) for live classification.

| File | Page |
|---|---|
| `property_view_real_kausani.png` | **Real** Kausani cluster, Property Y: Fix Room first (yours alone), star average, scorecard vs cluster; no trend (the source has no dates) |
| `market_real_kausani.png` | **Real** Kausani cluster: no shared weak spot; hotel-specific gaps by aspect |
| `property_view_SYNTHETIC.png` | Method demo on the SYNTHETIC timeline, Property F: Fix Food first since 2025-06 (yours alone), trend with the changepoint |
| `fix_check_SYNTHETIC.png` | "Did my fix work?" on the SYNTHETIC timeline: before/after vs the market |
| `review_explorer_SYNTHETIC.png` | "Try your own review" on a Hinglish example; illustrative SYNTHETIC review texts |

The real screenshots show only anonymised aggregates; no real review text appears.

Re-capture after UI changes (needs `pip install playwright==1.58.0`, not a project
dependency, and an installed Edge or Chrome):

```bash
uvicorn cri.server:app --port 8000
cd web && npm run build && python -m http.server 3000 --directory out
python scripts/capture_screenshots.py
```
