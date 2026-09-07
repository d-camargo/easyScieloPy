"""Data models for easyscielo."""

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Query:
    """Represents a search query to be sent to SciELO."""

    term: str = ""
    lang: str = "en"
    lang_operator: str = "AND"
    collections: list[str] = field(default_factory=list)
    journals: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    journal_issn: Optional[str] = None
    collection: Optional[str] = None


@dataclass
class Article:
    """Represents a scientific article retrieved from SciELO.

    The full schema is guaranteed by every backend: a field the backend
    cannot fill is ``None`` (or an empty list), never absent.
    """

    title: str
    authors: list[str]
    year: int
    doi: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    collection: Optional[str] = None
    pid: Optional[str] = None
    url: Optional[str] = None
    languages: list[str] = field(default_factory=list)
    journal_issn: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    source: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a dict with a stable column order.

        The first five keys (title, authors, year, doi, abstract) keep
        parity with the data.frame returned by the legacy R package.
        """
        d = asdict(self)
        stable_order = ["title", "authors", "year", "doi", "abstract"]
        return {
            **{key: d[key] for key in stable_order},
            **{key: value for key, value in d.items() if key not in stable_order},
        }
