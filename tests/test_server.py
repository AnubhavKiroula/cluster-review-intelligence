"""HTTP API contract (FastAPI TestClient; skipped without the `api` extra)."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from cri import api  # noqa: E402
from cri.server import create_app  # noqa: E402

START = "2026-12-25"


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize("path", [
    "/health",
    "/meta",
    f"/demand/calendar?destination=mussoorie&start={START}&days=7",
    f"/demand/trip?destination=mussoorie&start={START}&nights=2",
    f"/demand/overview?start={START}&days=7",
    f"/alternatives?destination=mussoorie&start={START}&nights=2",
    "/stays?destination=kanatal",
    "/provider/Property%20F/insights?start=2026-10-13&days=60",
    "/sellers?destination=kanatal",
    f"/sellers/opportunities?destination=kanatal&start={START}&days=30",
    f"/region?start={START}&days=14",
])
def test_get_endpoints_return_json(client, path):
    r = client.get(path)
    assert r.status_code == 200, r.text
    assert r.json()


def test_unknown_ids_are_404_and_bad_input_422(client):
    assert client.get(f"/demand/calendar?destination=atlantis&start={START}").status_code == 404
    assert client.get("/provider/Property%20Z/insights?start=2026-10-13").status_code == 404
    assert client.get(f"/demand/calendar?destination=manali&start={START}&days=500").status_code \
        == 422
    assert client.get("/demand/calendar?destination=manali&start=not-a-date").status_code == 422
    bad = client.post("/plan", json={"destination": "kanatal", "start": START, "budget": -1})
    assert bad.status_code == 422
    unknown_interest = client.post("/plan", json={"destination": "kanatal", "start": START,
                                                  "budget": 20000, "interests": ["skydiving"]})
    assert unknown_interest.status_code == 422


def test_plan_and_demand_payloads(client):
    r = client.post("/plan", json={"destination": "kanatal", "start": START, "nights": 2,
                                   "travellers": 3, "budget": 30000, "transport": "bus"})
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == sum(line["value"] for line in body["costs"])
    day = client.get(f"/demand/calendar?destination=mussoorie&start={START}&days=1").json()[0]
    assert day["index"] == sum(f["value"] for f in day["factors"])
    assert {f["basis"] for f in day["factors"]} <= {"fact", "synthetic", "assumption", "derived"}


def test_no_nan_reaches_json(client):
    # Scorecard CIs are NaN below 10 reviews; JSON has no NaN, so they must arrive as null.
    profiles = client.get("/stays").json()
    for p in profiles:
        for f in p["feedback"]:
            for key in ("mean", "ci_low", "ci_high"):
                assert f[key] is None or math.isfinite(f[key])


def test_classify_matches_the_core(client):
    text = "Khana accha tha lekin kamra ganda tha."
    r = client.post("/reviews/classify", json={"text": text})
    got = [(m["aspect"], m["sentiment"]) for m in r.json()["mentions"]]
    expected = [(a, int(s)) for a, s in api.classify_text(text)[["aspect", "sentiment"]].values]
    assert got == expected == [("Food", 1), ("Room", -1), ("Cleanliness", -1)]
    assert client.post("/reviews/classify", json={"text": ""}).status_code == 422


def test_cors_allows_only_configured_origins(client):
    ok = client.options("/health", headers={"Origin": "http://localhost:3000",
                                            "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options("/health", headers={"Origin": "http://evil.example",
                                             "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
