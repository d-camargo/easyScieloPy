"""Regression tests: errors from SciELO sources must propagate, never
silently degrade into an empty result with exit 0.

Measured on 2026-09-07: `search.scielo.org` and the OAI-PMH endpoint at
`www.scielo.br/oai/scielo-oai.php` are behind the Bunny Shield (HTTP 403 with
a JS challenge page). Before this fix, the three SciELO backends caught
every exception around their HTTP calls and turned it into "no more
results", so a blocked/broken source looked identical to a legitimate empty
search. These tests pin the fixed behavior: `BlockedError`, `BackendError`
and `ParseError` must propagate out of `search()`.
"""

from pathlib import Path

import httpx
import pytest

from easyscielo.backends.articlemeta import ArticleMetaBackend
from easyscielo.backends.oai import OaiBackend
from easyscielo.backends.search_html import SearchBackend
from easyscielo.errors import BackendError, BlockedError, ParseError
from easyscielo.http import HttpClient
from easyscielo.models import Query

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BUNNY_SHIELD_HTML = (FIXTURE_DIR / "bunny_shield_403.html").read_text(
    encoding="utf-8"
)


# --------------------------------------------------------------------------
# search_html backend
# --------------------------------------------------------------------------


def test_search_blocked_error_propagates():
    """A 403 from search.scielo.org must raise BlockedError, not return []."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text=BUNNY_SHIELD_HTML)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = SearchBackend(client=client)

    with pytest.raises(BlockedError):
        list(backend.search(Query(term="dengue")))


# --------------------------------------------------------------------------
# oai backend
# --------------------------------------------------------------------------


def test_oai_404_raises_backend_error():
    """A non-200 response (e.g. moved/removed endpoint) must raise
    BackendError, not be treated as 'no more records'."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = OaiBackend(client=client)

    with pytest.raises(BackendError, match="404"):
        list(backend.search())


def test_oai_html_challenge_body_raises_parse_error():
    """A 200 response whose body is not valid XML (the shield's HTML
    challenge page) must raise ParseError, not be treated as 'no more
    records'."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=BUNNY_SHIELD_HTML)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = OaiBackend(client=client)

    with pytest.raises(ParseError):
        list(backend.search())


# --------------------------------------------------------------------------
# articlemeta backend
# --------------------------------------------------------------------------


def test_articlemeta_blocked_on_identifiers_page_propagates():
    """A 403 on the identifiers page (the spine of the harvest) must
    propagate, not end the collection in silence."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text=BUNNY_SHIELD_HTML)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = ArticleMetaBackend(client=client)

    with pytest.raises(BlockedError):
        list(backend.search(Query(term="", collections=["scl"])))


def test_articlemeta_blocked_on_individual_article_propagates():
    """A 403 fetching a single article must still propagate: a blockage
    is not a per-article problem."""

    ids_page = {
        "meta": {"total": 1, "offset": 0, "limit": 50},
        "objects": [{"code": "P001", "collection": "scl"}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/article/identifiers/" in url_str:
            return httpx.Response(200, json=ids_page)
        if "/article/?" in url_str:
            return httpx.Response(403, text=BUNNY_SHIELD_HTML)
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = ArticleMetaBackend(client=client)

    with pytest.raises(BlockedError):
        list(backend.search(Query(term="", collections=["scl"])))


def test_articlemeta_bad_json_on_individual_article_is_skipped_with_warning():
    """A malformed individual article (e.g. invalid JSON) must not abort a
    harvest of thousands: it is skipped, and a single UserWarning reports
    the total count of skipped articles."""

    ids_page = {
        "meta": {"total": 3, "offset": 0, "limit": 50},
        "objects": [
            {"code": "P001", "collection": "scl"},
            {"code": "P002", "collection": "scl"},
            {"code": "P003", "collection": "scl"},
        ],
    }

    good_payload = {
        "code": "P002",
        "collection": "scl",
        "publication_year": 2020,
        "article": {"v12": [{"_": "Good Article"}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/article/identifiers/" in url_str:
            return httpx.Response(200, json=ids_page)
        if "code=P001" in url_str or "code=P003" in url_str:
            # Malformed body: not valid JSON.
            return httpx.Response(200, text="not-json{")
        if "code=P002" in url_str:
            return httpx.Response(200, json=good_payload)
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = ArticleMetaBackend(client=client)

    with pytest.warns(
        UserWarning, match="2 artigos não puderam ser lidos e foram pulados"
    ):
        articles = list(backend.search(Query(term="", collections=["scl"])))

    assert len(articles) == 1
    assert articles[0].title == "Good Article"


# --------------------------------------------------------------------------
# explicit regression: 403 never becomes an empty list again
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "make_backend",
    [
        lambda client: SearchBackend(client=client),
        lambda client: OaiBackend(client=client),
        lambda client: ArticleMetaBackend(client=client),
    ],
    ids=["search", "oai", "articlemeta"],
)
def test_403_nao_vira_lista_vazia(make_backend):
    """A blocked source (HTTP 403, Bunny Shield) must never look like a
    search that simply found nothing: it must raise BlockedError, never
    return []."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text=BUNNY_SHIELD_HTML)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = make_backend(client)

    with pytest.raises(BlockedError):
        result = list(backend.search(Query(term="dengue", collections=["scl"])))
        assert result != []  # pragma: no cover - should never be reached
