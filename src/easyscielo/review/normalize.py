"""String and metadata normalization functions for systematic reviews."""

import re
from typing import Optional

from easyscielo.filters import _remove_accents
from easyscielo.models import Article

__all__ = [
    "normalize_doi",
    "normalize_title",
    "normalize_author",
    "blocking_key",
]


def normalize_doi(doi: Optional[str]) -> str:
    """Normalize a DOI string.

    Removes 'https://doi.org/', 'http://doi.org/', 'doi:', spaces,
    and converts to lowercase.
    """
    if not doi:
        return ""
    s = _remove_accents(doi).lower()
    s = re.sub(r"\s+", "", s)
    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    )
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if s.startswith(prefix):
                s = s[len(prefix) :]
                changed = True
    return s


def normalize_title(title: Optional[str]) -> str:
    """Normalize an article title.

    Folds accents using filters._remove_accents, converts to lowercase,
    removes punctuation, and collapses whitespace.
    """
    if not title:
        return ""
    s = _remove_accents(title).lower()
    s = re.sub(r"[^\w\s]|_", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_author(author: Optional[str]) -> str:
    """Normalize an author name ('Sobrenome, N' -> 'sobrenome n')."""
    if not author:
        return ""
    if "," in author:
        parts = author.split(",", 1)
        last = normalize_title(parts[0])
        first = normalize_title(parts[1])
        if last and first:
            return f"{last} {first}"
        return last or first
    return normalize_title(author)


def blocking_key(article: Optional[Article]) -> str:
    """Generate a blocking key for an Article (year + first 4 letters of normalized title)."""
    if article is None:
        return ""
    year_str = str(article.year) if article.year is not None else ""
    norm_title = normalize_title(article.title)
    return f"{year_str}{norm_title[:4]}"
