"""OAI-PMH backend for SciELO."""

import re
import xml.etree.ElementTree as ET
from typing import Iterator, Optional

from easyscielo.backends.articlemeta import matches
from easyscielo.errors import BackendError, ParseError
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query

DEFAULT_OAI_ENDPOINT = "https://www.scielo.br/oai/scielo-oai.php"

DOI_REGEX = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*|^)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)",
    re.IGNORECASE,
)


def _extract_doi(identifiers: list[str]) -> Optional[str]:
    """Extract clean DOI string from identifiers list, or None if no DOI present."""
    for item in identifiers:
        item_str = item.strip()
        match = DOI_REGEX.search(item_str)
        if match:
            doi = match.group(1)
            return doi.rstrip(".")
        elif item_str.startswith("10.") and "/" in item_str:
            return item_str.rstrip(".")
    return None


def _extract_year(date_strs: list[str]) -> int:
    """Extract publication year from date strings."""
    for ds in date_strs:
        match = re.search(r"\b(18|19|20)\d{2}\b", ds)
        if match:
            return int(match.group(0))
    return 0


def parse_oai_record(record: ET.Element) -> Optional[Article]:
    """Parse an XML OAI record element into an Article instance.

    Parses oai_dc fields: dc:title, dc:creator*, dc:date, dc:identifier,
    dc:description, dc:language. Sets DOI only when dc:identifier is a DOI.
    """
    metadata = record.find("{http://www.openarchives.org/OAI/2.0/}metadata")
    if metadata is None:
        metadata = record.find("metadata")

    dc_elem = None
    if metadata is not None:
        for child in metadata:
            if child.tag.endswith("dc"):
                dc_elem = child
                break

    if dc_elem is None:
        dc_elem = metadata if metadata is not None else record

    titles: list[str] = []
    creators: list[str] = []
    dates: list[str] = []
    identifiers: list[str] = []
    descriptions: list[str] = []
    languages: list[str] = []

    for elem in dc_elem.iter():
        tag = elem.tag.split("}")[-1]
        text = elem.text.strip() if elem.text else ""
        if not text:
            continue
        if tag == "title":
            titles.append(text)
        elif tag == "creator":
            creators.append(text)
        elif tag == "date":
            dates.append(text)
        elif tag == "identifier":
            identifiers.append(text)
        elif tag == "description":
            descriptions.append(text)
        elif tag == "language":
            languages.append(text)

    if not titles and not creators and not identifiers:
        return None

    title = titles[0] if titles else ""
    authors = creators
    year = _extract_year(dates)
    doi = _extract_doi(identifiers)
    abstract = descriptions[0] if descriptions else None
    url = next(
        (item for item in identifiers if item.startswith(("http://", "https://"))),
        None,
    )

    pid: Optional[str] = None
    journal_issn: Optional[str] = None

    header = record.find("{http://www.openarchives.org/OAI/2.0/}header")
    if header is None:
        header = record.find("header")

    if header is not None:
        header_id = header.findtext(
            "{http://www.openarchives.org/OAI/2.0/}identifier"
        ) or header.findtext("identifier")
        if header_id:
            if "oai:scielo:" in header_id:
                pid = header_id.split("oai:scielo:")[-1]
            else:
                pid = header_id

        setspec = header.findtext(
            "{http://www.openarchives.org/OAI/2.0/}setSpec"
        ) or header.findtext("setSpec")
        if setspec:
            journal_issn = setspec

    return Article(
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        abstract=abstract,
        pid=pid,
        url=url,
        languages=languages,
        journal_issn=journal_issn,
        source="oai",
    )


class OaiBackend:
    """OAI-PMH backend for SciELO."""

    name: str = "oai"

    def __init__(
        self,
        endpoint: str = DEFAULT_OAI_ENDPOINT,
        client: Optional[HttpClient] = None,
    ) -> None:
        self.endpoint = endpoint
        self.client = client

    def search(
        self,
        query: Optional[Query] = None,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
        from_date: Optional[str] = None,
        until: Optional[str] = None,
        set_spec: Optional[str] = None,
        metadata_prefix: str = "oai_dc",
    ) -> Iterator[Article]:
        """Fetch articles via OAI-PMH ListRecords verb.

        Args:
            query: Query object (year range and journal/ISSN map to
                from/until/set OAI parameters).
            n_max: Maximum number of articles to yield.
            client: Optional HttpClient instance override.
            from_date: Optional start date for OAI filtering (YYYY-MM-DD or YYYY).
            until: Optional end date for OAI filtering (YYYY-MM-DD or YYYY).
            set_spec: Optional set identifier for OAI filtering.
            metadata_prefix: OAI metadata format (default "oai_dc").

        Yields:
            Article objects.
        """
        http = client or self.client
        own_client = False
        if http is None:
            http = HttpClient()
            own_client = True

        try:
            yield from self._search_impl(
                query=query if query is not None else Query(),
                n_max=n_max,
                http=http,
                from_date=from_date,
                until=until,
                set_spec=set_spec,
                metadata_prefix=metadata_prefix,
            )
        finally:
            if own_client:
                http.close()

    def _search_impl(
        self,
        query: Query,
        n_max: Optional[int],
        http: HttpClient,
        from_date: Optional[str],
        until: Optional[str],
        set_spec: Optional[str],
        metadata_prefix: str,
    ) -> Iterator[Article]:
        f_val = from_date
        u_val = until
        s_val = set_spec

        if not f_val and query.year_start:
            f_val = f"{query.year_start}-01-01"
        if not u_val and query.year_end:
            u_val = f"{query.year_end}-12-31"
        if not s_val:
            if query.journals:
                s_val = query.journals[0]
            elif query.journal_issn:
                s_val = query.journal_issn

        target_n_max: Optional[int] = n_max

        resumption_token: Optional[str] = None
        total_fetched = 0

        while True:
            if target_n_max is not None and total_fetched >= target_n_max:
                break

            params: dict[str, str] = {"verb": "ListRecords"}
            if resumption_token:
                params["resumptionToken"] = resumption_token
            else:
                params["metadataPrefix"] = metadata_prefix
                if f_val:
                    params["from"] = str(f_val)
                if u_val:
                    params["until"] = str(u_val)
                if s_val:
                    params["set"] = str(s_val)

            response = http.get(self.endpoint, params=params)
            if response.status_code != 200:
                raise BackendError(
                    f"OAI-PMH endpoint {self.endpoint} returned HTTP "
                    f"{response.status_code}."
                )
            xml_text = response.text

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as exc:
                raise ParseError(
                    f"OAI-PMH endpoint {self.endpoint} did not return valid XML: "
                    f"{exc}"
                ) from exc

            error_elem = root.find(".//{http://www.openarchives.org/OAI/2.0/}error")
            if error_elem is None:
                error_elem = root.find(".//error")
            if error_elem is not None:
                break

            records = root.findall(".//{http://www.openarchives.org/OAI/2.0/}record")
            if not records:
                records = root.findall(".//record")

            if not records:
                break

            for record in records:
                header = record.find("{http://www.openarchives.org/OAI/2.0/}header")
                if header is None:
                    header = record.find("header")
                if header is not None and header.get("status") == "deleted":
                    continue

                article = parse_oai_record(record)
                if article is None:
                    continue

                if not matches(article, query):
                    continue

                yield article

                total_fetched += 1
                if target_n_max is not None and total_fetched >= target_n_max:
                    return

            token_elem = root.find(
                ".//{http://www.openarchives.org/OAI/2.0/}resumptionToken"
            )
            if token_elem is None:
                token_elem = root.find(".//resumptionToken")

            if token_elem is not None and token_elem.text and token_elem.text.strip():
                resumption_token = token_elem.text.strip()
            else:
                break
