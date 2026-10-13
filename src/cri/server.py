"""HTTP API for the Next.js frontend (``web/``): the G5 review core + the travel layer.

Run:  ``uvicorn cri.server:app --port 8000``  (needs ``pip install -e ".[api]"``).

Everything served is computed by ``cri.api`` and ``cri.travel`` on the SYNTHETIC review
cluster and the packaged travel resources; this module only validates input, maps
errors to HTTP codes and encodes results. Interactive docs: ``/docs``.

Configuration (environment variables):
- ``CRI_API_CORS_ORIGINS``: comma-separated browser origins allowed to call the API
  (default: the local Next.js dev server).
- ``CRI_MODEL_BACKEND``: classifier backend for ``/reviews/classify`` (see cri.classify).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import __version__, api
from .travel import alternatives, demand, planner, region, stays
from .travel.data import TravelData, UnknownIdError, load_travel_data

DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


class PlanRequest(BaseModel):
    origin: str = "delhi"
    destination: str
    start: date
    nights: int = Field(2, ge=1, le=14)
    travellers: int = Field(2, ge=1, le=12)
    budget: int = Field(..., gt=0, le=10_000_000)
    interests: list[str] = Field(default_factory=list, max_length=10)
    stay_pref: Literal["any", "budget", "standard", "family"] = "any"
    transport: Literal["car", "bus"] = "car"
    sustainability: bool = False


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


def _ctx(request: Request) -> tuple[api.ClusterData, TravelData]:
    return request.app.state.cluster, request.app.state.travel


def _json(obj) -> JSONResponse:
    return JSONResponse(jsonable_encoder(obj))


def _meta(d: api.ClusterData, td: TravelData) -> dict:
    return {
        "is_synthetic": d.is_synthetic,
        "source_name": d.source_name,
        "destinations": [
            {"id": x.id, "name": x.name, "state": x.place.state, "district": x.place.district,
             "region": x.region, "elevation_m": x.place.elevation_m, "lat": x.place.lat,
             "lon": x.place.lon, "belt": x.belt, "budget": x.budget, "popularity": x.popularity,
             "popularity_evidence": x.evidence, "sensitivity": x.sensitivity,
             "landscape": sorted(x.landscape), "tags": sorted(x.tags)}
            for x in td.destinations.values()
        ],
        "origins": [{"id": p.id, "name": p.name} for p in td.places.values() if p.kind == "origin"],
        "properties": [{"id": s.property_id, "destination": s.destination, "kind": s.kind}
                       for s in td.stays.values()],
        "interests": sorted({t for x in td.destinations.values() for t in x.tags}),
        "seller_categories": td.seller_categories,
        "holiday_coverage": {"start": td.coverage[0], "end": td.coverage[1]},
        "holidays": [{"date": h.day, "name": h.name, "source": td.source(h.source).title,
                      "url": td.source(h.source).url, "moon_dependent": h.moon_dependent}
                     for h in td.holidays],
        "assumed_windows": [vars(w) for w in td.windows],
        "demand_weights": td.demand,
        "ceilings": alternatives.CEILING,
        "costs": td.costs,
        "road_factor": td.road_factor,
        "emission_factors": [vars(f) | {"source_title": td.source(f.source).title,
                                        "url": td.source(f.source).url}
                             for f in td.emission_factors.values()],
        "sources": [vars(s) for s in td.sources.values()],
    }


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.cluster = api.load_cluster(synthetic=True)
        app.state.travel = load_travel_data()
        yield

    app = FastAPI(
        title="Cluster Review Intelligence API (SYNTHETIC prototype)",
        version=__version__,
        description="Review intelligence plus holiday-aware travel estimates for Uttarakhand "
                    "and Himachal hill destinations. All data is SYNTHETIC or sourced; demand is "
                    "an indicative estimate, not live traffic. See docs/API_CONTRACTS.md.",
        lifespan=lifespan,
    )
    origins = os.environ.get("CRI_API_CORS_ORIGINS", DEFAULT_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.exception_handler(UnknownIdError)
    async def _unknown(_: Request, exc: UnknownIdError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValueError)
    async def _invalid(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/health")
    def health(request: Request):
        d, _ = _ctx(request)
        return {"status": "ok", "is_synthetic": d.is_synthetic, "source_name": d.source_name,
                "classifier": os.environ.get("CRI_MODEL_BACKEND") or "rule",
                "demand_model": f"{demand.DEFAULT_MODEL.name} v{demand.DEFAULT_MODEL.version}"}

    @app.get("/meta")
    def meta(request: Request):
        return _json(_meta(*_ctx(request)))

    @app.get("/demand/calendar")
    def demand_calendar(request: Request, destination: str, start: date,
                        days: int = Query(30, ge=1, le=demand.MAX_DAYS)):
        _, td = _ctx(request)
        return _json(demand.demand_calendar(td, destination, start, days))

    @app.get("/demand/trip")
    def demand_trip(request: Request, destination: str, start: date,
                    nights: int = Query(2, ge=1, le=14)):
        _, td = _ctx(request)
        trip = demand.trip_demand(td, destination, start, nights)
        return _json({"trip": trip, "drivers": trip.drivers(),
                      "quieter": demand.quieter_dates(td, destination, start, nights)})

    @app.get("/demand/overview")
    def demand_overview(request: Request, start: date,
                        days: int = Query(30, ge=1, le=demand.MAX_DAYS)):
        _, td = _ctx(request)
        return _json(demand.regional_overview(td, start, days))

    @app.get("/alternatives")
    def get_alternatives(
        request: Request, destination: str, start: date,
        nights: int = Query(2, ge=1, le=14), home: str = "delhi",
        top_n: int = Query(3, ge=1, le=10),
        w_landscape: float = Query(0.30, ge=0, le=1), w_activities: float = Query(0.30, ge=0, le=1),
        w_budget: float = Query(0.15, ge=0, le=1), w_travel: float = Query(0.15, ge=0, le=1),
        w_season: float = Query(0.10, ge=0, le=1),
    ):
        _, td = _ctx(request)
        weights = alternatives.Weights(w_landscape, w_activities, w_budget, w_travel, w_season)
        return _json(alternatives.find_alternatives(td, destination, start, nights, home=home,
                                                    weights=weights, top_n=top_n))

    @app.get("/stays")
    def get_stays(request: Request, destination: str | None = None):
        return _json(stays.stay_profiles(*_ctx(request), destination))

    @app.get("/provider/{property_id}/insights")
    def provider(request: Request, property_id: str, start: date,
                 days: int = Query(90, ge=7, le=demand.MAX_DAYS)):
        d, td = _ctx(request)
        profile = stays.stay_profiles(d, td, property_id=property_id)[0]
        return _json({"profile": profile,
                      "insights": stays.provider_insights(d, td, property_id, start, days)})

    @app.get("/sellers")
    def get_sellers(request: Request, destination: str | None = None, category: str | None = None):
        _, td = _ctx(request)
        return _json(region.sellers_for(td, destination, category))

    @app.get("/sellers/opportunities")
    def opportunities(request: Request, destination: str, start: date,
                      days: int = Query(60, ge=1, le=demand.MAX_DAYS)):
        _, td = _ctx(request)
        return _json(region.seller_opportunities(td, destination, start, days))

    @app.get("/region")
    def get_region(request: Request, start: date, days: int = Query(30, ge=1, le=demand.MAX_DAYS)):
        return _json(region.region_dashboard(*_ctx(request), start, days))

    @app.post("/plan")
    def plan(request: Request, body: PlanRequest):
        d, td = _ctx(request)
        inp = planner.PlanInput(**(body.model_dump() | {"interests": tuple(body.interests)}))
        return _json(planner.plan_trip(d, td, inp))

    @app.post("/reviews/classify")
    def classify(body: ClassifyRequest):
        rows = api.classify_text(body.text)
        return {"backend": os.environ.get("CRI_MODEL_BACKEND") or "rule",
                "mentions": rows.to_dict(orient="records")}

    return app


app = create_app()
