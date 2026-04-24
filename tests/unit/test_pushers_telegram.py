import httpx
import pytest
import respx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Retryable
from app.pushers.telegram import TelegramPusher
from trendradar.api import CrawledItem


def _item() -> CrawledItem:
    return CrawledItem(
        fingerprint="fp", source="HN", category="论文",
        title="T", url="https://example.com/", summary="s",
        published_at=None, raw={},
    )


@pytest.fixture
def pusher() -> TelegramPusher:
    return TelegramPusher(bot_token="TOK")


@pytest.mark.unit
@respx.mock
async def test_success_returns_sent(pusher: TelegramPusher):
    route = respx.post("https://api.telegram.org/botTOK/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = await pusher.push(PushContext(target_external_id="123"), _item())
    assert result is PushResult.SENT
    assert route.called


@pytest.mark.unit
@respx.mock
async def test_4xx_raises_broken(pusher: TelegramPusher):
    respx.post("https://api.telegram.org/botTOK/sendMessage").mock(
        return_value=httpx.Response(403, json={"ok": False})
    )
    with pytest.raises(BrokenChannel):
        await pusher.push(PushContext(target_external_id="123"), _item())


@pytest.mark.unit
@respx.mock
async def test_5xx_raises_retryable(pusher: TelegramPusher):
    respx.post("https://api.telegram.org/botTOK/sendMessage").mock(
        return_value=httpx.Response(502, json={"ok": False})
    )
    with pytest.raises(Retryable):
        await pusher.push(PushContext(target_external_id="123"), _item())
