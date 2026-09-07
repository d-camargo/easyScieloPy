"""Tests for OpenAlexBackend implementation, protocol compliance, and seam paging."""

import json
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from easyscielo.backends.base import Backend
from easyscielo.backends.openalex import (
    DEFAULT_MAX_RECORDS,
    OpenAlexBackend,
    _pyalex_pager,
)
from easyscielo.models import Article, Query


def _load_fixture_results() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "openalex_works.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return data["results"]


def test_openalex_backend_is_backend_protocol():
    """Test that isinstance(OpenAlexBackend(), Backend) is True."""
    backend = OpenAlexBackend()
    assert isinstance(backend, Backend)
    assert backend.name == "openalex"


def test_openalex_backend_search_returns_article_and_respects_n_max():
    """Test search yields Article instances and respects n_max=2."""
    fixture_records = _load_fixture_results()
    assert len(fixture_records) == 5

    def fake_pager(query: Query, **kwargs):
        return iter(fixture_records)

    backend = OpenAlexBackend(pager=fake_pager)
    query = Query(term="structural health")

    articles = list(backend.search(query, n_max=2))
    assert len(articles) == 2
    for art in articles:
        assert isinstance(art, Article)
        assert art.source == "openalex"

    assert articles[0].pid == "W2027456229"
    assert "Farrar" in articles[0].authors[0]


def test_openalex_backend_search_default_n_max_warning():
    """Test search without n_max emits UserWarning stating default max records ceiling."""
    fixture_records = _load_fixture_results()

    def fake_pager(query: Query, **kwargs):
        return iter(fixture_records)

    backend = OpenAlexBackend(pager=fake_pager)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        articles = list(backend.search(Query(term="test")))

        assert len(record) == 1
        assert issubclass(record[0].category, UserWarning)
        msg = str(record[0].message)
        assert str(DEFAULT_MAX_RECORDS) in msg

    assert len(articles) == 5


def test_openalex_backend_search_caps_at_default_max_records():
    """Test search without n_max caps yielded results at DEFAULT_MAX_RECORDS (1000)."""
    large_dataset = [
        {"display_name": f"Title {i}", "publication_year": 2020} for i in range(1050)
    ]

    def fake_pager(query: Query, **kwargs):
        return iter(large_dataset)

    backend = OpenAlexBackend(pager=fake_pager)

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        articles = list(backend.search(Query(term="test")))

    assert len(articles) == 1000


def test_openalex_backend_seam_and_client_ignored():
    """Test __init__ stores seam attributes and search accepts/ignores client parameter."""

    def fake_pager(q):
        return iter([])

    backend = OpenAlexBackend(
        pager=fake_pager,
        email="test@example.com",
        api_key="secret-key",
    )

    assert backend.pager is fake_pager
    assert backend.email == "test@example.com"
    assert backend.api_key == "secret-key"

    # Search accepts client without error
    articles = list(backend.search(Query(term="test"), n_max=1, client=object()))
    assert articles == []


def test_pyalex_pager_import_error_when_pyalex_not_installed():
    """Test that default _pyalex_pager raises ImportError if pyalex is not installed."""
    with patch.dict("sys.modules", {"pyalex": None}):
        with pytest.raises(ImportError) as exc_info:
            list(_pyalex_pager(Query(term="test")))
        assert "pyalex is required for this feature" in str(exc_info.value)
