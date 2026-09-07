"""Multiple source iteration and materialization."""

from typing import Any, Iterator, Optional, Sequence, Union

from easyscielo.api import build_query
from easyscielo.backends import get_backend
from easyscielo.http import HttpClient
from easyscielo.models import Article

SCIELO_SOURCES = ("search", "articlemeta", "oai")
EXTERNAL_SOURCES = ("openalex", "crossref")
ALL_SOURCES = SCIELO_SOURCES + EXTERNAL_SOURCES


def iter_articles(
    query: str,
    *,
    sources: Sequence[str] = ("crossref",),
    lang: str = "en",
    lang_operator: str = "AND",
    n_max: Optional[Union[int, str]] = None,
    journals: Optional[Union[str, Sequence[str]]] = None,
    collections: Optional[Union[str, Sequence[str]]] = None,
    languages: Optional[Union[str, Sequence[str]]] = None,
    categories: Optional[Union[str, Sequence[str]]] = None,
    year_start: Optional[Union[int, str]] = None,
    year_end: Optional[Union[int, str]] = None,
    journal_issn: Optional[str] = None,
    delay: Optional[Union[int, float, tuple[float, float]]] = None,
    cache_dir: Optional[str] = None,
) -> Iterator[Article]:
    """Search multiple sources and return an iterator of Article objects.

    Iterates over sources in order, and propagates n_max per source.
    Default source is ``crossref`` since 2026-09-07: SciELO blocks
    automated requests (Bunny Shield), and Crossref is the textual-search
    source that responds.
    """
    q, norm_n_max = build_query(
        query=query,
        lang=lang,
        lang_operator=lang_operator,
        n_max=n_max,
        journals=journals,
        collections=collections,
        languages=languages,
        categories=categories,
        year_start=year_start,
        year_end=year_end,
        journal_issn=journal_issn,
    )

    client_kwargs: dict[str, Any] = {}
    if delay is not None:
        if isinstance(delay, (int, float)):
            client_kwargs["delay"] = (float(delay), float(delay))
        else:
            client_kwargs["delay"] = delay
    if cache_dir is not None:
        client_kwargs["cache_dir"] = cache_dir

    client = HttpClient(**client_kwargs) if client_kwargs else None

    try:
        for source in sources:
            backend_obj = get_backend(source)
            for article in backend_obj.search(query=q, n_max=norm_n_max, client=client):
                if not article.source:
                    article.source = source
                yield article
    finally:
        if client is not None:
            client.close()


def search_articles(
    query: str,
    *,
    sources: Sequence[str] = ("crossref",),
    lang: str = "en",
    lang_operator: str = "AND",
    n_max: Optional[Union[int, str]] = None,
    journals: Optional[Union[str, Sequence[str]]] = None,
    collections: Optional[Union[str, Sequence[str]]] = None,
    languages: Optional[Union[str, Sequence[str]]] = None,
    categories: Optional[Union[str, Sequence[str]]] = None,
    year_start: Optional[Union[int, str]] = None,
    year_end: Optional[Union[int, str]] = None,
    journal_issn: Optional[str] = None,
    delay: Optional[Union[int, float, tuple[float, float]]] = None,
    cache_dir: Optional[str] = None,
) -> list[Article]:
    """Search multiple sources and return a list of Article objects.

    Wrapper around iter_articles that materializes the results.
    Default source is ``crossref`` since 2026-09-07: SciELO blocks
    automated requests (Bunny Shield), and Crossref is the textual-search
    source that responds.
    """
    return list(
        iter_articles(
            query=query,
            sources=sources,
            lang=lang,
            lang_operator=lang_operator,
            n_max=n_max,
            journals=journals,
            collections=collections,
            languages=languages,
            categories=categories,
            year_start=year_start,
            year_end=year_end,
            journal_issn=journal_issn,
            delay=delay,
            cache_dir=cache_dir,
        )
    )
