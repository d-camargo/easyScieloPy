"""Tests for easyscielo.http module."""

from pathlib import Path

import httpx
import pytest

from easyscielo.errors import BackendError, BlockedError
from easyscielo.http import USER_AGENTS, HttpClient


def test_retry_on_503():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, text="Success")

    transport = httpx.MockTransport(handler)
    client = HttpClient(delay=(0, 0), max_retries=3, transport=transport)

    response = client.get("https://example.com/test-retry")
    assert response.status_code == 200
    assert response.text == "Success"
    assert attempts == 3


def test_retry_exceeded_raises_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler)
    client = HttpClient(delay=(0, 0), max_retries=3, transport=transport)

    with pytest.raises(BackendError, match="HTTP error 503"):
        client.get("https://example.com/test-retry-exceeded")


def test_blocked_error_on_403():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    transport = httpx.MockTransport(handler)
    client = HttpClient(delay=(0, 0), transport=transport)

    with pytest.raises(
        BlockedError,
        match="Access denied with HTTP 403. SciELO may be blocking automated requests.",
    ):
        client.get("https://example.com/test-403")


def test_cache_second_call_does_not_hit_transport(tmp_path: Path):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, text=f"Data call {call_count}")

    transport = httpx.MockTransport(handler)
    client = HttpClient(delay=(0, 0), cache_dir=tmp_path, transport=transport)

    url = "https://example.com/test-cache"

    res1 = client.get(url)
    assert res1.status_code == 200
    assert res1.text == "Data call 1"
    assert call_count == 1

    res2 = client.get(url)
    assert res2.status_code == 200
    assert res2.text == "Data call 1"  # Cached content
    assert call_count == 1  # Did NOT hit transport second time


def test_headers_and_user_agent_rotation():
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, text="OK")

    transport = httpx.MockTransport(handler)
    client = HttpClient(delay=(0, 0), transport=transport)

    client.get("https://example.com/headers-test")

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers["accept-language"] == "en-US,en;q=0.9"
    expected_accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    assert req.headers["accept"] == expected_accept
    assert req.headers["user-agent"] in USER_AGENTS


def test_context_manager():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="OK")

    transport = httpx.MockTransport(handler)
    with HttpClient(delay=(0, 0), transport=transport) as client:
        res = client.get("https://example.com/cm")
        assert res.status_code == 200
