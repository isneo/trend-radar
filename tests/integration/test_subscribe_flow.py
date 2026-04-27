import pytest

from app.bot.repo import DbBotRepo


@pytest.mark.integration
async def test_upsert_user_then_subscribe(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(111, "alice", "Alice")
    sub = await repo.create_subscription(111, ["ai", "rag"], ["telegram"])
    assert sub["id"] >= 1
    listed = await repo.list_subscriptions(111)
    assert len(listed) == 1
    assert set(listed[0]["keywords"]) == {"ai", "rag"}


@pytest.mark.integration
async def test_delete_subscription(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(111, "alice", "Alice")
    sub = await repo.create_subscription(111, ["ai"], ["telegram"])
    ok = await repo.delete_subscription(111, sub["id"])
    assert ok is True
    assert await repo.list_subscriptions(111) == []


@pytest.mark.integration
async def test_delete_foreign_subscription_denied(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(111, "a", "A")
    await repo.upsert_user(222, "b", "B")
    sub = await repo.create_subscription(111, ["ai"], ["telegram"])
    ok = await repo.delete_subscription(222, sub["id"])
    assert ok is False
    assert await repo.list_subscriptions(111) != []
