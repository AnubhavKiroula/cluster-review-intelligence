"""Capture the web app screenshots in docs/screenshots/ (SYNTHETIC data).

Not a project dependency - a one-off tool:

    pip install playwright==1.58.0
    uvicorn cri.server:app --port 8000                                   # terminal 1
    cd web && npm run build && python -m http.server 3000 --directory out  # terminal 2
    python scripts/capture_screenshots.py                 # uses installed Edge
    python scripts/capture_screenshots.py --channel chrome

Each page is captured once its data has rendered, so the images show exactly what a
visitor sees (SYNTHETIC / prototype banners included). Port 3000 matches the API's
default CORS origin.
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

# (file, path, text that appears once rendered)
PAGES = [
    ("property_view_SYNTHETIC.png", "/property/?property=Property%20F", "Fix this first"),
    ("market_quadrant_SYNTHETIC.png", "/market/", "Scope by aspect"),
    ("explore_SYNTHETIC.png", "/explore/?destination=mussoorie&start=2026-12-25&nights=2",
     "Similar, less crowded places"),
    ("provider_SYNTHETIC.png", "/provider/?property=Property%20F", "Fix Food first since 2025-06"),
    ("region_SYNTHETIC.png", "/region/", "Expected pressure vs assumed ceilings"),
]
PLAN = ("plan_SYNTHETIC.png", "/plan/?destination=kanatal&start=2026-12-25&nights=2")
EXPLORER = "review_explorer_SYNTHETIC.png"


def settle(page, marker: str) -> None:
    page.get_by_text(marker, exact=False).first.wait_for(timeout=60_000)
    page.wait_for_timeout(2000)  # let Plotly finish drawing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:3000")
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--channel", default="msedge", help="installed browser: msedge|chrome")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        for name, path, marker in PAGES:
            page.goto(args.url + path, wait_until="networkidle")
            settle(page, marker)
            page.screenshot(path=str(args.out / name), full_page=True)
            print("saved", args.out / name)

        name, path = PLAN
        page.goto(args.url + path, wait_until="networkidle")
        page.get_by_role("button", name="Plan my trip").click()
        settle(page, "Cheaper or quieter options")
        page.screenshot(path=str(args.out / name), full_page=True)
        print("saved", args.out / name)

        page.goto(args.url + "/explorer/", wait_until="networkidle")
        page.get_by_role("button", name="Classify").click()
        settle(page, "Classifier backend")
        page.screenshot(path=str(args.out / EXPLORER))
        print("saved", args.out / EXPLORER)
        browser.close()


if __name__ == "__main__":
    main()
