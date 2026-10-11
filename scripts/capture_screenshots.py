"""Capture the dashboard screenshots in docs/screenshots/ (SYNTHETIC data).

Not a project dependency - a one-off tool:

    pip install playwright==1.58.0
    streamlit run app/Home.py --server.port 8600 --server.headless true   # other terminal
    python scripts/capture_screenshots.py                 # uses installed Edge
    python scripts/capture_screenshots.py --channel chrome

Each page is captured after Streamlit finishes its script run, so the images show
exactly what a visitor sees (SYNTHETIC banner included).
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

# (file, path, text that appears once rendered, viewport height)
PAGES = [
    ("property_view_SYNTHETIC.png", "/Property?property=Property%20F", "Trend over time", 2350),
    ("market_quadrant_SYNTHETIC.png", "/Market", "Scope by aspect", 1250),
    ("cluster_heatmap_SYNTHETIC.png", "/Cluster", "Cluster heatmap", 1000),
    ("destination_view_SYNTHETIC.png", "/Destination", "Negative share by aspect", 1450),
    ("review_explorer_SYNTHETIC.png", "/Explorer", "Search the reviews", 1000),
]
EXAMPLE = "Khana accha tha lekin kamra ganda tha."


def settle(page, marker: str) -> None:
    page.get_by_text(marker, exact=False).first.wait_for(timeout=120_000)
    page.wait_for_function(  # the "running" status widget disappears when a run ends
        "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=120_000
    )
    page.wait_for_timeout(2500)  # let Plotly finish drawing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8600")
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--channel", default="msedge", help="installed browser: msedge|chrome")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        for name, path, marker, height in PAGES:
            page.set_viewport_size({"width": 1400, "height": height})
            page.goto(args.url + path)
            settle(page, marker)
            if name.startswith("review_explorer"):
                box = page.get_by_placeholder(EXAMPLE)
                box.fill(EXAMPLE)
                box.press("Control+Enter")
                page.get_by_text("clause it came from").first.wait_for(state="attached")
                settle(page, marker)
            page.screenshot(path=str(args.out / name))
            print("saved", args.out / name)
        browser.close()


if __name__ == "__main__":
    main()
