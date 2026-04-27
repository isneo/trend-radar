"""Sentry initialization — safe to call from any process.

Reads SENTRY_DSN from env; no-ops silently if unset.
"""

from __future__ import annotations

import os


def init_sentry(proc: str) -> None:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("APP_ENV", "local"),
        traces_sample_rate=0.1,
    )
    sentry_sdk.set_tag("proc", proc)
