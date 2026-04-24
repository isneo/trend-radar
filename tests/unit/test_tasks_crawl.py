from unittest.mock import MagicMock

import pytest

from app.worker import tasks as tasks_mod
from trendradar.api import CrawledItem


@pytest.mark.unit
async def test_persist_items_inserts_on_conflict(monkeypatch):
    saved: list[str] = []

    class _Session:
        async def execute(self, stmt):
            saved.append(str(stmt.compile(compile_kwargs={"literal_binds": False})).split("\n")[0])
            return MagicMock()
        async def commit(self): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass

    monkeypatch.setattr(tasks_mod, "AsyncSessionLocal", lambda: _Session())

    items = [CrawledItem("fp1", "HN", None, "t", "https://x/", None, None, {})]
    await tasks_mod._persist_crawl(items)

    assert saved, "expected at least one INSERT statement to be executed"
    assert any("INSERT INTO crawl_history" in s for s in saved)
