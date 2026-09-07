from typing import Iterator, Optional
from unittest.mock import patch

import pytest

from easyscielo.api import search_scielo
from easyscielo.backends import BackendError
from easyscielo.backends.base import Backend
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query
from easyscielo.sources import iter_articles


class MockBackendA(Backend):
    name = "mock_a"

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        limit = n_max if n_max is not None else 5
        for i in range(limit):
            yield Article(title=f"Article A {i}", authors=[], year=2020)


class MockBackendB(Backend):
    name = "mock_b"

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        limit = n_max if n_max is not None else 5
        for i in range(limit):
            yield Article(title=f"Article B {i}", authors=[], year=2021)


def test_iter_articles_multi_source():
    # Monkeypatch the backends dictionary
    from easyscielo.backends import _BACKENDS

    with patch.dict(_BACKENDS, {"mock_a": MockBackendA, "mock_b": MockBackendB}):
        results = list(
            iter_articles("test query", sources=("mock_a", "mock_b"), n_max=2)
        )

        assert len(results) == 4

        # Check order
        assert results[0].title == "Article A 0"
        assert results[1].title == "Article A 1"
        assert results[2].title == "Article B 0"
        assert results[3].title == "Article B 1"

        # Check source propagation
        assert results[0].source == "mock_a"
        assert results[1].source == "mock_a"
        assert results[2].source == "mock_b"
        assert results[3].source == "mock_b"


def test_iter_articles_unknown_source():
    with pytest.raises(BackendError):
        list(iter_articles("test query", sources=("unknown_source",)))


def test_search_scielo_legacy_behavior():
    from easyscielo.backends import _BACKENDS

    with patch.dict(_BACKENDS, {"mock_a": MockBackendA}):
        results = search_scielo("test query", backend="mock_a", n_max=3)
        assert len(results) == 3
        # In legacy mode, source might not be set by iter_articles since it's just iter_scielo
        # But iter_scielo delegates to the backend directly, and Article defaults to ""
        assert results[0].source == ""
        assert results[0].title == "Article A 0"
