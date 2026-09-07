from .articlemeta import ArticleMetaBackend, article_to_record
from .base import Backend, BackendError
from .oai import OaiBackend, parse_oai_record
from .search_html import SearchBackend

_VALID_BACKENDS = {"search", "articlemeta", "oai"}


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
    if name not in _VALID_BACKENDS:
        valid = ", ".join(f"{k!r}" for k in sorted(_VALID_BACKENDS))
        raise BackendError(
            f"Unknown backend {name!r}. Valid backend names are: {valid}."
        )

    if name == "search":
        return SearchBackend()
    if name == "articlemeta":
        return ArticleMetaBackend()
    if name == "oai":
        return OaiBackend()

    raise BackendError(f"Backend {name!r} not implemented.")


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
