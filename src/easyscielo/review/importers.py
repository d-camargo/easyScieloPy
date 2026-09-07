"""Importers for systematic review data formats."""

import ast
import csv
import io
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional

from easyscielo._optional import require
from easyscielo.models import Article
from easyscielo.review.models import ReviewRecord, Stage, make_record_id

__all__ = ["from_ris", "from_bibtex", "from_csv", "from_articles"]


def from_ris(
    path_or_text: str | Path,
    source_db: Optional[str] = None,
) -> list[ReviewRecord]:
    """Import records from a RIS file or text string into a list of ReviewRecords.

    Requires rispy optional dependency (pip install easyscielopy[review]).

    Args:
        path_or_text: File path (str or Path) or raw RIS text string.
        source_db: Optional database source name. Defaults to f"ris:{nome_do_arquivo}".

    Returns:
        List of ReviewRecord objects with stage=IDENTIFIED and source="ris".
    """
    rispy = require("rispy", "review")

    if isinstance(path_or_text, Path):
        file_path = path_or_text
        text_content = file_path.read_text(encoding="utf-8")
        filename = file_path.name
    elif isinstance(path_or_text, str):
        path_candidate = Path(path_or_text)
        if path_candidate.exists() and path_candidate.is_file():
            text_content = path_candidate.read_text(encoding="utf-8")
            filename = path_candidate.name
        elif (
            "\n" in path_or_text
            or "\r" in path_or_text
            or path_or_text.strip().startswith("TY ")
        ):
            text_content = path_or_text
            filename = "text"
        else:
            text_content = path_candidate.read_text(encoding="utf-8")
            filename = path_candidate.name
    else:
        raise TypeError(
            f"Expected str or Path for path_or_text, got {type(path_or_text)}"
        )

    if source_db is None:
        source_db = f"ris:{filename}"

    entries = rispy.loads(text_content)
    records: list[ReviewRecord] = []

    for entry in entries:
        # Title mapping: TI or T1 -> title
        title_raw = entry.get("title") or entry.get("primary_title") or ""
        title = str(title_raw).strip()

        # Authors mapping: AU or A1 (all) -> authors
        raw_authors = entry.get("authors") or entry.get("first_authors") or []
        if isinstance(raw_authors, str):
            raw_authors = [raw_authors]

        if "authors" in entry and "first_authors" in entry:
            authors_list = (
                list(entry["authors"])
                if isinstance(entry["authors"], list)
                else [entry["authors"]]
            )
            first_list = (
                list(entry["first_authors"])
                if isinstance(entry["first_authors"], list)
                else [entry["first_authors"]]
            )
            for item in first_list:
                if item not in authors_list:
                    authors_list.append(item)
            raw_authors = authors_list

        authors = [str(a).strip() for a in raw_authors if a and str(a).strip()]

        # Year mapping: PY or Y1 -> year (4-digit regex)
        raw_year = entry.get("year") or entry.get("publication_year")
        year = 0
        if raw_year:
            match = re.search(r"\d{4}", str(raw_year))
            if match:
                year = int(match.group(0))

        # DOI mapping: DO -> doi
        doi_raw = entry.get("doi")
        doi = str(doi_raw).strip() if doi_raw and str(doi_raw).strip() else None

        # Abstract mapping: AB or N2 -> abstract
        ab_raw = entry.get("abstract") or entry.get("notes_abstract")
        abstract = str(ab_raw).strip() if ab_raw and str(ab_raw).strip() else None

        # Journal mapping: JO, T2, or JF -> journal
        jo_raw = (
            entry.get("journal_name")
            or entry.get("secondary_title")
            or entry.get("alternate_title3")
        )
        journal = str(jo_raw).strip() if jo_raw and str(jo_raw).strip() else None

        # Language mapping: LA -> languages
        la_raw = entry.get("language")
        if isinstance(la_raw, list):
            languages = [str(x).strip() for x in la_raw if x and str(x).strip()]
        elif la_raw and str(la_raw).strip():
            languages = [str(la_raw).strip()]
        else:
            languages = []

        # Journal ISSN mapping: SN -> journal_issn
        sn_raw = entry.get("issn")
        journal_issn = str(sn_raw).strip() if sn_raw and str(sn_raw).strip() else None

        # URL mapping: UR -> url
        ur_raw = entry.get("urls") or entry.get("url")
        url: Optional[str] = None
        if isinstance(ur_raw, list) and ur_raw:
            url = str(ur_raw[0]).strip() if ur_raw[0] else None
        elif ur_raw and str(ur_raw).strip():
            url = str(ur_raw).strip()

        article = Article(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            journal=journal,
            collection=source_db,
            url=url,
            languages=languages,
            journal_issn=journal_issn,
            source="ris",
        )

        record = ReviewRecord(
            record_id=make_record_id(article),
            article=article,
            stage=Stage.IDENTIFIED,
            source_db=source_db,
        )
        records.append(record)

    return records


def from_bibtex(
    path_or_text: str | Path,
    source_db: Optional[str] = None,
) -> list[ReviewRecord]:
    """Import records from a BibTeX file or text string into a list of ReviewRecords.

    Requires bibtexparser optional dependency (pip install easyscielopy[review]).

    Args:
        path_or_text: File path (str or Path) or raw BibTeX text string.
        source_db: Optional database source name. Defaults to f"bibtex:{filename}".

    Returns:
        List of ReviewRecord objects with stage=IDENTIFIED and source="bibtex".
    """
    bibtexparser = require("bibtexparser", "review")

    if isinstance(path_or_text, Path):
        file_path = path_or_text
        text_content = file_path.read_text(encoding="utf-8")
        filename = file_path.name
    elif isinstance(path_or_text, str):
        path_candidate = Path(path_or_text)
        if path_candidate.exists() and path_candidate.is_file():
            text_content = path_candidate.read_text(encoding="utf-8")
            filename = path_candidate.name
        elif "\n" in path_or_text or "\r" in path_or_text or "@" in path_or_text:
            text_content = path_or_text
            filename = "text"
        else:
            text_content = path_candidate.read_text(encoding="utf-8")
            filename = path_candidate.name
    else:
        raise TypeError(
            f"Expected str or Path for path_or_text, got {type(path_or_text)}"
        )

    if source_db is None:
        source_db = f"bibtex:{filename}"

    db = bibtexparser.loads(text_content)
    entries = getattr(db, "entries", db)
    records: list[ReviewRecord] = []

    for entry in entries:
        title_raw = entry.get("title") or ""
        title = str(title_raw).strip()

        author_raw = entry.get("author") or entry.get("authors") or ""
        if isinstance(author_raw, str):
            authors = [
                a.strip()
                for a in re.split(r"\s+and\s+", author_raw, flags=re.IGNORECASE)
                if a.strip()
            ]
        elif isinstance(author_raw, list):
            authors = [str(a).strip() for a in author_raw if a and str(a).strip()]
        else:
            authors = []

        raw_year = entry.get("year") or entry.get("publication_year")
        year = 0
        if raw_year:
            match = re.search(r"\d{4}", str(raw_year))
            if match:
                year = int(match.group(0))

        doi_raw = entry.get("doi")
        doi = str(doi_raw).strip() if doi_raw and str(doi_raw).strip() else None

        ab_raw = entry.get("abstract")
        abstract = str(ab_raw).strip() if ab_raw and str(ab_raw).strip() else None

        jo_raw = entry.get("journal") or entry.get("journaltitle")
        journal = str(jo_raw).strip() if jo_raw and str(jo_raw).strip() else None

        issn_raw = entry.get("issn")
        journal_issn = (
            str(issn_raw).strip() if issn_raw and str(issn_raw).strip() else None
        )

        url_raw = entry.get("url")
        url = str(url_raw).strip() if url_raw and str(url_raw).strip() else None

        article = Article(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            journal=journal,
            collection=source_db,
            url=url,
            journal_issn=journal_issn,
            source="bibtex",
        )

        record = ReviewRecord(
            record_id=make_record_id(article),
            article=article,
            stage=Stage.IDENTIFIED,
            source_db=source_db,
        )
        records.append(record)

    return records


def from_csv(
    path_or_text: str | Path,
    source_db: Optional[str] = None,
) -> list[ReviewRecord]:
    """Import records from a CSV file or text string into a list of ReviewRecords.

    Compatible with CSV structure written by frame.py::to_csv.

    Args:
        path_or_text: File path (str or Path) or raw CSV text string.
        source_db: Optional database source name. Defaults to row['collection'] or f"csv:{filename}".

    Returns:
        List of ReviewRecord objects with stage=IDENTIFIED.
    """
    if isinstance(path_or_text, Path):
        file_path = path_or_text
        text_content = file_path.read_text(encoding="utf-8")
        filename = file_path.name
    elif isinstance(path_or_text, str):
        path_candidate = Path(path_or_text)
        if path_candidate.exists() and path_candidate.is_file():
            text_content = path_candidate.read_text(encoding="utf-8")
            filename = path_candidate.name
        elif "\n" in path_or_text or "\r" in path_or_text or "," in path_or_text:
            text_content = path_or_text
            filename = "text"
        else:
            text_content = path_candidate.read_text(encoding="utf-8")
            filename = path_candidate.name
    else:
        raise TypeError(
            f"Expected str or Path for path_or_text, got {type(path_or_text)}"
        )

    def _parse_list_field(val: Any) -> list[str]:
        if not val:
            return []
        if isinstance(val, list):
            return [str(x).strip() for x in val if x and str(x).strip()]
        s_val = str(val).strip()
        if not s_val:
            return []
        if s_val.startswith("[") and s_val.endswith("]"):
            try:
                parsed = ast.literal_eval(s_val)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if x and str(x).strip()]
            except (ValueError, SyntaxError):
                pass
        return [s_val]

    reader = csv.DictReader(io.StringIO(text_content))
    records: list[ReviewRecord] = []

    for row in reader:
        title = str(row.get("title") or "").strip()
        authors = _parse_list_field(row.get("authors"))

        raw_year = row.get("year")
        year = 0
        if raw_year:
            match = re.search(r"\d{4}", str(raw_year))
            if match:
                year = int(match.group(0))

        doi_raw = row.get("doi")
        doi = str(doi_raw).strip() if doi_raw and str(doi_raw).strip() else None

        ab_raw = row.get("abstract")
        abstract = str(ab_raw).strip() if ab_raw and str(ab_raw).strip() else None

        jo_raw = row.get("journal")
        journal = str(jo_raw).strip() if jo_raw and str(jo_raw).strip() else None

        row_coll = row.get("collection")
        coll_str = str(row_coll).strip() if row_coll and str(row_coll).strip() else None

        collection = (
            source_db if source_db is not None else (coll_str or f"csv:{filename}")
        )

        pid_raw = row.get("pid")
        pid = str(pid_raw).strip() if pid_raw and str(pid_raw).strip() else None

        url_raw = row.get("url")
        url = str(url_raw).strip() if url_raw and str(url_raw).strip() else None

        languages = _parse_list_field(row.get("languages"))

        issn_raw = row.get("journal_issn")
        journal_issn = (
            str(issn_raw).strip() if issn_raw and str(issn_raw).strip() else None
        )

        categories = _parse_list_field(row.get("categories"))

        src_raw = row.get("source")
        source = str(src_raw).strip() if src_raw and str(src_raw).strip() else "csv"

        article = Article(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            journal=journal,
            collection=collection,
            pid=pid,
            url=url,
            languages=languages,
            journal_issn=journal_issn,
            categories=categories,
            source=source,
        )

        rec_id = (
            str(row.get("record_id")).strip()
            if row.get("record_id") and str(row.get("record_id")).strip()
            else make_record_id(article)
        )

        stage_raw = row.get("stage")
        stage = Stage.IDENTIFIED
        if stage_raw and str(stage_raw).strip() in Stage.__members__:
            stage = Stage[str(stage_raw).strip()]

        source_db_raw = row.get("source_db")
        source_db_val = (
            str(source_db_raw).strip()
            if source_db_raw and str(source_db_raw).strip()
            else None
        )
        if source_db is None:
            source_db = source_db_val or coll_str or f"csv:{filename}"

        record = ReviewRecord(
            record_id=rec_id,
            article=article,
            stage=stage,
            source_db=source_db,
        )
        records.append(record)

    return records


def from_articles(
    articles: Iterable[Article],
    source_db: Optional[str] = None,
) -> list[ReviewRecord]:
    """Import records from an iterable of Article objects.

    Args:
        articles: Iterable of Article objects.
        source_db: Optional database source name. Defaults to article.source.

    Returns:
        List of ReviewRecord objects with stage=IDENTIFIED.
    """
    records: list[ReviewRecord] = []
    for art in articles:
        db = (
            source_db
            if source_db is not None
            else (art.source or art.collection or "unknown")
        )
        if art.collection is None or source_db is not None:
            art.collection = db
        record = ReviewRecord(
            record_id=make_record_id(art),
            article=art,
            stage=Stage.IDENTIFIED,
            source_db=db,
        )
        records.append(record)
    return records
