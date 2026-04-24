"""Common contracts for channel pushers (telegram, feishu).

Error semantics drive ADR-011 retry policy:
- BrokenChannel → 4xx; mark channel broken, no retry.
- Retryable    → 5xx / timeout / network; Celery autoretry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from trendradar.api import CrawledItem


class PushResult(str, Enum):
    SENT = "sent"
    SKIPPED = "skipped"


class BrokenChannel(Exception):
    """Permanent failure. Caller should mark the channel broken."""


class Retryable(Exception):
    """Transient failure. Caller should retry with backoff."""


@dataclass(frozen=True)
class PushContext:
    """Carries what a pusher needs — kept small and concrete."""
    target_external_id: str   # TG chat id OR Feishu webhook URL


class Pusher(Protocol):
    async def push(self, ctx: PushContext, item: CrawledItem) -> PushResult: ...
