from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.feishu import (
    handle_add_feishu_group,
    handle_my_feishu_groups,
    handle_remove_feishu_group,
)


class _Msg:
    def __init__(self, text: str):
        self.text = text
        self.from_user = MagicMock(id=123, username="neo", full_name="Neo")
        self.answer = AsyncMock()


class _FakeRepo:
    def __init__(self):
        self.groups: list[dict] = []
        self.next_id = 1
        self.probe_ok = True

    async def upsert_user(self, *a, **kw):
        return {"id": 123}

    async def create_feishu_group(self, owner_user_id, name, webhook_url, keywords):
        g = {"id": self.next_id, "owner": owner_user_id, "name": name, "url": webhook_url,
             "keywords": keywords, "status": "active"}
        self.groups.append(g)
        self.next_id += 1
        return g

    async def list_feishu_groups(self, owner_user_id):
        return [g for g in self.groups if g["owner"] == owner_user_id]

    async def remove_feishu_group(self, owner_user_id, group_id):
        before = len(self.groups)
        self.groups = [g for g in self.groups if not (g["owner"] == owner_user_id and g["id"] == group_id)]
        return len(self.groups) < before

    async def probe_webhook(self, url: str) -> bool:
        return self.probe_ok


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


GOOD_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/abcdef"


@pytest.mark.unit
async def test_add_feishu_group_happy(repo: _FakeRepo):
    msg = _Msg(f"/add_feishu_group {GOOD_URL} 大模型, agent")
    await handle_add_feishu_group(msg, repo=repo)
    assert len(repo.groups) == 1
    assert repo.groups[0]["keywords"] == ["大模型", "agent"]
    assert "已绑定" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_add_feishu_group_invalid_url(repo: _FakeRepo):
    msg = _Msg("/add_feishu_group https://evil.example/x 大模型")
    await handle_add_feishu_group(msg, repo=repo)
    assert len(repo.groups) == 0
    assert "webhook" in msg.answer.call_args.args[0].lower()


@pytest.mark.unit
async def test_add_feishu_group_probe_failure(repo: _FakeRepo):
    repo.probe_ok = False
    msg = _Msg(f"/add_feishu_group {GOOD_URL} 大模型")
    await handle_add_feishu_group(msg, repo=repo)
    assert len(repo.groups) == 0
    assert "不可达" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_my_feishu_groups_empty(repo: _FakeRepo):
    msg = _Msg("/my_feishu_groups")
    await handle_my_feishu_groups(msg, repo=repo)
    assert "没有" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_remove_feishu_group(repo: _FakeRepo):
    await repo.create_feishu_group(123, "g", GOOD_URL, ["x"])
    msg = _Msg("/remove_feishu_group 1")
    await handle_remove_feishu_group(msg, repo=repo)
    assert repo.groups == []
