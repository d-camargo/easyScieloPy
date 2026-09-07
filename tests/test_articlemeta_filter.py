"""Tests for ArticleMeta local filtering matches() function and Query parameters."""

import warnings

import pytest

from easyscielo.backends.articlemeta import ArticleMetaBackend, matches
from easyscielo.models import Article, Query


def test_query_journal_issn_and_collection():
    """Test exposing journal_issn and collection on Query."""
    q = Query(
        term="parasitosis",
        collection="scl",
        journal_issn="0102-311X",
    )
    assert q.term == "parasitosis"
    assert q.collection == "scl"
    assert q.journal_issn == "0102-311X"


def test_matches_accent_insensitive_and_case_insensitive():
    """Test matches() with accents and case insensitivity in title and abstract."""
    article = Article(
        title="Adiestramiento en el diagnóstico de las parasitosis intestinales",
        authors=["Author A"],
        year=2001,
        abstract="Un proyecto nacional de adiestramiento integral para diagnóstico.",
    )

    # Search term without accent matching title with accent
    q1 = Query(term="diagnostico parasitosis")
    assert matches(article, q1) is True

    # Search term uppercase with accent
    q2 = Query(term="DIAGNÓSTICO PARASITOSIS")
    assert matches(article, q2) is True

    # Search term matching abstract
    q3 = Query(term="proyecto nacional")
    assert matches(article, q3) is True


def test_matches_missing_word():
    """Test matches() returns False when any word in the query term is missing."""
    article = Article(
        title="Adiestramiento en el diagnóstico de las parasitosis intestinales",
        authors=["Author A"],
        year=2001,
        abstract="Un proyecto nacional de adiestramiento.",
    )

    # 'dengue' is missing
    q = Query(term="parasitosis dengue")
    assert matches(article, q) is False


def test_matches_year_filtering():
    """Test matches() year range filtering ('corte por ano')."""
    article = Article(
        title="Sample Article Title",
        authors=["Author A"],
        year=2010,
    )

    # Within year range
    assert matches(article, Query(year_start=2005, year_end=2015)) is True
    assert matches(article, Query(year_start=2010, year_end=2010)) is True

    # Cut off by start year
    assert matches(article, Query(year_start=2011, year_end=2015)) is False

    # Cut off by end year
    assert matches(article, Query(year_start=2000, year_end=2009)) is False


def test_matches_language_filtering():
    """Test matches() language filter."""
    article = Article(
        title="Sample Title",
        authors=["Author A"],
        year=2020,
    )
    article.languages = ["es", "en"]

    assert matches(article, Query(languages=["es"])) is True
    assert matches(article, Query(languages=["pt"])) is False


def test_matches_journal_and_issn_filtering():
    """Test matches() journal name and journal_issn filtering."""
    article = Article(
        title="Sample Title",
        authors=["Author A"],
        year=2020,
    )
    article.journal = "Cad. Saúde Pública"
    article.journal_issn = "0102-311X"

    # Match by ISSN via Query(journal_issn=...)
    assert matches(article, Query(journal_issn="0102-311X")) is True

    # Match by journal name via Query(journals=...)
    assert matches(article, Query(journals=["Cad. Saúde Pública"])) is True

    # Non-matching ISSN
    assert matches(article, Query(journal_issn="9999-9999")) is False

    # Non-matching journal name
    assert matches(article, Query(journals=["Nature"])) is False


def test_matches_category_filtering():
    """Test matches() subject category filtering."""
    article = Article(
        title="Sample Title",
        authors=["Author A"],
        year=2020,
    )
    article.categories = ["SAUDE PUBLICA", "SAUDE COLETIVA"]

    # Match with accents / case variation
    assert matches(article, Query(categories=["Saúde Pública"])) is True

    # Non-matching category
    assert matches(article, Query(categories=["Physics"])) is False


def test_articlemeta_warning_on_text_search_without_collection_or_issn():
    """Test that ArticleMetaBackend issues a warning when text search is performed without collection or journal_issn."""
    import httpx

    from easyscielo.http import HttpClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"meta": {"total": 0, "offset": 0, "limit": 50}, "objects": []}
        )

    client = HttpClient(transport=httpx.MockTransport(handler), delay=(0, 0))
    backend = ArticleMetaBackend(client=client)

    # Warning SHOULD be raised when term is non-empty and no collection or journal_issn
    with pytest.warns(
        UserWarning,
        match="ArticleMeta textual search without 'collection' or 'journal_issn'",
    ):
        list(backend.search(Query(term="parasitosis")))

    # Warning SHOULD NOT be raised when collection is provided
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        list(backend.search(Query(term="parasitosis", collection="scl")))
        assert len(record) == 0

    # Warning SHOULD NOT be raised when journal_issn is provided
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        list(backend.search(Query(term="parasitosis", journal_issn="0102-311X")))
        assert len(record) == 0
