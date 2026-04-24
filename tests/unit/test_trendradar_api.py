from datetime import datetime

import pytest

from trendradar.api import CrawledItem


@pytest.mark.unit
def test_crawled_item_is_frozen():
    item = CrawledItem(
        fingerprint="abc123", source="HN", category=None,
        title="Hello", url="https://example.com/", summary=None,
        published_at=None, raw={},
    )
    with pytest.raises(AttributeError):
        item.title = "mutated"


@pytest.mark.unit
def test_crawled_item_equality():
    a = CrawledItem("fp", "S", None, "T", "https://x/", None, None, {})
    b = CrawledItem("fp", "S", None, "T", "https://x/", None, None, {})
    assert a == b


@pytest.mark.unit
def test_fetch_all_yields_crawled_items(monkeypatch):
    """With mocked _fetch_all_impl, fetch_all returns CrawledItem instances."""
    from trendradar import api as api_mod

    fake_items = [
        CrawledItem("fp1", "HN", None, "t1", "https://a/", None, None, {}),
        CrawledItem("fp2", "TW", None, "t2", "https://b/", None, None, {}),
    ]

    def fake_impl(config_path, sources):
        yield from fake_items

    monkeypatch.setattr("trendradar.api_impl._fetch_all_impl", fake_impl)

    got = list(api_mod.fetch_all())
    assert got == fake_items
