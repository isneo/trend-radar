import pytest

from app.fingerprint import canonicalize_url, fingerprint


@pytest.mark.unit
class TestCanonicalizeUrl:
    def test_strips_utm_params(self):
        raw = "https://example.com/post?id=1&utm_source=tw&utm_medium=x"
        assert canonicalize_url(raw) == "https://example.com/post?id=1"

    def test_strips_fbclid(self):
        raw = "https://example.com/?fbclid=abc&x=1"
        assert canonicalize_url(raw) == "https://example.com/?x=1"

    def test_strips_trailing_slash(self):
        assert canonicalize_url("https://example.com/post/") == "https://example.com/post"

    def test_preserves_path_and_non_tracking_params(self):
        raw = "https://example.com/a/b?q=python&page=2"
        assert canonicalize_url(raw) == "https://example.com/a/b?page=2&q=python"

    def test_lowercases_scheme_and_host(self):
        assert canonicalize_url("HTTPS://Example.COM/X") == "https://example.com/X"


@pytest.mark.unit
class TestFingerprint:
    def test_is_deterministic(self):
        fp1 = fingerprint("HN", "https://example.com/x")
        fp2 = fingerprint("HN", "https://example.com/x")
        assert fp1 == fp2

    def test_different_source_different_fp(self):
        assert fingerprint("HN", "https://x.com/a") != fingerprint("TW", "https://x.com/a")

    def test_tracking_params_do_not_change_fp(self):
        fp1 = fingerprint("HN", "https://example.com/x")
        fp2 = fingerprint("HN", "https://example.com/x?utm_source=t")
        assert fp1 == fp2

    def test_length_is_16_hex_chars(self):
        fp = fingerprint("HN", "https://example.com/")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)
