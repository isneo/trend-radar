"""Public library API for the trendradar engine.

Consumed by app.worker.tasks.crawl_task. This is the ONLY surface the
platform layer depends on — core internals may change freely.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CrawledItem:
    fingerprint: str
    source: str
    category: str | None
    title: str
    url: str
    summary: str | None
    published_at: datetime | None
    raw: dict[str, Any]


def fetch_all(
    config_path: str | None = None,
    sources: list[str] | None = None,
) -> Iterable[CrawledItem]:
    """Crawl all (or selected) sources and yield structured items.

    Does NOT write HTML, SQLite, or send notifications — those are the
    single-user CLI's concern. Platform callers iterate and persist.
    """
    from trendradar.api_impl import _fetch_all_impl
    yield from _fetch_all_impl(config_path=config_path, sources=sources)
