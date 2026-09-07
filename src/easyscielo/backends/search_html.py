"""HTML Search backend for SciELO."""

import math
import re
import urllib.parse
import warnings
from typing import Iterator, Optional

from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from easyscielo.http import HttpClient
from easyscielo.models import Article, Query


def build_filter(param: str, values: list[str]) -> str:
    """Build URL query string fragment for array filter parameters."""
    if not values:
        return ""
    return "".join(
        f"&filter%5B{param}%5D%5B%5D={urllib.parse.quote(v)}" for v in values
    )


def build_operator(param: str, op: str, values_count: int) -> str:
    """Build URL query string fragment for filter boolean operator."""
    if values_count > 1 or (values_count == 1 and op != "AND"):
        return f"&filter_boolean_operator%5B{param}%5D%5B%5D={op}"
    return ""


def build_year_filter(start_year: Optional[int], end_year: Optional[int]) -> str:
    """Build URL query string fragment for year cluster filter parameters."""
    if start_year is None or end_year is None:
        return ""
    try:
        start_int = int(start_year)
        end_int = int(end_year)
    except (ValueError, TypeError):
        return ""

    if start_int > end_int:
        return ""

    years = range(start_int, end_int + 1)
    return "".join(f"&filter%5Byear_cluster%5D%5B%5D={y}" for y in years)


def build_search_url(query: Query, from_idx: int, count: int) -> str:
    """Build SciELO search URL based on query object and pagination parameters.

    Args:
        query: Query object containing search filters.
        from_idx: The 'from' index for pagination (1-indexed).
        count: The number of items per page.

    Returns:
        Full SciELO search URL string.
    """
    base_url = "https://search.scielo.org/"

    encoded_query = urllib.parse.quote(query.term)
    page = math.ceil(from_idx / count)

    filters = (
        build_filter("in", query.collections)
        + build_filter("journal_title", query.journals)
        + build_filter("la", query.languages)
        + build_operator("la", query.lang_operator, len(query.languages))
        + build_filter("wok_subject_categories", query.categories)
        + build_year_filter(query.year_start, query.year_end)
    )

    return (
        f"{base_url}"
        f"?lang={query.lang}"
        f"&count={count}"
        f"&from={from_idx}"
        f"&output=site&format=summary&sort=&fb=&page={page}"
        f"&q={encoded_query}"
        f"{filters}"
    )


def parse_search_page(html: str, lang: str = "en") -> list[Article]:
    """Parse a SciELO search results HTML page into a list of Article objects.

    Args:
        html: Raw HTML content of search results page.
        lang: Language code for abstract retrieval preference (fallback).

    Returns:
        List of Article objects parsed from the page.
    """
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(".item")
    articles: list[Article] = []

    for item in items:
        # Title in .title
        title_node = item.select_one(".title")
        title = title_node.get_text(strip=True) if title_node else ""

        # Article URL in the .title link (href), when present
        url = None
        if title_node is not None:
            raw_href = title_node.get("href")
            if raw_href and isinstance(raw_href, str):
                url = raw_href.strip()
            else:
                link = title_node.find("a", href=True)
                if link is not None:
                    raw_link_href = link.get("href")
                    if raw_link_href and isinstance(raw_link_href, str):
                        url = raw_link_href.strip()

        # All authors in .authors a.author
        author_nodes = item.select(".authors a.author")
        if author_nodes:
            authors = [
                a.get_text(strip=True) for a in author_nodes if a.get_text(strip=True)
            ]
        else:
            authors_node = item.select_one(".authors")
            if authors_node:
                text = authors_node.get_text(strip=True)
                authors = [text] if text else []
            else:
                authors = []

        # DOI in href of .DOIResults a
        doi = None
        doi_node = item.select_one(".DOIResults a")
        if doi_node and doi_node.has_attr("href"):
            raw_doi_href = doi_node.get("href")
            if raw_doi_href and isinstance(raw_doi_href, str):
                doi = raw_doi_href.strip()

        # Year by regex \b\d{4}\b in span of .source; journal is the
        # first span of .source
        source_node = item.select_one(".source")
        year = 0
        journal = None
        if source_node:
            spans = source_node.select("span")
            if spans:
                journal = spans[0].get_text(strip=True) or None
            source_text = " ".join(s.get_text(strip=True) for s in spans)
            match = re.search(r"\b\d{4}\b", source_text)
            if match:
                year = int(match.group(0))

        # pid in attribute 'id' of item, abstract in div#<id>_en
        # with fallback to div#<id>_<lang>
        raw_item_id = item.get("id")
        item_id = raw_item_id if isinstance(raw_item_id, str) else None
        abstract = None
        if item_id:
            abstract_node = soup.select_one(f"div#{item_id}_en")
            if not abstract_node and lang != "en":
                abstract_node = soup.select_one(f"div#{item_id}_{lang}")
            if abstract_node:
                abstract = abstract_node.get_text(strip=True)

        articles.append(
            Article(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract=abstract,
                journal=journal,
                pid=item_id,
                url=url,
                source="search",
            )
        )

    return articles


def parse_total_hits(html: str) -> Optional[int]:
    """Parse total number of search results hits from #TotalHits in HTML.

    Args:
        html: Raw HTML content of search results page.

    Returns:
        Total hits count as int, or None if not found.
    """
    soup = BeautifulSoup(html, "lxml")
    hit_node = soup.select_one("#TotalHits")
    if not hit_node:
        return None

    val = hit_node.get("value") or hit_node.get_text(strip=True)
    if not val:
        return None

    digits = "".join(c for c in val if c.isdigit())
    if digits:
        return int(digits)
    return None


class SearchBackend:
    """Backend for searching SciELO HTML web interface."""

    name: str = "search"

    def __init__(self, client: Optional[HttpClient] = None) -> None:
        self.client = client

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        """Search SciELO and yield Articles up to n_max.

        Args:
            query: Query object.
            n_max: Maximum number of articles to yield. If None, discovers total hits
                   from `#TotalHits` on the first page, fallback to 100 with warning.
            client: Optional HttpClient instance override.

        Yields:
            Article objects.
        """
        http = client or self.client
        own_client = False
        if http is None:
            http = HttpClient()
            own_client = True

        try:
            yield from self._search_impl(query=query, n_max=n_max, http=http)
        finally:
            if own_client:
                http.close()

    def _search_impl(
        self,
        query: Query,
        n_max: Optional[int],
        http: HttpClient,
    ) -> Iterator[Article]:
        items_per_page = 15
        from_idx = 1
        total_fetched = 0
        effective_n_max: Optional[int] = n_max

        while True:
            if effective_n_max is not None and total_fetched >= effective_n_max:
                break

            url = build_search_url(query, from_idx=from_idx, count=items_per_page)
            try:
                response = http.get(url)
                html = response.text
            except Exception:
                break

            if effective_n_max is None:
                hits = parse_total_hits(html)
                if hits is not None:
                    effective_n_max = hits
                else:
                    warnings.warn(
                        "Could not determine total hits. Defaulting to 100.",
                        UserWarning,
                        stacklevel=2,
                    )
                    effective_n_max = 100

            if effective_n_max <= 0:
                break

            articles = parse_search_page(html, lang=query.lang)

            if not articles:
                # Retry once on empty page before giving up
                try:
                    retry_response = http.get(url)
                    retry_html = retry_response.text
                    articles = parse_search_page(retry_html, lang=query.lang)
                except Exception:
                    articles = []

            if not articles:
                break

            for article in articles:
                yield article
                total_fetched += 1
                if total_fetched >= effective_n_max:
                    return

            from_idx += items_per_page
