from typing import Callable

from .articlemeta import ArticleMetaBackend, article_to_record
from .base import Backend, BackendError
from .crossref import CrossrefBackend
from .oai import OaiBackend, parse_oai_record
from .openalex import OpenAlexBackend
from .search_html import SearchBackend

_BACKENDS: dict[str, Callable[[], Backend]] = {
    "search": SearchBackend,
    "articlemeta": ArticleMetaBackend,
    "oai": OaiBackend,
    "openalex": OpenAlexBackend,
    "crossref": CrossrefBackend,
}


def get_backend(name: str) -> Backend:
    """
    Get a backend instance by name.

    Args:
        name: The name of the backend ("search", "articlemeta", or "oai").

    Returns:
        An instance of the requested backend.

    Raises:
        BackendError: If the requested backend name is unknown.
    """
    if name not in _BACKENDS:
        valid = ", ".join(f"{k!r}" for k in sorted(_BACKENDS))
        raise BackendError(
            f"Unknown backend {name!r}. Valid backend names are: {valid}."
        )

    return _BACKENDS[name]()


__all__ = [
    "ArticleMetaBackend",
    "Backend",
    "BackendError",
    "OaiBackend",
    "SearchBackend",
    "article_to_record",
    "get_backend",
    "parse_oai_record",
]
