"""Tests for OpenAlex filter translation and warning functionality."""

import pytest

from easyscielo.backends.openalex import (
    SUPPORTED_FILTERS,
    build_openalex_filters,
    warn_unsupported,
)
from easyscielo.models import Query


def test_supported_filters_constant():
    """Test that SUPPORTED_FILTERS contains the expected set of filter names."""
    expected = frozenset(
        {"term", "year_start", "year_end", "languages", "journal_issn"}
    )
    assert SUPPORTED_FILTERS == expected


def test_empty_query_returns_empty_dict():
    """Test that an empty Query returns an empty filter dictionary."""
    q = Query()
    assert build_openalex_filters(q) == {}


def test_filter_year_start_isolated():
    """Test translating year_start isoladamente."""
    q = Query(year_start=2020)
    assert build_openalex_filters(q) == {"from_publication_date": "2020-01-01"}


def test_filter_year_end_isolated():
    """Test translating year_end isoladamente."""
    q = Query(year_end=2022)
    assert build_openalex_filters(q) == {"to_publication_date": "2022-12-31"}


def test_filter_languages_isolated():
    """Test translating languages isoladamente (uses first language)."""
    q = Query(languages=["es", "pt", "en"])
    assert build_openalex_filters(q) == {"language": "es"}


def test_filter_journal_issn_isolated():
    """Test translating journal_issn isoladamente."""
    q = Query(journal_issn="0102-311X")
    assert build_openalex_filters(q) == {"primary_location.source.issn": "0102-311X"}


def test_warn_unsupported_collections():
    """Test that passing collections emits UserWarning mentioning collections."""
    q = Query(collections=["scl"])
    with pytest.warns(UserWarning, match="collections"):
        warn_unsupported(q, "OpenAlex")

    # Also test via build_openalex_filters
    with pytest.warns(UserWarning, match="collections"):
        filters = build_openalex_filters(q)
    assert filters == {}


def test_warn_unsupported_categories_and_journals():
    """Test that passing categories and journals emits UserWarning naming them."""
    q = Query(categories=["Public Health"], journals=["Cad. Saúde Pública"])
    with pytest.warns(UserWarning) as record:
        warn_unsupported(q, "OpenAlex")

    assert len(record) == 1
    msg = str(record[0].message)
    assert "categories" in msg
    assert "journals" in msg


def test_combined_supported_filters():
    """Test combining multiple supported filters in a single Query."""
    q = Query(
        term="parasitosis",
        year_start=2015,
        year_end=2020,
        languages=["pt", "en"],
        journal_issn="0102-311X",
    )
    result = build_openalex_filters(q)
    assert result == {
        "from_publication_date": "2015-01-01",
        "to_publication_date": "2020-12-31",
        "language": "pt",
        "primary_location.source.issn": "0102-311X",
    }
