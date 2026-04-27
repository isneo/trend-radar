"""Feishu webhook validation + group helpers."""

from __future__ import annotations

from urllib.parse import urlparse

_ALLOWED_HOSTS: frozenset[str] = frozenset({
    "open.feishu.cn",
    "open.larksuite.com",
})
_REQUIRED_PATH_PREFIX = "/open-apis/bot/v2/hook/"


def is_valid_feishu_webhook(url: str) -> bool:
    if not url:
        return False
    try:
        parts = urlparse(url)
    except ValueError:
        return False
    if parts.scheme != "https":
        return False
    if parts.hostname not in _ALLOWED_HOSTS:
        return False
    if not parts.path.startswith(_REQUIRED_PATH_PREFIX):
        return False
    # token segment must be non-empty
    token = parts.path[len(_REQUIRED_PATH_PREFIX):]
    return bool(token.strip("/"))
