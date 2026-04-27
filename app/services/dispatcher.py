"""Match + fanout logic for dispatch_task (ADR-005 + ADR-011)."""

from __future__ import annotations

from collections.abc import Iterable


def item_matches(
    title: str,
    keywords: Iterable[str],
    excluded: Iterable[str],
) -> bool:
    """Case-insensitive substring match. Excluded wins over included."""
    lower = title.lower()
    if any(ex.lower() in lower for ex in excluded if ex):
        return False
    return any(kw.lower() in lower for kw in keywords if kw)
