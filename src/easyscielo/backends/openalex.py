import warnings
from typing import Any, Callable, Iterator, Optional

from easyscielo._optional import require
from easyscielo.config import openalex_api_key, openalex_email, warn_no_contact
from easyscielo.models import Article, Query

DEFAULT_MAX_RECORDS = 1000

SUPPORTED_FILTERS = frozenset(
    {"term", "year_start", "year_end", "languages", "journal_issn"}
)


def warn_unsupported(query: Query, source_name: str) -> None:
    """Emit UserWarning for requested filters that are not supported by the backend."""
    unsupported: list[str] = []
    if query.collections or query.collection:
        unsupported.append("collections")
    if query.categories:
        unsupported.append("categories")
    if query.journals:
        unsupported.append("journals")

    if unsupported:
        filters_str = ", ".join(unsupported)
        warnings.warn(
            f"The following filter(s) are not supported by {source_name} and will be ignored: {filters_str}",
            UserWarning,
            stacklevel=2,
        )


def build_openalex_filters(query: Query) -> dict[str, str]:
    """Build OpenAlex API filter key-value dictionary from Query object."""
    warn_unsupported(query, "OpenAlex")
    filters: dict[str, str] = {}

    if query.year_start is not None:
        filters["from_publication_date"] = f"{query.year_start}-01-01"

    if query.year_end is not None:
        filters["to_publication_date"] = f"{query.year_end}-12-31"

    if query.languages:
        filters["language"] = query.languages[0]

    if query.journal_issn:
        filters["primary_location.source.issn"] = query.journal_issn

    return filters


def invert_abstract(index: Optional[dict[str, list[int]]]) -> Optional[str]:
    """Reconstruct abstract string from OpenAlex abstract_inverted_index.

    Args:
        index: Dictionary mapping word tokens to lists of positional indices.

    Returns:
        Reconstructed abstract text in positional order, or None if index is missing or empty.
    """
    if not index or not isinstance(index, dict):
        return None

    position_word_pairs: list[tuple[int, str]] = []
    for word, positions in index.items():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int):
                    position_word_pairs.append((pos, word))

    if not position_word_pairs:
        return None

    position_word_pairs.sort(key=lambda item: item[0])
    return " ".join(word for _, word in position_word_pairs)


def work_to_record(payload: dict[str, Any]) -> Article:
    """Map an OpenAlex Work JSON object to an Article instance.

    Args:
        payload: JSON dictionary representing an OpenAlex Work item.

    Returns:
        Mapped Article instance.
    """
    if not isinstance(payload, dict):
        payload = {}

    # Title: display_name / title -> title
    title = payload.get("display_name") or payload.get("title") or ""

    # Authors: authorships[].author.display_name -> authors
    authors: list[str] = []
    authorships = payload.get("authorships")
    if isinstance(authorships, list):
        for item in authorships:
            if isinstance(item, dict):
                author = item.get("author")
                if isinstance(author, dict):
                    name = author.get("display_name")
                    if isinstance(name, str) and name:
                        authors.append(name)

    # Publication Year: publication_year -> year (missing -> 0)
    year_raw = payload.get("publication_year")
    if year_raw is not None:
        try:
            year = int(year_raw)
        except (ValueError, TypeError):
            year = 0
    else:
        year = 0

    # DOI: doi without prefix https://doi.org/ (or http://doi.org/), missing -> None
    doi_raw = payload.get("doi")
    doi: Optional[str] = None
    if isinstance(doi_raw, str) and doi_raw.strip():
        doi = doi_raw.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        if not doi:
            doi = None

    # Abstract: via invert_abstract
    abstract = invert_abstract(payload.get("abstract_inverted_index"))

    # Primary Location & Journal Info: primary_location.source.display_name -> journal, .issn_l -> journal_issn
    journal: Optional[str] = None
    journal_issn: Optional[str] = None
    primary_location = payload.get("primary_location")
    if isinstance(primary_location, dict):
        source = primary_location.get("source")
        if isinstance(source, dict):
            journal = source.get("display_name")
            journal_issn = source.get("issn_l")

    # Languages: language -> languages
    languages: list[str] = []
    lang = payload.get("language")
    if isinstance(lang, str) and lang:
        languages = [lang]
    elif isinstance(lang, list):
        languages = [str(x) for x in lang if x]

    # Categories: topics[].display_name (fallback to concepts[].display_name) -> categories
    categories: list[str] = []
    topics = payload.get("topics")
    if isinstance(topics, list):
        for topic in topics:
            if isinstance(topic, dict):
                d_name = topic.get("display_name")
                if isinstance(d_name, str) and d_name:
                    categories.append(d_name)

    if not categories:
        concepts = payload.get("concepts")
        if isinstance(concepts, list):
            for concept in concepts:
                if isinstance(concept, dict):
                    d_name = concept.get("display_name")
                    if isinstance(d_name, str) and d_name:
                        categories.append(d_name)

    # PID: short id (W...) -> pid
    id_raw = payload.get("id")
    pid: Optional[str] = None
    if isinstance(id_raw, str) and id_raw:
        pid = id_raw.split("/")[-1]

    # URL: id / doi -> url
    url: Optional[str] = None
    if isinstance(id_raw, str) and id_raw:
        url = id_raw
    elif isinstance(doi_raw, str) and doi_raw:
        url = doi_raw

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
        source="openalex",
    )


def _pyalex_pager(
    query: Query,
    *,
    email: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Iterator[dict[str, Any]]:
    """Default pager for OpenAlex backend using pyalex library."""
    pyalex = require("pyalex", "openalex")

    email_val = openalex_email(email)
    api_key_val = openalex_api_key(api_key)

    if not email_val:
        warn_no_contact("OpenAlex")

    pyalex.config.email = email_val
    pyalex.config.api_key = api_key_val

    works = pyalex.Works()
    if query.term and query.term.strip():
        works = works.search(query.term.strip())

    filters = build_openalex_filters(query)
    if filters:
        works = works.filter(**filters)

    for page in works.paginate(per_page=200, cursor="*"):
        for item in page:
            yield item


class OpenAlexBackend:
    """Backend for searching OpenAlex API via pyalex."""

    name: str = "openalex"

    def __init__(
        self,
        *,
        pager: Optional[Callable[..., Iterator[dict[str, Any]]]] = None,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.pager = pager
        self.email = email
        self.api_key = api_key

    def search(
        self,
        query: Query,
        *,
        n_max: Optional[int] = None,
        client: Optional[Any] = None,
    ) -> Iterator[Article]:
        """Search OpenAlex for works matching query.

        Args:
            query: Query object containing search filters and term.
            n_max: Optional maximum number of articles to yield.
                If None, capped at DEFAULT_MAX_RECORDS (1000) with a UserWarning.
            client: Ignored parameter accepted for Backend interface compatibility.
                pyalex manages its own HTTP transport.

        Yields:
            Article objects mapped from OpenAlex works.
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

        active_pager = self.pager if self.pager is not None else _pyalex_pager
        try:
            items = active_pager(query, email=self.email, api_key=self.api_key)
        except TypeError:
            items = active_pager(query)

        count = 0
        for item in items:
            if count >= limit:
                break
            yield work_to_record(item)
            count += 1
