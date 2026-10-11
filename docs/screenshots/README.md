# Dashboard screenshots (SYNTHETIC data)

Real screenshots of the Streamlit dashboard running on the **SYNTHETIC** sample
(seed 42); the SYNTHETIC banner is visible on every page.

| File | Page |
|---|---|
| `property_view_SYNTHETIC.png` | Property F: fix-this-first, scorecard vs cluster with 95% intervals, trend with the detected changepoint |
| `market_quadrant_SYNTHETIC.png` | Market-wide vs property-specific quadrant |
| `cluster_heatmap_SYNTHETIC.png` | Property × aspect heatmap |
| `destination_view_SYNTHETIC.png` | Tourism-board view |
| `review_explorer_SYNTHETIC.png` | "Try your own review" on a Hinglish example + review search |

Re-capture after UI changes (needs `pip install playwright==1.58.0`, not a project
dependency, and an installed Edge or Chrome):

```bash
streamlit run app/Home.py --server.port 8600 --server.headless true
python scripts/capture_screenshots.py
```
