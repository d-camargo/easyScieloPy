"""Tests for review exporters (to_ris, to_bibtex, to_review_csv, to_json)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from easyscielo.models import Article
from easyscielo.review.exporters import to_bibtex, to_json, to_review_csv, to_ris
from easyscielo.review.importers import from_bibtex, from_csv, from_ris
from easyscielo.review.models import Decision, ReviewRecord, Stage, make_record_id

pytest.importorskip("rispy")
pytest.importorskip("bibtexparser")

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "review"
PUBMED_RIS = FIXTURES_DIR / "pubmed_sample.ris"
SCOPUS_BIB = FIXTURES_DIR / "scopus_sample.bib"


def test_to_ris_roundtrip(tmp_path: Path) -> None:
    """Test RIS -> ReviewRecord -> RIS round-trip preserving title, authors, year, and doi."""
    original_records = from_ris(PUBMED_RIS)
    assert len(original_records) == 5

    out_file = tmp_path / "exported.ris"
    to_ris(original_records, out_file)

    roundtrip_records = from_ris(out_file)
    assert len(roundtrip_records) == len(original_records)

    for orig, rt in zip(original_records, roundtrip_records):
        assert rt.article.title == orig.article.title
        assert rt.article.authors == orig.article.authors
        assert rt.article.year == orig.article.year
        assert rt.article.doi == orig.article.doi


def test_to_bibtex_key_disambiguation(tmp_path: Path) -> None:
    """Test BibTeX export and cite key disambiguation for two entries with the same author and year."""
    art1 = Article(
        title="Estudo sobre vacinação e imunologia",
        authors=["Silva, João Carlos", "Santos, Maria"],
        year=2023,
        doi="10.1000/test.1",
        journal="Revista A",
    )
    art2 = Article(
        title="Estudo sobre cobertura vacinal urbana",
        authors=["Silva, João Carlos"],
        year=2023,
        doi="10.1000/test.2",
        journal="Revista B",
    )

    rec1 = ReviewRecord(
        record_id=make_record_id(art1), article=art1, stage=Stage.IDENTIFIED
    )
    rec2 = ReviewRecord(
        record_id=make_record_id(art2), article=art2, stage=Stage.IDENTIFIED
    )

    out_file = tmp_path / "exported.bib"
    to_bibtex([rec1, rec2], out_file)

    content = out_file.read_text(encoding="utf-8")
    assert "@article{silva2023estudo," in content
    assert "@article{silva2023estudoa," in content

    # Re-import via from_bibtex to verify validity
    imported = from_bibtex(out_file)
    assert len(imported) == 2
    assert imported[0].article.title == art1.title
    assert imported[1].article.title == art2.title


def test_to_review_csv(tmp_path: Path) -> None:
    """Test exporting review records to CSV including review columns."""
    art = Article(
        title="Artigo de Teste CSV",
        authors=["Oliveira, Carlos"],
        year=2022,
        doi="10.1000/csv.1",
    )
    rec = ReviewRecord(
        record_id=make_record_id(art),
        article=art,
        stage=Stage.SCREENED,
        decision=Decision.INCLUDE,
        duplicate_of=None,
    )

    out_file = tmp_path / "review.csv"
    to_review_csv([rec], out_file)

    content = out_file.read_text(encoding="utf-8")
    header = content.splitlines()[0]
    assert "record_id" in header
    assert "stage" in header
    assert "decision" in header
    assert "duplicate_of" in header

    imported = from_csv(out_file)
    assert len(imported) == 1
    assert imported[0].article.title == art.title
    assert imported[0].stage == Stage.SCREENED


def test_to_json(tmp_path: Path) -> None:
    """Test exporting review records to JSON file."""
    art = Article(
        title="Artigo JSON",
        authors=["Lima, Ana"],
        year=2021,
    )
    rec = ReviewRecord(
        record_id=make_record_id(art),
        article=art,
        stage=Stage.INCLUDED,
        decision=Decision.INCLUDE,
    )

    out_file = tmp_path / "review.json"
    to_json([rec], out_file)

    content = out_file.read_text(encoding="utf-8")
    data = json.loads(content)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Artigo JSON"
    assert data[0]["stage"] == "INCLUDED"
    assert data[0]["decision"] == "INCLUDE"
    assert data[0]["record_id"] == rec.record_id


def test_to_ris_missing_dependency(tmp_path: Path) -> None:
    """Test raising ImportError when rispy is not installed."""
    with patch(
        "importlib.import_module", side_effect=ImportError("No module named 'rispy'")
    ):
        with pytest.raises(ImportError, match="rispy is required"):
            to_ris([], tmp_path / "test.ris")


def test_to_bibtex_missing_dependency(tmp_path: Path) -> None:
    """Test raising ImportError when bibtexparser is not installed."""
    with patch(
        "importlib.import_module",
        side_effect=ImportError("No module named 'bibtexparser'"),
    ):
        with pytest.raises(ImportError, match="bibtexparser is required"):
            to_bibtex([], tmp_path / "test.bib")
