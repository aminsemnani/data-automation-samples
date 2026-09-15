import pytest

from api_sync import ApiError, PaginatedApiClient


class FakeResponse:
    def __init__(self, status_code, payload=None, json_error=None):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        return self.responses.pop(0)


def test_client_does_not_retry_permanent_http_error():
    session = FakeSession([FakeResponse(404, {"error": "not found"})])
    client = PaginatedApiClient(session=session, max_retries=3, backoff_seconds=0)

    with pytest.raises(ApiError, match="HTTP 404"):
        client._get_json("https://example.test/missing")

    assert session.calls == 1


def test_client_does_not_retry_malformed_json():
    session = FakeSession([FakeResponse(200, json_error=ValueError("bad json"))])
    client = PaginatedApiClient(session=session, max_retries=3, backoff_seconds=0)

    with pytest.raises(ApiError, match="Invalid JSON response"):
        client._get_json("https://example.test/bad-json")

    assert session.calls == 1
