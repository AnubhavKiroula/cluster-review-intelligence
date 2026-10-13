"""HTTP API contract (FastAPI TestClient; skipped without the `api` extra)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from cri import api  # noqa: E402
from cri.server import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "classifier": "rule"}


def test_classify_matches_the_core(client):
    text = "Khana accha tha lekin kamra ganda tha."
    r = client.post("/reviews/classify", json={"text": text})
    got = [(m["aspect"], m["sentiment"]) for m in r.json()["mentions"]]
    expected = [(a, int(s)) for a, s in api.classify_text(text)[["aspect", "sentiment"]].values]
    assert got == expected == [("Food", 1), ("Room", -1), ("Cleanliness", -1)]
    assert r.json()["backend"] == "rule"


def test_classify_rejects_empty_and_oversized_text(client):
    assert client.post("/reviews/classify", json={"text": ""}).status_code == 422
    assert client.post("/reviews/classify", json={"text": "a" * 2001}).status_code == 422


def test_cors_allows_only_configured_origins(client):
    ok = client.options("/health", headers={"Origin": "http://localhost:3000",
                                            "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options("/health", headers={"Origin": "http://evil.example",
                                             "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
