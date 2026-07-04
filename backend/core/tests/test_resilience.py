import pytest

from core.services.resilience import is_transient, retry_call


class Transient(Exception):
    status_code = 503


class RateLimited(Exception):
    status_code = 429


def test_is_transient_by_status():
    assert is_transient(Transient())
    assert is_transient(RateLimited())


def test_is_transient_by_message():
    assert is_transient(Exception("RESOURCE_EXHAUSTED: quota"))
    assert is_transient(Exception("connection reset"))


def test_not_transient():
    assert not is_transient(ValueError("bad input"))
    assert not is_transient(Exception("invalid_request: missing field"))


def test_retries_then_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Transient()
        return "ok"

    assert retry_call(flaky, attempts=3, sleep=lambda _: None) == "ok"
    assert calls["n"] == 3


def test_gives_up_after_attempts():
    calls = {"n": 0}

    def always():
        calls["n"] += 1
        raise Transient()

    with pytest.raises(Transient):
        retry_call(always, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 3


def test_non_transient_raises_immediately():
    calls = {"n": 0}

    def bad():
        calls["n"] += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        retry_call(bad, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 1  # no retries on a non-transient error
