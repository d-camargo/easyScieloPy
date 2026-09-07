"""Golden tests for SciELO search URL construction."""

from easyscielo.backends.search_html import build_search_url
from easyscielo.models import Query


def test_build_search_url_simple_query():
    """Golden test for simple query without filters."""
    query = Query(term="salud ambiental")
    url = build_search_url(query, from_idx=1, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=1&output=site&format=summary&sort=&fb=&page=1"
        "&q=salud%20ambiental"
    )
    assert url == expected


def test_build_search_url_string_query():
    """Test that a Query with defaults produces the bare search URL."""
    query = Query()
    url = build_search_url(query, from_idx=1, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=1&output=site&format=summary&sort=&fb=&page=1"
        "&q="
    )
    assert url == expected


def test_build_search_url_collection_and_language():
    """Golden test for query with collection and language filters."""
    query = Query(term="salud ambiental", collections=["cri"], languages=["es"])
    url = build_search_url(query, from_idx=1, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=1&output=site&format=summary&sort=&fb=&page=1"
        "&q=salud%20ambiental"
        "&filter%5Bin%5D%5B%5D=cri"
        "&filter%5Bla%5D%5B%5D=es"
    )
    assert url == expected


def test_build_search_url_3_year_interval():
    """Golden test for query with 3-year range filter (e.g. 2018 to 2020)."""
    query = Query(term="salud ambiental", year_start=2018, year_end=2020)
    url = build_search_url(query, from_idx=1, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=1&output=site&format=summary&sort=&fb=&page=1"
        "&q=salud%20ambiental"
        "&filter%5Byear_cluster%5D%5B%5D=2018"
        "&filter%5Byear_cluster%5D%5B%5D=2019"
        "&filter%5Byear_cluster%5D%5B%5D=2020"
    )
    assert url == expected


def test_build_search_url_two_languages():
    """Golden test for query with two languages (boolean operator appears)."""
    query = Query(term="salud ambiental", languages=["es", "pt"], lang_operator="AND")
    url = build_search_url(query, from_idx=1, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=1&output=site&format=summary&sort=&fb=&page=1"
        "&q=salud%20ambiental"
        "&filter%5Bla%5D%5B%5D=es"
        "&filter%5Bla%5D%5B%5D=pt"
        "&filter_boolean_operator%5Bla%5D%5B%5D=AND"
    )
    assert url == expected


def test_build_search_url_pagination():
    """Test pagination index and page calculation."""
    query = Query(term="salud ambiental")
    url = build_search_url(query, from_idx=16, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=16&output=site&format=summary&sort=&fb=&page=2"
        "&q=salud%20ambiental"
    )
    assert url == expected


def test_build_search_url_journal_and_categories():
    """Test journals and subject categories filter encoding."""
    query = Query(
        term="salud ambiental",
        journals=["Revista Ambiente & Agua"],
        categories=["environmental sciences"],
    )
    url = build_search_url(query, from_idx=1, count=15)
    expected = (
        "https://search.scielo.org/"
        "?lang=en&count=15&from=1&output=site&format=summary&sort=&fb=&page=1"
        "&q=salud%20ambiental"
        "&filter%5Bjournal_title%5D%5B%5D=Revista%20Ambiente%20%26%20Agua"
        "&filter%5Bwok_subject_categories%5D%5B%5D=environmental%20sciences"
    )
    assert url == expected
