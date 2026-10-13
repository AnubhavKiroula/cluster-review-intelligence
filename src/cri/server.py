"""HTTP API for the Next.js frontend (``web/``): live review classification.

Every page reads the static snapshot (``web/scripts/export_snapshot.py``) except the
explorer's *Try your own review*, which posts typed text here and gets back the same
aspect / sentiment / clause rows the pipeline produces (``cri.api.classify_text``).

Run:  ``uvicorn cri.server:app --port 8000``  (needs ``pip install -e ".[api]"``).
Interactive docs: ``/docs``.

Configuration (environment variables):
- ``CRI_API_CORS_ORIGINS``: comma-separated browser origins allowed to call the API
  (default: the local Next.js dev server).
- ``CRI_MODEL_BACKEND``: classifier backend for ``/reviews/classify`` (see cri.classify).
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__, api

DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


def _backend() -> str:
    return os.environ.get("CRI_MODEL_BACKEND") or "rule"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cluster Review Intelligence API",
        version=__version__,
        description="Classify one typed review into aspect, sentiment and the clause it came "
                    "from. See docs/API_CONTRACTS.md.",
    )
    origins = os.environ.get("CRI_API_CORS_ORIGINS", DEFAULT_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "classifier": _backend()}

    @app.post("/reviews/classify")
    def classify(body: ClassifyRequest):
        rows = api.classify_text(body.text)
        return {"backend": _backend(), "mentions": rows.to_dict(orient="records")}

    return app


app = create_app()
