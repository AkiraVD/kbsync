"""Transient failures must not end a run."""

import pytest
import requests

from src.http import MAX_ATTEMPTS, Client


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.headers: dict = {}
        self.attempts = 0

    def request(self, method, url, **kwargs):
        self.attempts += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.headers: dict = {}
        self._payload = payload if payload is not None else {"ok": True}
        self.content = b"{}"
        self.text = "{}"

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr("src.http.time.sleep", lambda _: None)


def _client(outcomes):
    client = Client()
    client.session = FakeSession(outcomes)
    return client


def test_read_timeout_is_retried_then_succeeds():
    client = _client([requests.ReadTimeout("slow"), FakeResponse(payload={"id": "x"})])

    assert client.get("https://api.test/thing") == {"id": "x"}
    assert client.session.attempts == 2


def test_connection_error_is_retried():
    client = _client([requests.ConnectionError("reset"), FakeResponse()])

    assert client.get("https://api.test/thing") == {"ok": True}


def test_a_timeout_that_never_clears_is_raised():
    client = _client([requests.ReadTimeout("slow")] * MAX_ATTEMPTS)

    with pytest.raises(requests.ReadTimeout):
        client.get("https://api.test/thing")
    assert client.session.attempts == MAX_ATTEMPTS


def test_rate_limit_is_retried_honouring_retry_after():
    limited = FakeResponse(status_code=429)
    limited.headers = {"Retry-After": "7"}
    client = _client([limited, FakeResponse()])

    assert client.get("https://api.test/thing") == {"ok": True}


def test_a_client_error_is_not_retried():
    client = _client([FakeResponse(status_code=400)])

    with pytest.raises(requests.HTTPError):
        client.get("https://api.test/thing")
    assert client.session.attempts == 1
