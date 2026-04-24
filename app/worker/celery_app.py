from __future__ import annotations

from celery import Celery

from app.config import get_settings
from app.observability.sentry import init_sentry

_settings = get_settings()
init_sentry("worker")

celery_app: Celery = Celery(
    "trendradar",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_hijack_root_logger=False,
    # --- ADR-011 hardening ---
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # --- beat ---
    beat_schedule={
        "hourly-crawl": {
            "task": "app.tasks.crawl",
            "schedule": 3600.0,
        },
    },
)

from celery.signals import worker_ready  # noqa: E402


@worker_ready.connect
def _on_worker_ready(**_) -> None:
    from app.worker.heartbeat import start_heartbeat

    start_heartbeat()
