"""Feishu custom-bot webhook pusher.

Sends interactive card (richer than plain text). Feishu returns 200 with
`code != 0` on logical failures (e.g., invalid signature, deleted bot) —
these are treated as BrokenChannel, not Retryable.
"""

from __future__ import annotations

import httpx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Pusher, Retryable
from trendradar.api import CrawledItem

_TRANSIENT_CODES: frozenset[int] = frozenset({9499, 9504})  # Feishu internal error range


class FeishuPusher(Pusher):
    def __init__(self, *, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def push(self, ctx: PushContext, item: CrawledItem) -> PushResult:
        payload = {"msg_type": "interactive", "card": _card(item)}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
                resp = await client.post(ctx.target_external_id, json=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise Retryable(f"feishu network: {e}") from e

        if 500 <= resp.status_code < 600:
            raise Retryable(f"feishu {resp.status_code}")
        if resp.status_code >= 400:
            raise BrokenChannel(f"feishu {resp.status_code}: {resp.text[:200]}")

        body = resp.json() if resp.content else {}
        code = int(body.get("code", 0))
        if code == 0:
            return PushResult.SENT
        if code in _TRANSIENT_CODES:
            raise Retryable(f"feishu code {code}")
        raise BrokenChannel(f"feishu code {code}: {body.get('msg','')}")


def _card(item: CrawledItem) -> dict:
    cat = f"【{item.category}】 " if item.category else ""
    elements: list[dict] = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**{cat}{item.title}**"}},
    ]
    if item.summary:
        elements.append({"tag": "div", "text": {"tag": "plain_text", "content": item.summary[:280]}})
    elements.append({
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": {"tag": "plain_text", "content": "阅读原文"},
            "type": "primary",
            "url": item.url,
        }],
    })
    return {
        "config": {"wide_screen_mode": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": item.source}},
        "elements": elements,
    }
