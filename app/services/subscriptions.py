"""Pure-Python business logic for subscriptions (no DB session here).

DB CRUD happens in the caller (bot handler) using SQLAlchemy session.
These helpers are easy to unit-test without a DB.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def parse_keywords(raw: str) -> list[str]:
    """Comma-delimited (ASCII or fullwidth) → normalized, deduped, lowercased, non-empty."""
    normalized = raw.replace("，", ",")
    seen: dict[str, None] = {}
    for token in normalized.split(","):
        t = token.strip().lower()
        if t:
            seen[t] = None
    if not seen:
        raise ValueError("关键词不能为空")
    return list(seen.keys())


def format_subscription_list(subs: Sequence[dict[str, Any]]) -> str:
    if not subs:
        return "你还没有任何订阅。发 /subscribe 关键词 来添加。"
    lines = ["<b>你的订阅：</b>"]
    for s in subs:
        flag = "" if s["is_active"] else " （已暂停）"
        kws = ", ".join(s["keywords"])
        targets = ", ".join(s["delivery_targets"])
        lines.append(f"#{s['id']}  {kws}  →  {targets}{flag}")
    return "\n".join(lines)
