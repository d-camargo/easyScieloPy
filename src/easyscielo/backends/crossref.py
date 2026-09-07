"""Crossref API backend parser and search implementation for easyscielo."""

import re
import warnings
from typing import Any, Iterator, Optional

from easyscielo.config import crossref_mailto, warn_no_contact
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query

DEFAULT_MAX_RECORDS = 1000

SUPPORTED_FILTERS = frozenset({"term", "year_start", "year_end", "journal_issn"})


def warn_unsupported(query: Query, source_name: str = "Crossref") -> None:
    """Emit UserWarning for requested filters that are not supported by the backend."""
    unsupported: list[str] = []
    if query.collections or query.collection:
        unsupported.append("collections")
    if query.categories:
        unsupported.append("categories")
    if query.journals:
        unsupported.append("journals")
    if query.languages:
        unsupported.append("languages")

    if unsupported:
        filters_str = ", ".join(unsupported)
        warnings.warn(
            f"The following filter(s) are not supported by {source_name} and will be ignored: {filters_str}",
            UserWarning,
            stacklevel=2,
        )


def build_crossref_params(
    query: Query,
    *,
    cursor: str = "*",
    mailto: Optional[str] = None,
    rows: int = 100,
) -> dict[str, Any]:
    """Build query parameters dictionary for Crossref API endpoint.

    Args:
        query: Query object containing search filters and term.
        cursor: Pagination cursor string (defaults to "*").
        mailto: Optional contact email (defaults to config.crossref_mailto()).
        rows: Number of results per page (defaults to 100).

    Returns:
        Dictionary of URL parameters for Crossref API query.
    """
    warn_unsupported(query, "Crossref")

    params: dict[str, Any] = {
        "rows": rows,
        "cursor": cursor,
    }

    if query.term and query.term.strip():
        params["query.bibliographic"] = query.term.strip()

    filter_parts: list[str] = []
    if query.year_start is not None:
        filter_parts.append(f"from-pub-date:{query.year_start}-01-01")
    if query.year_end is not None:
        filter_parts.append(f"until-pub-date:{query.year_end}-12-31")
    if query.journal_issn:
        filter_parts.append(f"issn:{query.journal_issn}")

    if filter_parts:
        params["filter"] = ",".join(filter_parts)

    contact_email = crossref_mailto(mailto)
    if contact_email:
        params["mailto"] = contact_email
    else:
        warn_no_contact("Crossref")

    return params


def _clean_abstract(abstract: Optional[str]) -> Optional[str]:
    """Remove JATS/HTML tags from abstract text.

    Args:
        abstract: Raw abstract string potentially containing XML/JATS tags.

    Returns:
        Cleaned abstract string or None if empty or missing.
    """
    if not isinstance(abstract, str) or not abstract.strip():
        return None

    cleaned = re.sub(r"<[^>]+>", "", abstract).strip()
    return cleaned if cleaned else None


def item_to_record(item: dict[str, Any]) -> Article:
    """Map a Crossref work item JSON object to an Article instance.

    Args:
        item: JSON dictionary representing a Crossref work item.

    Returns:
        Mapped Article instance.
    """
    if not isinstance(item, dict):
        item = {}

    # Title: title[0] -> title
    titles = item.get("title")
    title = ""
    if isinstance(titles, list) and titles:
        title = str(titles[0])
    elif isinstance(titles, str):
        title = titles

    # Authors: author[] formatted as "Given Family" (fallback to name) -> authors
    authors: list[str] = []
    raw_authors = item.get("author")
    if isinstance(raw_authors, list):
        for auth in raw_authors:
            if isinstance(auth, dict):
                given = (
                    auth.get("given", "").strip()
                    if isinstance(auth.get("given"), str)
                    else ""
                )
                family = (
                    auth.get("family", "").strip()
                    if isinstance(auth.get("family"), str)
                    else ""
                )

                if given or family:
                    parts = [p for p in (given, family) if p]
                    authors.append(" ".join(parts))
                else:
                    name = (
                        auth.get("name", "").strip()
                        if isinstance(auth.get("name"), str)
                        else ""
                    )
                    if name:
                        authors.append(name)

    # Publication Year: issued.date-parts[0][0] -> year (missing -> 0)
    year = 0
    issued = item.get("issued")
    if isinstance(issued, dict):
        date_parts = issued.get("date-parts")
        if isinstance(date_parts, list) and date_parts:
            first_part = date_parts[0]
            if isinstance(first_part, list) and first_part:
                try:
                    year = int(first_part[0])
                except (ValueError, TypeError):
                    year = 0

    # DOI: DOI -> doi
    raw_doi = item.get("DOI")
    doi: Optional[str] = (
        str(raw_doi).strip() if isinstance(raw_doi, str) and raw_doi.strip() else None
    )

    # Abstract: abstract with JATS tags removed -> abstract
    abstract = _clean_abstract(item.get("abstract"))

    # Journal: container-title[0] -> journal
    container_titles = item.get("container-title")
    journal: Optional[str] = None
    if isinstance(container_titles, list) and container_titles:
        journal = str(container_titles[0]) if container_titles[0] else None
    elif isinstance(container_titles, str) and container_titles.strip():
        journal = container_titles.strip()

    # ISSN: ISSN[0] -> journal_issn
    issns = item.get("ISSN")
    journal_issn: Optional[str] = None
    if isinstance(issns, list) and issns:
        journal_issn = str(issns[0]) if issns[0] else None
    elif isinstance(issns, str) and issns.strip():
        journal_issn = issns.strip()

    # Languages: language -> languages
    languages: list[str] = []
    lang = item.get("language")
    if isinstance(lang, str) and lang.strip():
        languages = [lang.strip()]
    elif isinstance(lang, list):
        languages = [str(x).strip() for x in lang if x and str(x).strip()]

    # Categories: subject -> categories
    categories: list[str] = []
    subjects = item.get("subject")
    if isinstance(subjects, list):
        categories = [str(s).strip() for s in subjects if s and str(s).strip()]
    elif isinstance(subjects, str) and subjects.strip():
        categories = [subjects.strip()]

    # PID: DOI -> pid
    pid: Optional[str] = doi

    # URL: URL -> url
    raw_url = item.get("URL")
    url: Optional[str] = (
        str(raw_url).strip() if isinstance(raw_url, str) and raw_url.strip() else None
    )

    return Article(
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        abstract=abstract,
        journal=journal,
        pid=pid,
        url=url,
        languages=languages,
        journal_issn=journal_issn,
        categories=categories,
        source="crossref",
    )


class CrossrefBackend:
    """Backend for searching Crossref API using HttpClient."""

    name: str = "crossref"
    base_url: str = "https://api.crossref.org/works"

    def __init__(self, mailto: Optional[str] = None) -> None:
        self.mailto = mailto

    def search(
        self,
        query: Query,
        *,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        """Search Crossref for works matching query.

        Args:
            query: Query object containing search filters and term.
            n_max: Optional maximum number of articles to yield.
                If None, capped at DEFAULT_MAX_RECORDS (1000) with a UserWarning.
            client: Optional HttpClient instance to reuse.

        Yields:
            Article objects mapped from Crossref work items.
        """
        if n_max is None:
            limit = DEFAULT_MAX_RECORDS
            warnings.warn(
                f"No n_max specified; search capped at default max limit of {DEFAULT_MAX_RECORDS} records.",
                UserWarning,
                stacklevel=2,
            )
        else:
            limit = n_max

        if limit <= 0:
            return

        cursor = "*"
        count = 0
        own_client = client is None
        http_client = client if client is not None else HttpClient()

        try:
            while count < limit:
                params = build_crossref_params(query, cursor=cursor, mailto=self.mailto)
                response = http_client.get(self.base_url, params=params)
                data = response.json()

                if not isinstance(data, dict):
                    break

                message = data.get("message")
                if not isinstance(message, dict):
                    break

                items = message.get("items")
                if not isinstance(items, list) or not items:
                    break

                for item in items:
                    if count >= limit:
                        break
                    yield item_to_record(item)
                    count += 1

                next_cursor = message.get("next-cursor")
                if not next_cursor or next_cursor == cursor:
                    break

                cursor = next_cursor
        finally:
            if own_client:
                http_client.close()
