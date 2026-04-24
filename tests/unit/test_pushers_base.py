import pytest

from app.pushers.base import BrokenChannel, PushResult, Retryable


@pytest.mark.unit
def test_push_result_enum_values():
    assert PushResult.SENT.value == "sent"
    assert PushResult.SKIPPED.value == "skipped"


@pytest.mark.unit
def test_broken_channel_exception():
    err = BrokenChannel("webhook deleted")
    assert str(err) == "webhook deleted"
    assert isinstance(err, Exception)


@pytest.mark.unit
def test_retryable_exception():
    err = Retryable("timeout")
    assert isinstance(err, Exception)
