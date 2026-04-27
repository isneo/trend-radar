import pytest

from app.services.dispatcher import item_matches


@pytest.mark.unit
class TestItemMatches:
    def test_contains_single_keyword(self):
        assert item_matches("GPT-5 evaluation", ["gpt-5"], []) is True

    def test_case_insensitive(self):
        assert item_matches("OpenAI releases GPT-5", ["gpt-5"], []) is True

    def test_no_match(self):
        assert item_matches("Weather report", ["gpt-5"], []) is False

    def test_any_of_keywords_hits(self):
        assert item_matches("Anthropic announcement", ["gpt", "anthropic"], []) is True

    def test_excluded_keyword_blocks(self):
        assert item_matches("GPT-5 user agent bug", ["gpt-5"], ["user agent"]) is False

    def test_excluded_absent_keeps_match(self):
        assert item_matches("GPT-5 big news", ["gpt-5"], ["user agent"]) is True
