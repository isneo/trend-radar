"""Telegram Bot API pusher.

Uses sendMessage with HTML parse mode; 10s timeout (ADR-011 §3).
"""

from __future__ import annotations

import os
from html import escape

import httpx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Pusher, Retryable
from trendradar.api import CrawledItem


class TelegramPusher(Pusher):
    def __init__(self, bot_token: str, *, timeout: float = 10.0) -> None:
        self._base = f"https://api.telegram.org/bot{bot_token}"
        self._timeout = timeout

    async def push(self, ctx: PushContext, item: CrawledItem) -> PushResult:
        body = _format(item)
        url = f"{self._base}/sendMessage"
        payload = {
            "chat_id": ctx.target_external_id,
            "text": body,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            async with httpx.AsyncClient(
                timeout=self._timeout, trust_env=False, proxy=proxy
            ) as client:
                resp = await client.post(url, json=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise Retryable(f"telegram network: {e}") from e

        if 200 <= resp.status_code < 300:
            return PushResult.SENT
        if 400 <= resp.status_code < 500:
            raise BrokenChannel(f"telegram {resp.status_code}: {resp.text[:200]}")
        raise Retryable(f"telegram {resp.status_code}")


def _format(item: CrawledItem) -> str:
    cat = f"【{item.category}】 " if item.category else ""
    lines = [f"<b>{cat}{escape(item.title)}</b>"]
    if item.summary:
        lines.append(escape(item.summary[:280]))
    lines.append(f'<a href="{escape(item.url)}">阅读原文</a>  ·  {escape(item.source)}')
    return "\n".join(lines)
