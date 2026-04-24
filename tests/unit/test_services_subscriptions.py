import pytest

from app.services.subscriptions import parse_keywords, format_subscription_list


@pytest.mark.unit
class TestParseKeywords:
    def test_comma_delimited(self):
        assert parse_keywords("大模型, agent, rag") == ["大模型", "agent", "rag"]

    def test_strips_whitespace(self):
        assert parse_keywords("  ai ,  ml  ") == ["ai", "ml"]

    def test_dedups_case_insensitive(self):
        assert parse_keywords("AI, ai, Ai") == ["ai"]

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_keywords("")

    def test_rejects_all_whitespace(self):
        with pytest.raises(ValueError):
            parse_keywords(" ,  ,")


@pytest.mark.unit
def test_format_subscription_list_empty():
    assert format_subscription_list([]) == "你还没有任何订阅。发 /subscribe 关键词 来添加。"


@pytest.mark.unit
def test_format_subscription_list_two_items():
    subs = [
        {"id": 3, "keywords": ["ai"], "delivery_targets": ["telegram"], "is_active": True},
        {"id": 5, "keywords": ["大模型", "agent"], "delivery_targets": ["telegram", "feishu:42"], "is_active": False},
    ]
    out = format_subscription_list(subs)
    assert "3" in out and "ai" in out
    assert "5" in out and "大模型" in out and "agent" in out
    assert "已暂停" in out  # sub 5 is_active=False
