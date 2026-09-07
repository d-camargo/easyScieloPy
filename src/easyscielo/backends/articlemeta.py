"""ArticleMeta API backend for SciELO."""

import urllib.parse
import warnings
from typing import Any, Iterator, Optional

from easyscielo.errors import BlockedError
from easyscielo.filters import _remove_accents
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query


def article_to_record(payload: dict[str, Any]) -> Article:
    """Map ArticleMeta article JSON payload to an Article object.

    Args:
        payload: JSON dictionary retrieved from ArticleMeta endpoint.

    Returns:
        Mapped Article instance.
    """
    art = payload.get("article", {}) if isinstance(payload, dict) else {}

    # Title
    title = ""
    v12 = art.get("v12", [])
    if isinstance(v12, list) and v12:
        for item in v12:
            if isinstance(item, dict) and item.get("_"):
                title = item["_"]
                break
            elif isinstance(item, str) and item:
                title = item
                break

    if not title:
        raw_title = payload.get("title")
        if isinstance(raw_title, str):
            title = raw_title
        elif isinstance(raw_title, dict):
            for lang_key in ("en", "es", "pt"):
                if lang_key in raw_title and isinstance(raw_title[lang_key], str):
                    title = raw_title[lang_key]
                    break
            if not title:
                for k, v in raw_title.items():
                    if isinstance(v, str) and not k.startswith("v"):
                        title = v
                        break

    # Authors
    authors: list[str] = []
    raw_v10 = art.get("v10") or payload.get("authors") or []
    if isinstance(raw_v10, list):
        for a in raw_v10:
            if isinstance(a, str):
                if a.strip():
                    authors.append(a.strip())
            elif isinstance(a, dict):
                _val = a.get("_", "").strip()
                if _val:
                    authors.append(_val)
                else:
                    n = (a.get("n") or a.get("given_names") or "").strip()
                    s = (a.get("s") or a.get("surname") or "").strip()
                    if n and s:
                        authors.append(f"{n} {s}")
                    elif s:
                        authors.append(s)
                    elif n:
                        authors.append(n)

    # Year
    year = 0
    pub_year = payload.get("publication_year")
    if pub_year is not None:
        try:
            year = int(pub_year)
        except (ValueError, TypeError):
            year = 0

    if not year:
        v65 = art.get("v65", [])
        year_str = ""
        if isinstance(v65, list) and v65:
            first = v65[0]
            if isinstance(first, dict):
                year_str = first.get("_", "")
            elif isinstance(first, str):
                year_str = first
        if len(year_str) >= 4 and year_str[:4].isdigit():
            year = int(year_str[:4])

    # DOI
    doi: Optional[str] = payload.get("doi")
    if not doi and "v237" in art:
        v237 = art.get("v237", [])
        if isinstance(v237, list) and v237:
            first = v237[0]
            if isinstance(first, dict):
                doi = first.get("_")
            elif isinstance(first, str):
                doi = first

    # Abstract
    abstract: Optional[str] = None
    v83 = art.get("v83", [])
    if isinstance(v83, list) and v83:
        for item in v83:
            if isinstance(item, dict):
                txt = item.get("a") or item.get("_")
                if txt:
                    abstract = txt
                    break
            elif isinstance(item, str) and item:
                abstract = item
                break

    if not abstract:
        raw_abs = payload.get("abstract")
        if isinstance(raw_abs, str):
            abstract = raw_abs
        elif isinstance(raw_abs, dict):
            for lang_key in ("en", "es", "pt"):
                if lang_key in raw_abs and isinstance(raw_abs[lang_key], str):
                    abstract = raw_abs[lang_key]
                    break
            if not abstract:
                for k, v in raw_abs.items():
                    if isinstance(v, str):
                        abstract = v
                        break

    # Journal
    journal: Optional[str] = None
    v30 = art.get("v30", [])
    if isinstance(v30, list) and v30:
        first = v30[0]
        if isinstance(first, dict):
            journal = first.get("_")
        elif isinstance(first, str):
            journal = first

    if not journal and isinstance(payload.get("title"), dict):
        v100 = payload["title"].get("v100", [])
        if isinstance(v100, list) and v100:
            first = v100[0]
            if isinstance(first, dict):
                journal = first.get("_")
            elif isinstance(first, str):
                journal = first

    if not journal:
        raw_j = payload.get("journal")
        if isinstance(raw_j, str):
            journal = raw_j

    # Journal ISSN
    journal_issn: Optional[str] = None
    v35 = art.get("v35", [])
    if isinstance(v35, list) and v35:
        first = v35[0]
        if isinstance(first, dict):
            journal_issn = first.get("_")
        elif isinstance(first, str):
            journal_issn = first

    if not journal_issn and isinstance(payload.get("title"), dict):
        v35_t = payload["title"].get("v35", [])
        if isinstance(v35_t, list) and v35_t:
            first = v35_t[0]
            if isinstance(first, dict):
                journal_issn = first.get("_")
            elif isinstance(first, str):
                journal_issn = first

    if not journal_issn:
        raw_issn = payload.get("issn") or payload.get("journal_issn")
        if isinstance(raw_issn, str):
            journal_issn = raw_issn

    # Categories
    categories: list[str] = []
    title_dict = (
        payload.get("title", {})
        if isinstance(payload, dict) and isinstance(payload.get("title"), dict)
        else {}
    )
    for cat_field in ("v440", "v441", "v854"):
        raw_cats = art.get(cat_field) or title_dict.get(cat_field) or []
        if isinstance(raw_cats, list):
            for item in raw_cats:
                if isinstance(item, dict) and item.get("_"):
                    c_val = item["_"].strip()
                    if c_val and c_val not in categories:
                        categories.append(c_val)
                elif isinstance(item, str) and item.strip():
                    c_val = item.strip()
                    if c_val not in categories:
                        categories.append(c_val)

    if not categories and payload.get("categories"):
        raw_c = payload.get("categories")
        if isinstance(raw_c, list):
            categories = [str(i) for i in raw_c]
        elif isinstance(raw_c, str):
            categories = [raw_c]

    # Collection
    collection: Optional[str] = payload.get("collection") or art.get("collection")

    # PID
    pid: Optional[str] = payload.get("code") or art.get("code")

    # Languages
    languages: list[str] = []
    v40 = art.get("v40", [])
    if isinstance(v40, list):
        for item in v40:
            if isinstance(item, dict) and "_" in item:
                languages.append(item["_"])
            elif isinstance(item, str):
                languages.append(item)
    if not languages and payload.get("languages"):
        raw_lang = payload.get("languages")
        if isinstance(raw_lang, list):
            languages = [str(item) for item in raw_lang]
        elif isinstance(raw_lang, str):
            languages = [raw_lang]

    return Article(
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        abstract=abstract,
        journal=journal,
        collection=collection,
        pid=pid,
        languages=languages,
        journal_issn=journal_issn,
        categories=categories,
        source="articlemeta",
    )


def matches(article: Article, query: Query) -> bool:
    """Filter article against query criteria locally.

    Matches search term (accent-insensitive, case-insensitive, all words present)
    in title + abstract, and applies year range, languages, journals/issn, and categories.

    Args:
        article: Mapped Article instance.
        query: Query object.

    Returns:
        True if article matches query filters, False otherwise.
    """
    # 1. Term matching
    if query.term.strip():
        norm_term = _remove_accents(query.term).lower().strip()
        query_words = norm_term.split()

        text = f"{article.title or ''} {article.abstract or ''}"
        norm_text = _remove_accents(text).lower()

        if not all(word in norm_text for word in query_words):
            return False

    # 2. Year filtering
    art_year = article.year
    if query.year_start is not None:
        if art_year is None or art_year == 0 or art_year < int(query.year_start):
            return False
    if query.year_end is not None:
        if art_year is None or art_year == 0 or art_year > int(query.year_end):
            return False

    # 3. Languages filtering
    if query.languages:
        q_langs = [lang.lower().strip() for lang in query.languages if lang]
        a_langs = [lang.lower().strip() for lang in article.languages if lang]
        if not any(ql in a_langs for ql in q_langs):
            return False

    # 4. Journal / ISSN filtering
    query_journals: list[str] = list(query.journals)
    if query.journal_issn and query.journal_issn not in query_journals:
        query_journals.append(query.journal_issn)

    if query_journals:
        norm_q_j = [_remove_accents(j).lower().strip() for j in query_journals if j]
        norm_a_j = (
            _remove_accents(article.journal).lower().strip() if article.journal else ""
        )
        norm_a_issn = (
            article.journal_issn.lower().strip() if article.journal_issn else ""
        )

        matched = False
        for qj in norm_q_j:
            if (norm_a_issn and qj == norm_a_issn) or (
                norm_a_j and (qj in norm_a_j or norm_a_j in qj)
            ):
                matched = True
                break
        if not matched:
            return False

    # 5. Categories filtering
    if query.categories:
        norm_q_cats = [
            _remove_accents(c).lower().strip() for c in query.categories if c
        ]
        norm_a_cats = [
            _remove_accents(c).lower().strip() for c in article.categories if c
        ]

        matched = False
        for qc in norm_q_cats:
            if any(qc in ac or ac in qc for ac in norm_a_cats):
                matched = True
                break
        if not matched:
            return False

    return True


class ArticleMetaBackend:
    """Backend for SciELO ArticleMeta REST API."""

    name: str = "articlemeta"
    base_url: str = "https://articlemeta.scielo.org/api/v1"

    def __init__(self, client: Optional[HttpClient] = None) -> None:
        self.client = client

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        """Fetch articles from ArticleMeta paginating identifiers by offset.

        Args:
            query: Query object.
            n_max: Maximum number of articles to yield.
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
        collections: list[str] = list(query.collections)
        if query.collection and query.collection not in collections:
            collections.append(query.collection)

        journals: list[str] = list(query.journals)
        if query.journal_issn and query.journal_issn not in journals:
            journals.append(query.journal_issn)

        if query.term.strip() and not collections and not journals:
            warnings.warn(
                "ArticleMeta textual search without 'collection' or 'journal_issn' requires scanning all articles (expensive operation).",
                UserWarning,
                stacklevel=2,
            )

        target_n_max: Optional[int] = n_max

        offset = 0
        limit = 50
        total_fetched = 0
        failed_articles = 0

        try:
            while True:
                if target_n_max is not None and total_fetched >= target_n_max:
                    return

                url = (
                    f"{self.base_url}/article/identifiers/"
                    f"?offset={offset}&limit={limit}"
                )
                if collections:
                    url += f"&collection={urllib.parse.quote(collections[0])}"
                if journals:
                    url += f"&issn={urllib.parse.quote(journals[0])}"

                response = http.get(url)
                data = response.json()

                objects = data.get("objects", [])
                meta = data.get("meta", {})
                total = meta.get("total")

                if not objects:
                    return

                for obj in objects:
                    code = obj.get("code")
                    col = obj.get("collection")
                    if not code:
                        continue

                    art_url = f"{self.base_url}/article/?code={code}"
                    if col:
                        art_url += f"&collection={urllib.parse.quote(col)}"

                    try:
                        art_resp = http.get(art_url)
                        art_payload = art_resp.json()
                    except BlockedError:
                        raise
                    except Exception:
                        failed_articles += 1
                        continue

                    article = article_to_record(art_payload)

                    if not matches(article, query):
                        continue

                    yield article

                    total_fetched += 1
                    if target_n_max is not None and total_fetched >= target_n_max:
                        return

                offset += len(objects)

                if total is not None and offset >= total:
                    return
        finally:
            if failed_articles > 0:
                warnings.warn(
                    f"{failed_articles} artigos não puderam ser lidos e foram "
                    "pulados",
                    UserWarning,
                    stacklevel=2,
                )
