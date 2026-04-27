"""URL canonicalization + stable content fingerprinting (ADR-011)."""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAM_PREFIXES: tuple[str, ...] = ("utm_",)
_TRACKING_PARAM_EXACT: frozenset[str] = frozenset({
    "fbclid", "gclid", "msclkid", "yclid", "mc_cid", "mc_eid",
    "ref", "ref_src", "ref_url", "_hsenc", "_hsmi",
})


def canonicalize_url(url: str) -> str:
    """Remove tracking params, normalize scheme/host case, strip trailing slash."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_param(k)
    ]
    kept.sort()
    query = urlencode(kept)

    path = parts.path
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    return urlunsplit((scheme, netloc, path, query, ""))


def _is_tracking_param(key: str) -> bool:
    lk = key.lower()
    if lk in _TRACKING_PARAM_EXACT:
        return True
    return any(lk.startswith(p) for p in _TRACKING_PARAM_PREFIXES)


def fingerprint(source: str, url: str) -> str:
    """Stable 16-hex fingerprint for dedup."""
    key = f"{source}|{canonicalize_url(url)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
