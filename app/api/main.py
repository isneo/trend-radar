"""FastAPI app — V1 only exposes /healthz.

Future: TG webhook endpoint for prod, admin APIs.
Run local: uv run uvicorn app.api.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="TrendRadar Platform", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "env": settings.app_env}
