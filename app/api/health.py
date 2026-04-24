"""Health check endpoints.

GET /healthz        — shallow, always 200
GET /healthz?deep=1 — checks Postgres, Redis, worker heartbeat freshness
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.db import engine

router = APIRouter()

_HEARTBEAT_MAX_AGE = 300  # seconds


@router.get("/healthz")
async def healthz(deep: int = 0, response: Response = None) -> dict:
    if not deep:
        return {"status": "ok"}

    checks: dict[str, str] = {}
    ok = True

    # --- Postgres ---
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        ok = False

    # --- Redis ---
    try:
        import redis.asyncio as aioredis

        from app.config import get_settings

        r = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        ok = False

    # --- Worker heartbeat ---
    try:
        from app.worker.heartbeat import read_latest

        latest = read_latest()
        if latest is None:
            checks["worker_heartbeat"] = "missing"
            ok = False
        elif time.time() - latest > _HEARTBEAT_MAX_AGE:
            age = int(time.time() - latest)
            checks["worker_heartbeat"] = f"stale ({age}s ago)"
            ok = False
        else:
            checks["worker_heartbeat"] = "ok"
    except Exception as exc:
        checks["worker_heartbeat"] = f"error: {exc}"
        ok = False

    if not ok and response is not None:
        response.status_code = 503

    return {"status": "ok" if ok else "degraded", **checks}
