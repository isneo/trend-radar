import httpx
import pytest
import respx

from app.bot.repo import DbBotRepo

GOOD_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/token-xyz"


@pytest.mark.integration
@respx.mock
async def test_probe_webhook_success(db):
    respx.post(GOOD_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
    repo = DbBotRepo(db)
    assert await repo.probe_webhook(GOOD_URL) is True


@pytest.mark.integration
@respx.mock
async def test_bind_and_list(db):
    respx.post(GOOD_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
    repo = DbBotRepo(db)
    await repo.upsert_user(777, "bob", "Bob")
    group = await repo.create_feishu_group(777, "AI 前沿群", GOOD_URL, ["rag", "agent"])
    assert group["id"] >= 1
    listed = await repo.list_feishu_groups(777)
    assert len(listed) == 1
    assert set(listed[0]["keywords"]) == {"rag", "agent"}
