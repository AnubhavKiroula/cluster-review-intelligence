"""Smoke test for the Streamlit dashboard (owner [P]).

Catches syntax and import breaks in CI without a running Streamlit server:

* the shared modules (``common``, ``theme``) are imported — this exercises the real
  import surface the pages rely on (streamlit, plotly, pandas, ``cri.api``);
* every page file is compiled, which catches syntax errors.

Skips entirely until ``streamlit`` and ``plotly`` are installed (they are not in the
default/dev extras yet — see the PR note requesting [R] add them to ``pyproject.toml``).
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
