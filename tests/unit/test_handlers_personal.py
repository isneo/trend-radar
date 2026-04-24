from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.personal import (
    handle_list,
    handle_start,
    handle_subscribe,
    handle_unsubscribe,
)


class _Msg:
    """Minimal aiogram.types.Message double."""

    def __init__(self, text: str, tg_user_id: int = 123, username: str = "neo"):
        self.text = text
        self.from_user = MagicMock(id=tg_user_id, username=username, full_name="Neo")
        self.answer = AsyncMock()


class _FakeRepo:
    def __init__(self):
        self.users: dict[int, dict] = {}
        self.subs: list[dict] = []
        self.next_sub_id = 1

    async def upsert_user(self, tg_user_id, tg_username, display_name):
        if tg_user_id not in self.users:
            self.users[tg_user_id] = {"id": tg_user_id, "username": tg_username, "name": display_name}
        return self.users[tg_user_id]

    async def create_subscription(self, user_id, keywords, targets):
        sub = {"id": self.next_sub_id, "user_id": user_id, "keywords": keywords,
               "delivery_targets": targets, "is_active": True}
        self.subs.append(sub)
        self.next_sub_id += 1
        return sub

    async def list_subscriptions(self, user_id):
        return [s for s in self.subs if s["user_id"] == user_id]

    async def delete_subscription(self, user_id, sub_id):
        before = len(self.subs)
        self.subs = [s for s in self.subs if not (s["user_id"] == user_id and s["id"] == sub_id)]
        return len(self.subs) < before


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.mark.unit
async def test_start_registers_user_and_greets(repo: _FakeRepo):
    msg = _Msg("/start")
    await handle_start(msg, repo=repo)
    assert 123 in repo.users
    assert msg.answer.called
    assert "欢迎" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_subscribe_creates_subscription(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    msg = _Msg("/subscribe 大模型, agent")
    await handle_subscribe(msg, repo=repo)
    assert len(repo.subs) == 1
    assert repo.subs[0]["keywords"] == ["大模型", "agent"]
    assert repo.subs[0]["delivery_targets"] == ["telegram"]


@pytest.mark.unit
async def test_subscribe_empty_keywords_rejects(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    msg = _Msg("/subscribe   ")
    await handle_subscribe(msg, repo=repo)
    assert len(repo.subs) == 0
    assert "用法" in msg.answer.call_args.args[0] or "不能为空" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_list_empty(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    msg = _Msg("/list")
    await handle_list(msg, repo=repo)
    assert "还没有任何订阅" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_unsubscribe_removes(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    await repo.create_subscription(123, ["ai"], ["telegram"])
    msg = _Msg("/unsubscribe 1")
    await handle_unsubscribe(msg, repo=repo)
    assert repo.subs == []
