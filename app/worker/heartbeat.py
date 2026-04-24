"""Worker heartbeat — writes a timestamp to Redis every 60s.

Each worker instance writes to a unique key so multiple workers
can coexist; read_latest() returns the freshest timestamp across all.
"""

from __future__ import annotations

import logging
import threading
import time

from app.config import get_settings

_KEY_PREFIX = "trendradar:worker:heartbeat:"
_TTL_SECONDS = 120
_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


def _loop() -> None:
    settings = get_settings()
    import redis

    client = redis.from_url(settings.redis_url, decode_responses=True)
    key = f"{_KEY_PREFIX}{threading.get_ident()}"
    while True:
        try:
            client.set(key, time.time(), ex=_TTL_SECONDS)
        except Exception:
            logger.exception("heartbeat write failed")
        time.sleep(_INTERVAL_SECONDS)


def start_heartbeat() -> None:
    """Spawn a daemon thread that writes heartbeat to Redis."""
    t = threading.Thread(target=_loop, daemon=True, name="worker-heartbeat")
    t.start()
    logger.info("worker heartbeat started (key prefix=%s)", _KEY_PREFIX)


def read_latest() -> float | None:
    """Return the most recent heartbeat epoch, or None if no keys found."""
    settings = get_settings()
    import redis

    client = redis.from_url(settings.redis_url, decode_responses=True)
    keys = client.keys(f"{_KEY_PREFIX}*")
    if not keys:
        return None
    values = client.mget(keys)
    epochs = [float(v) for v in values if v is not None]
    return max(epochs) if epochs else None
