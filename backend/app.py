"""FastAPI application factory.

Layers:
  routers/   — HTTP routers (request/response)
  services/  — use-cases / orchestration
  deid/      — de-identify ops, rules, models
  store/     — ephemeral session / download state
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import review


def create_app() -> FastAPI:
    application = FastAPI(
        title="Clinical · De-identify",
        description="Local synthetic-data de-identification API.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(review.router)
    return application


app = create_app()
