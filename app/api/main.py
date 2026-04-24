"""FastAPI app — V1 exposes /healthz and /healthz?deep=1."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.observability.sentry import init_sentry

init_sentry("api")

app = FastAPI(title="TrendRadar Platform", version="0.1.0")
app.include_router(health_router)
