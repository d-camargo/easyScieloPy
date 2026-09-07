"""Tests for easyscielo models and errors."""

from easyscielo.errors import (
    BackendError,
    BlockedError,
    ParseError,
    ScieloError,
    ValidationError,
)
from easyscielo.models import Article, Query


def test_article_as_dict_order():
    article = Article(
        title="Test Article",
        authors=["Author A", "Author B"],
        year=2023,
        doi="10.1234/test",
        abstract="A test abstract.",
    )

    d = article.as_dict()
    keys = list(d.keys())

    # Check if the keys start with the expected order
    expected_start = ["title", "authors", "year", "doi", "abstract"]
    assert keys[:5] == expected_start

    # Check values
    assert d["title"] == "Test Article"
    assert d["authors"] == ["Author A", "Author B"]
    assert d["year"] == 2023
    assert d["doi"] == "10.1234/test"
    assert d["abstract"] == "A test abstract."


def test_article_as_dict_order_with_missing_optional():
    article = Article(title="Title", authors=[], year=2020)

    d = article.as_dict()
    expected_start = ["title", "authors", "year", "doi", "abstract"]
    assert list(d.keys())[:5] == expected_start
    assert d["doi"] is None
    assert d["abstract"] is None


def test_query_dataclass():
    query = Query(term="machine learning")
    assert query.term == "machine learning"


def test_errors_hierarchy():
    assert issubclass(BlockedError, ScieloError)
    assert issubclass(ParseError, ScieloError)
    assert issubclass(BackendError, ScieloError)
    assert issubclass(ValidationError, ScieloError)
