"""Tests for CrossrefBackend implementation, protocol compliance, filter parameters, and MockTransport paging."""

import json
import warnings
from pathlib import Path

import httpx
import pytest

from easyscielo.backends.base import Backend
from easyscielo.backends.crossref import (
    DEFAULT_MAX_RECORDS,
    SUPPORTED_FILTERS,
    CrossrefBackend,
    build_crossref_params,
    warn_unsupported,
)
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query


def _load_fixture_data() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "crossref_works.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_crossref_backend_is_backend_protocol():
    """Test that CrossrefBackend satisfies the Backend protocol."""
    backend = CrossrefBackend()
    assert isinstance(backend, Backend)
    assert backend.name == "crossref"
    assert backend.base_url == "https://api.crossref.org/works"


def test_supported_filters_constant():
    """Test that SUPPORTED_FILTERS contains the expected set of filter names."""
    expected = frozenset({"term", "year_start", "year_end", "journal_issn"})
    assert SUPPORTED_FILTERS == expected


def test_build_crossref_params_default(monkeypatch):
    """Test build_crossref_params with default empty Query and missing contact email."""
    monkeypatch.delenv("CROSSREF_MAILTO", raising=False)
    q = Query()
    with pytest.warns(UserWarning, match="Sem e-mail para Crossref"):
        params = build_crossref_params(q)

    assert params == {"rows": 100, "cursor": "*"}


def test_build_crossref_params_full(monkeypatch):
    """Test build_crossref_params with term, year range, ISSN, custom cursor, rows, and mailto."""
    monkeypatch.setenv("CROSSREF_MAILTO", "env@example.com")
    q = Query(
        term="bridge health",
        year_start=2020,
        year_end=2023,
        journal_issn="0888-3270",
    )
    params = build_crossref_params(
        q, cursor="cursor_token_123", mailto="explicit@example.com", rows=50
    )

    assert params["query.bibliographic"] == "bridge health"
    assert (
        params["filter"]
        == "from-pub-date:2020-01-01,until-pub-date:2023-12-31,issn:0888-3270"
    )
    assert params["cursor"] == "cursor_token_123"
    assert params["rows"] == 50
    assert params["mailto"] == "explicit@example.com"


def test_warn_unsupported_filters():
    """Test warn_unsupported emits UserWarning listing unsupported filters."""
    q = Query(
        collections=["scl"],
        categories=["Engineering"],
        journals=["Revista A"],
        languages=["en"],
    )
    with pytest.warns(UserWarning) as record:
        warn_unsupported(q, "Crossref")

    assert len(record) == 1
    msg = str(record[0].message)
    assert "collections" in msg
    assert "categories" in msg
    assert "journals" in msg
    assert "languages" in msg


def test_crossref_backend_paging_and_cursor(monkeypatch):
    """Test search with MockTransport over 2 pages (page 2 empty), checking cursor chaining."""
    monkeypatch.setenv("CROSSREF_MAILTO", "researcher@example.com")
    page1_data = _load_fixture_data()
    page2_data = {
        "status": "ok",
        "message-type": "work-list",
        "message": {
            "total-results": 5,
            "items": [],
            "next-cursor": "IlNlY29uZFBhZ2VDdXJzb3Ii",
        },
    }

    requests_received: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        requests_received.append(request)
        cursor_val = request.url.params.get("cursor")

        if cursor_val == "*":
            return httpx.Response(200, json=page1_data)
        elif cursor_val == "IlNlY29uZFBhZ2VDdXJzb3Ii":
            return httpx.Response(200, json=page2_data)

        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(mock_handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = CrossrefBackend()

    q = Query(term="structural health", year_start=2020, journal_issn="0888-3270")
    articles = list(backend.search(q, n_max=10, client=client))

    # Should have requested 2 pages
    assert len(requests_received) == 2

    # Request 1 parameter verification
    req1_params = requests_received[0].url.params
    assert req1_params.get("query.bibliographic") == "structural health"
    assert req1_params.get("filter") == "from-pub-date:2020-01-01,issn:0888-3270"
    assert req1_params.get("rows") == "100"
    assert req1_params.get("cursor") == "*"
    assert req1_params.get("mailto") == "researcher@example.com"

    # Request 2 parameter verification (used next-cursor from Page 1)
    req2_params = requests_received[1].url.params
    assert req2_params.get("cursor") == "IlNlY29uZFBhZ2VDdXJzb3Ii"

    # Yielded articles verification
    assert len(articles) == 5
    for art in articles:
        assert isinstance(art, Article)
        assert art.source == "crossref"

    assert articles[0].title == "Structural health monitoring of bridges"
    assert articles[0].doi == "10.1016/j.ymssp.2023.100000"


def test_crossref_backend_search_respects_n_max(monkeypatch):
    """Test search with n_max=2 stops yielding after 2 items without fetching page 2."""
    monkeypatch.setenv("CROSSREF_MAILTO", "user@example.com")
    page1_data = _load_fixture_data()

    requests_received: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        requests_received.append(request)
        return httpx.Response(200, json=page1_data)

    transport = httpx.MockTransport(mock_handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = CrossrefBackend()

    q = Query(term="structural health")
    articles = list(backend.search(q, n_max=2, client=client))

    assert len(articles) == 2
    assert len(requests_received) == 1


def test_crossref_backend_search_default_n_max_warning(monkeypatch):
    """Test search without n_max emits UserWarning stating DEFAULT_MAX_RECORDS limit."""
    monkeypatch.setenv("CROSSREF_MAILTO", "user@example.com")
    page1_data = _load_fixture_data()
    page2_data = {"status": "ok", "message": {"items": []}}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        cursor_val = request.url.params.get("cursor")
        if cursor_val == "*":
            return httpx.Response(200, json=page1_data)
        return httpx.Response(200, json=page2_data)

    transport = httpx.MockTransport(mock_handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = CrossrefBackend()

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        articles = list(backend.search(Query(term="test"), client=client))

        assert len(record) >= 1
        warning_messages = [
            str(r.message) for r in record if issubclass(r.category, UserWarning)
        ]
        assert any(str(DEFAULT_MAX_RECORDS) in msg for msg in warning_messages)

    assert len(articles) == 5
