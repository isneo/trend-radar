import httpx
import pytest
import respx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Retryable
from app.pushers.feishu import FeishuPusher
from trendradar.api import CrawledItem


def _item() -> CrawledItem:
    return CrawledItem(
        fingerprint="fp", source="HN", category="论文",
        title="T", url="https://example.com/", summary="s",
        published_at=None, raw={},
    )


@pytest.fixture
def pusher() -> FeishuPusher:
    return FeishuPusher()


_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/abc"


@pytest.mark.unit
@respx.mock
async def test_success_returns_sent(pusher: FeishuPusher):
    route = respx.post(_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
    result = await pusher.push(PushContext(target_external_id=_URL), _item())
    assert result is PushResult.SENT
    assert route.called
    # Body should be a rich card (msg_type = "interactive")
    body = route.calls[0].request.content
    assert b'"msg_type":"interactive"' in body or b'"msg_type": "interactive"' in body


@pytest.mark.unit
@respx.mock
async def test_code_nonzero_is_broken(pusher: FeishuPusher):
    respx.post(_URL).mock(return_value=httpx.Response(200, json={"code": 19021}))
    with pytest.raises(BrokenChannel):
        await pusher.push(PushContext(target_external_id=_URL), _item())


@pytest.mark.unit
@respx.mock
async def test_5xx_is_retryable(pusher: FeishuPusher):
    respx.post(_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(Retryable):
        await pusher.push(PushContext(target_external_id=_URL), _item())


@pytest.mark.unit
@respx.mock
async def test_malformed_json_is_retryable(pusher: FeishuPusher):
    respx.post(_URL).mock(
        return_value=httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})
    )
    with pytest.raises(Retryable):
        await pusher.push(PushContext(target_external_id=_URL), _item())
