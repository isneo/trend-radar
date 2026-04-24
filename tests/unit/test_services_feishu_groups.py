import pytest

from app.services.feishu_groups import is_valid_feishu_webhook


@pytest.mark.unit
@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://open.feishu.cn/open-apis/bot/v2/hook/abc-123", True),
        ("http://open.feishu.cn/open-apis/bot/v2/hook/abc", False),   # http not https
        ("https://open.larksuite.com/open-apis/bot/v2/hook/abc", True),  # intl
        ("https://evil.example/feishu", False),
        ("not-a-url", False),
        ("", False),
    ],
)
def test_is_valid_feishu_webhook(url: str, ok: bool):
    assert is_valid_feishu_webhook(url) is ok
