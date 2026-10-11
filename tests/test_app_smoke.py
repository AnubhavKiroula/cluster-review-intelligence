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


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_page_runs_without_exception(app_test, path):
    assert _errors(app_test(path)) == []


def test_property_page_runs_for_every_property(app_test):
    at = app_test(APP / "pages" / "1_Property.py")
    properties = at.sidebar.selectbox(key="property").options
    assert len(properties) == 12
    for prop in properties:
        at.sidebar.selectbox(key="property").set_value(prop).run()
        assert _errors(at) == [], prop


def test_explorer_classifies_a_typed_review(app_test):
    at = app_test(APP / "pages" / "5_Explorer.py")
    at.text_area(key="ex_try").input("Khana accha tha lekin kamra ganda tha.").run()
    assert _errors(at) == []
    shown = at.dataframe[0].value
    assert {"Food", "Room"} <= set(shown["aspect"])
