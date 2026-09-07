from typing import Any, Iterator, Optional, Sequence, Union

from easyscielo.backends import get_backend
from easyscielo.errors import ValidationError
from easyscielo.filters import (
    normalize_categories,
    normalize_collections,
    normalize_journals,
    normalize_languages,
    normalize_nmax,
    normalize_years,
)
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query


def iter_scielo(
    query: str,
    *,
    backend: str = "search",
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
    """Search SciELO and return an iterator of Article objects.

    Validates arguments, builds a Query, resolves the backend, and yields results.
    """
    if not isinstance(query, str) or len(query.strip()) < 2:
        raise ValidationError(
            "The 'query' parameter must be a non-empty character string."
        )

    if lang not in ("en", "es", "pt"):
        raise ValidationError("The 'lang' parameter must be one of: 'en', 'es', 'pt'.")

    if lang_operator not in ("AND", "OR"):
        raise ValidationError(
            "The 'lang_operator' parameter must be either 'AND' or 'OR'."
        )

    norm_n_max = normalize_nmax(n_max)
    y_start, y_end = normalize_years(year_start, year_end)

    q = Query(
        term=query,
        lang=lang,
        lang_operator=lang_operator,
        collections=normalize_collections(collections)
        if collections is not None
        else [],
        journals=normalize_journals(journals) if journals is not None else [],
        languages=normalize_languages(languages) if languages is not None else [],
        categories=normalize_categories(categories) if categories is not None else [],
        year_start=y_start,
        year_end=y_end,
        journal_issn=journal_issn,
    )

    backend_obj = get_backend(backend)

    client_kwargs: dict[str, Any] = {}
    if delay is not None:
        if isinstance(delay, (int, float)):
            client_kwargs["delay"] = (float(delay), float(delay))
        else:
            client_kwargs["delay"] = delay
    if cache_dir is not None:
        client_kwargs["cache_dir"] = cache_dir

    client = HttpClient(**client_kwargs) if client_kwargs else None

    # Delegate to the backend. We check if it accepts n_max and client.
    # We know the builtin backends do.
    try:
        yield from backend_obj.search(query=q, n_max=norm_n_max, client=client)
    finally:
        if client is not None:
            client.close()


def search_scielo(
    query: str,
    *,
    backend: str = "search",
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
    """Search SciELO and return a list of Article objects.

    Wrapper around iter_scielo that materializes the results.
    """
    return list(
        iter_scielo(
            query=query,
            backend=backend,
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
