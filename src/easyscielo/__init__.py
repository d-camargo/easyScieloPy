"""easyscielo package."""

from easyscielo.api import iter_scielo, search_scielo
from easyscielo.errors import (
    BackendError,
    BlockedError,
    ParseError,
    ScieloError,
    ValidationError,
)
from easyscielo.filters import (
    normalize_categories,
    normalize_collections,
    normalize_journals,
    normalize_languages,
    normalize_n_max,
    normalize_nmax,
    normalize_years,
)
from easyscielo.frame import to_csv, to_dataframe
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query

__version__ = "0.1.0"

__all__ = [
    "Article",
    "Query",
    "HttpClient",
    "ScieloError",
    "BlockedError",
    "ParseError",
    "BackendError",
    "ValidationError",
    "iter_scielo",
    "search_scielo",
    "to_csv",
    "to_dataframe",
    "normalize_collections",
    "normalize_languages",
    "normalize_journals",
    "normalize_categories",
    "normalize_years",
    "normalize_n_max",
    "normalize_nmax",
]
