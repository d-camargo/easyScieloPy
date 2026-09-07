"""Tests for BibTeX importer (from_bibtex)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from easyscielo.review.importers import from_bibtex
from easyscielo.review.models import Stage, make_record_id

pytest.importorskip("bibtexparser")

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "review"
SCOPUS_BIB = FIXTURES_DIR / "scopus_sample.bib"


def test_from_bibtex_scopus_sample_file() -> None:
    """Test importing scopus_sample.bib fixture file."""
    records = from_bibtex(SCOPUS_BIB)
    assert len(records) == 5

    # Check first record: multiple authors separated by 'and'
    r1 = records[0]
    assert r1.stage == Stage.IDENTIFIED
    assert r1.article.source == "bibtex"
    assert r1.article.collection == "bibtex:scopus_sample.bib"
    assert (
        r1.article.title
        == "Estudo sobre vacinação e imunologia em populações vulneráveis no Brasil"
    )
    assert len(r1.article.authors) == 3
    assert r1.article.authors == [
        "Silva, João Carlos",
        "Santos, Maria Eduarda",
        "Oliveira, Ana Paula",
    ]
    assert r1.article.year == 2023
    assert isinstance(r1.article.year, int)
    assert r1.article.doi == "10.11606/s1518-8787.2023057004500"
    assert r1.article.journal == "Revista de Saúde Pública"
    assert r1.article.abstract is not None
    assert "cobertura vacinal" in r1.article.abstract
    assert r1.record_id == make_record_id(r1.article)

    # Check third record: record without abstract
    r3 = records[2]
    assert r3.article.doi == "10.1016/j.chc.2021.02.005"
    assert r3.article.abstract is None
    assert (
        r3.article.title
        == "Análise histórica da saúde coletiva na América Latina durante o século XX"
    )
    assert r3.article.year == 2021
    assert r3.article.authors == ["Gómez, Fernando", "Gonçalves, Beatriz"]
    assert r3.record_id == make_record_id(r3.article)


def test_from_bibtex_string_path() -> None:
    """Test passing string path instead of Path object."""
    records = from_bibtex(str(SCOPUS_BIB))
    assert len(records) == 5
    assert records[0].article.collection == "bibtex:scopus_sample.bib"


def test_from_bibtex_custom_source_db() -> None:
    """Test passing an explicit source_db parameter."""
    records = from_bibtex(SCOPUS_BIB, source_db="scopus_2024")
    assert len(records) == 5
    for r in records:
        assert r.article.collection == "scopus_2024"


def test_from_bibtex_raw_text() -> None:
    """Test passing raw BibTeX text content to from_bibtex."""
    bib_text = """@article{testkey,
    author = {Author One and Author Two},
    title = {Sample Title for Testing},
    journal = {Journal of Testing},
    year = {2022},
    doi = {10.1000/test.bib.123},
    abstract = {Sample BibTeX abstract},
    issn = {1234-5678},
    url = {https://example.org/test}
}
"""
    records = from_bibtex(bib_text)
    assert len(records) == 1
    r = records[0]
    assert r.article.title == "Sample Title for Testing"
    assert r.article.authors == ["Author One", "Author Two"]
    assert r.article.year == 2022
    assert r.article.doi == "10.1000/test.bib.123"
    assert r.article.abstract == "Sample BibTeX abstract"
    assert r.article.journal == "Journal of Testing"
    assert r.article.journal_issn == "1234-5678"
    assert r.article.url == "https://example.org/test"
    assert r.article.collection == "bibtex:text"
    assert r.article.source == "bibtex"


def test_from_bibtex_missing_dependency() -> None:
    """Test raising ImportError when bibtexparser is not installed."""
    with patch(
        "importlib.import_module",
        side_effect=ImportError("No module named 'bibtexparser'"),
    ):
        with pytest.raises(ImportError, match="bibtexparser is required"):
            from_bibtex("@article{test, title={Test}}")
