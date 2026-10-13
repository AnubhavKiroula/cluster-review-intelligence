"""Smoke tests for the Streamlit dashboard (owner [P]).

Runs every page headlessly with Streamlit's ``AppTest`` on the SYNTHETIC sample,
so runtime errors (bad columns, library incompatibilities) fail CI, not the demo:

* the shared modules (``common``, ``theme``) import;
* every page compiles, and runs without an exception;
* the Property page runs for every property (each has different findings).

Needs the ``dashboard`` extra (``pip install -e ".[dev,dashboard]"``, as CI does);
skips otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))  # mirror how Streamlit puts the entrypoint dir on sys.path

PAGES = sorted((APP / "pages").glob("*.py")) + [APP / "Home.py"]


def test_shared_modules_import():
    import common  # noqa: F401
    import theme  # noqa: F401


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_page_compiles(path):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


@pytest.fixture(scope="module")
def app_test():
    from streamlit.testing.v1 import AppTest

    def run(path: Path) -> AppTest:
        return AppTest.from_file(str(path), default_timeout=180).run()

    return run


def _errors(at) -> list[str]:
    return [e.message for e in at.exception]


def _invisible_shapes(at) -> list[dict]:
    """Chart lines drawn with width 0 (the simple_white template's shape default)."""
    bad = []
    for chart in at.get("plotly_chart"):
        layout = json.loads(chart.proto.spec)["layout"]
        defaults = layout.get("template", {}).get("layout", {}).get("shapedefaults", {})
        default_width = defaults.get("line", {}).get("width", 2)
        bad += [s for s in layout.get("shapes", [])
                if s.get("line", {}).get("width", default_width) == 0]
    return bad


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_page_runs_without_exception(app_test, path):
    at = app_test(path)
    assert _errors(at) == []
    assert _invisible_shapes(at) == []


def test_property_page_runs_for_every_property(app_test):
    at = app_test(APP / "pages" / "1_Property.py")
    properties = at.sidebar.selectbox(key="property").options
    assert len(properties) == 12
    for prop in properties:
        at.sidebar.selectbox(key="property").set_value(prop).run()
        assert _errors(at) == [], prop
        assert _invisible_shapes(at) == [], prop


def test_explorer_classifies_a_typed_review(app_test):
    at = app_test(APP / "pages" / "5_Explorer.py")
    at.text_area(key="ex_try").input("Khana accha tha lekin kamra ganda tha.").run()
    assert _errors(at) == []
    shown = at.dataframe[0].value
    assert {"Food", "Room"} <= set(shown["aspect"])


def test_property_deep_link_preselects_a_property():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "pages" / "1_Property.py"), default_timeout=180)
    at.query_params["property"] = "Property F"
    at.run()
    assert _errors(at) == []
    assert at.sidebar.selectbox(key="property").value == "Property F"


def test_fix_check_page_shows_a_market_adjusted_verdict(app_test):
    at = app_test(APP / "pages" / "6_Fix_check.py")
    at.selectbox(key="fix_aspect").set_value("Room").run()
    at.selectbox(key="fix_start").set_value("2025-12").run()
    assert _errors(at) == []
    assert any("No detectable change" in i.value for i in at.info)
