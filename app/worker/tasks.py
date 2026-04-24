"""Celery tasks — real crawl + dispatch logic lands in Task #7.

Current state: ping task only, proves Celery infrastructure works.
"""

from __future__ import annotations

from app.worker.celery_app import celery_app


@celery_app.task(name="app.ping")
def ping() -> str:
    return "pong"
