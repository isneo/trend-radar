"""Implementation of the fetch_all public API.

Bridges the new structured-output contract to the existing DataFetcher
plumbing in trendradar.crawler. Single-user CLI semantics (HTML / SQLite /
notification) are the CLI layer's responsibility and are NOT invoked here.

Real DataFetcher shape (verified from fetcher.py + __main__.py):
  - Constructor: DataFetcher(proxy_url=None, api_url=None)
  - Method: crawl_websites(ids_list, request_interval) ->
        (results: Dict[source_id, Dict[title, {ranks, url, mobileUrl}]],
         id_to_name: Dict[source_id, name],
         failed_ids: List[source_id])
  - items are title-keyed dicts, NOT a flat list
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from app.fingerprint import fingerprint as _fingerprint

log = logging.getLogger(__name__)


def _fetch_all_impl(
    config_path: str | None = None,
    sources: list[str] | None = None,
) -> Iterable["CrawledItem"]:  # forward-ref to avoid cycle
    from trendradar.api import CrawledItem
    from trendradar.core import load_config
    from trendradar.crawler import DataFetcher

    config = load_config(config_path) if config_path else load_config()

    platforms = config.get("PLATFORMS", [])
    # Build ids_list as (id, name) tuples, optionally filtered
    ids_list = [
        (p["id"], p.get("name", p["id"]))
        for p in platforms
        if not sources or p["id"] in sources
    ]

    use_proxy = bool(config.get("USE_PROXY", False))
    proxy_url = config.get("DEFAULT_PROXY") if use_proxy else None
    request_interval = config.get("REQUEST_INTERVAL", 100)

    if not ids_list:
        log.warning("fetch_all: no PLATFORMS configured; yielding 0 items")
        return

    fetcher = DataFetcher(proxy_url=proxy_url)
    results, id_to_name, _ = fetcher.crawl_websites(ids_list, request_interval)

    # results: Dict[source_id, Dict[title, {ranks, url, mobileUrl}]]
    for source_id, title_map in results.items():
        source_name = id_to_name.get(source_id, source_id)
        for title, item_data in title_map.items():
            url = item_data.get("url") or item_data.get("mobileUrl", "")
            if not url or not title:
                log.debug("skipping item with missing url/title in source=%s: %s", source_id, title)
                continue
            yield CrawledItem(
                fingerprint=_fingerprint(source_name, url),
                source=source_name,
                category=None,
                title=str(title),
                url=url,
                summary=None,
                published_at=None,
                raw={
                    "ranks": item_data.get("ranks", []),
                    "mobileUrl": item_data.get("mobileUrl", ""),
                },
            )
