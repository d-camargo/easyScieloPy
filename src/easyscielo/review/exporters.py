"""Exporters for systematic review data formats."""

import csv
import json
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from easyscielo._optional import require
from easyscielo.models import Article
from easyscielo.review.models import ReviewRecord, Stage, make_record_id

__all__ = ["to_ris", "to_bibtex", "to_review_csv", "to_json"]


def _to_record(item: ReviewRecord | Article) -> ReviewRecord:
    """Ensure an item is a ReviewRecord."""
    if isinstance(item, ReviewRecord):
        return item
    if isinstance(item, Article):
        return ReviewRecord(
            record_id=make_record_id(item),
            article=item,
            stage=Stage.IDENTIFIED,
        )
    raise TypeError(f"Expected ReviewRecord or Article, got {type(item)}")


def _clean_word(text: str) -> str:
    """Normalize unicode accents to ASCII and strip non-alphanumeric characters."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("utf-8")
    cleaned = re.sub(r"[^\w]", "", ascii_text)
    return cleaned.lower()


def _extract_first_word(text: str) -> str:
    """Extract and normalize the first alphanumeric word from text."""
    if not text:
        return ""
    words = text.strip().split()
    for word in words:
        cleaned = _clean_word(word)
        if cleaned:
            return cleaned
    return ""


def _make_suffix(idx: int) -> str:
    """Generate disambiguation suffix: a, b, ..., z, aa, ab, ..."""
    if idx < 26:
        return chr(ord("a") + idx)
    first = chr(ord("a") + (idx // 26) - 1)
    second = chr(ord("a") + (idx % 26))
    return f"{first}{second}"


def to_ris(
    records: Iterable[ReviewRecord | Article],
    path: str | Path,
) -> None:
    """Export review records or articles to a RIS file.

    Requires rispy optional dependency (pip install easyscielopy[review]).

    Args:
        records: Collection of ReviewRecord or Article objects.
        path: Output file path.
    """
    rispy = require("rispy", "review")
    path_obj = Path(path)

    entries: list[dict[str, Any]] = []
    for item in records:
        rec = _to_record(item)
        art = rec.article
        entry: dict[str, Any] = {"type_of_reference": "JOUR"}

        if art.title:
            entry["title"] = art.title
        if art.authors:
            entry["authors"] = art.authors
        if art.year:
            entry["year"] = str(art.year)
        if art.doi:
            entry["doi"] = art.doi
        if art.abstract:
            entry["abstract"] = art.abstract
        if art.journal:
            entry["journal_name"] = art.journal
        if art.languages:
            entry["language"] = art.languages
        if art.journal_issn:
            entry["issn"] = art.journal_issn
        if art.url:
            entry["urls"] = [art.url]

        entries.append(entry)

    content = rispy.dumps(entries)
    path_obj.write_text(content, encoding="utf-8")


def to_bibtex(
    records: Iterable[ReviewRecord | Article],
    path: str | Path,
) -> None:
    """Export review records or articles to a BibTeX file.

    Requires bibtexparser optional dependency (pip install easyscielopy[review]).

    Cite key format: primeiroautor + ano + primeirapalavradotítulo
    Collisions are disambiguated using a, b, c, ... suffixes.

    Args:
        records: Collection of ReviewRecord or Article objects.
        path: Output file path.
    """
    bibtexparser = require("bibtexparser", "review")
    path_obj = Path(path)

    seen_keys: set[str] = set()
    entries: list[dict[str, str]] = []

    for item in records:
        rec = _to_record(item)
        art = rec.article

        author_part = _extract_first_word(art.authors[0]) if art.authors else "unknown"
        if not author_part:
            author_part = "unknown"

        year_part = str(art.year) if art.year and art.year > 0 else "0000"

        title_part = _extract_first_word(art.title) if art.title else "untitled"
        if not title_part:
            title_part = "untitled"

        base_key = f"{author_part}{year_part}{title_part}"

        if base_key not in seen_keys:
            cite_key = base_key
        else:
            suffix_idx = 0
            while True:
                suffix = _make_suffix(suffix_idx)
                candidate = f"{base_key}{suffix}"
                if candidate not in seen_keys:
                    cite_key = candidate
                    break
                suffix_idx += 1

        seen_keys.add(cite_key)

        entry: dict[str, str] = {
            "ENTRYTYPE": "article",
            "ID": cite_key,
        }
        if art.title:
            entry["title"] = art.title
        if art.authors:
            entry["author"] = " and ".join(art.authors)
        if art.year:
            entry["year"] = str(art.year)
        if art.doi:
            entry["doi"] = art.doi
        if art.abstract:
            entry["abstract"] = art.abstract
        if art.journal:
            entry["journal"] = art.journal
        if art.journal_issn:
            entry["issn"] = art.journal_issn
        if art.url:
            entry["url"] = art.url

        entries.append(entry)

    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = entries
    content = bibtexparser.dumps(db)
    path_obj.write_text(content, encoding="utf-8")


def to_review_csv(
    records: Iterable[ReviewRecord | Article],
    path: str | Path,
) -> None:
    """Export review records or articles to a CSV file including review metadata columns.

    Args:
        records: Collection of ReviewRecord or Article objects.
        path: Output file path.
    """
    path_obj = Path(path)
    rec_list = [_to_record(r) for r in records]
    rows = [r.as_dict() for r in rec_list]

    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = [
            "title",
            "authors",
            "year",
            "doi",
            "abstract",
            "journal",
            "collection",
            "pid",
            "url",
            "languages",
            "journal_issn",
            "categories",
            "source",
            "record_id",
            "stage",
            "source_db",
            "decision",
            "duplicate_of",
            "decision_reason",
        ]

    with open(path_obj, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def to_json(
    records: Iterable[ReviewRecord | Article],
    path: str | Path,
) -> None:
    """Export review records or articles to a JSON file.

    Args:
        records: Collection of ReviewRecord or Article objects.
        path: Output file path.
    """
    path_obj = Path(path)
    rec_list = [_to_record(r) for r in records]
    data = [r.as_dict() for r in rec_list]
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
