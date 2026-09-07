"""Tests for RIS importer (from_ris)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from easyscielo.review.importers import from_ris
from easyscielo.review.models import Stage, make_record_id

pytest.importorskip("rispy")

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "review"
PUBMED_RIS = FIXTURES_DIR / "pubmed_sample.ris"


def test_from_ris_pubmed_sample_file() -> None:
    """Test importing pubmed_sample.ris fixture file."""
    records = from_ris(PUBMED_RIS)
    assert len(records) == 5

    # Check first record: multiple authors
    r1 = records[0]
    assert r1.stage == Stage.IDENTIFIED
    assert r1.article.source == "ris"
    assert r1.article.collection == "ris:pubmed_sample.ris"
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
    assert r1.article.doi == "10.11606/s1518-8787.2023057004500"
    assert r1.article.journal == "Revista de Saúde Pública"
    assert r1.article.abstract is not None
    assert "cobertura vacinal" in r1.article.abstract
    assert r1.record_id == make_record_id(r1.article)

    # Check third record: record without DOI
    r3 = records[2]
    assert r3.article.doi is None
    assert (
        r3.article.title
        == "Análise histórica da saúde coletiva na América Latina durante o século XX"
    )
    assert r3.article.year == 2021
    assert r3.article.authors == ["Gómez, Fernando", "Gonçalves, Beatriz"]
    assert r3.record_id is not None
    assert len(r3.record_id) == 16
    assert r3.record_id == make_record_id(r3.article)


def test_from_ris_string_path() -> None:
    """Test passing string path instead of Path object."""
    records = from_ris(str(PUBMED_RIS))
    assert len(records) == 5
    assert records[0].article.collection == "ris:pubmed_sample.ris"


def test_from_ris_custom_source_db() -> None:
    """Test passing an explicit source_db parameter."""
    records = from_ris(PUBMED_RIS, source_db="pubmed_2024")
    assert len(records) == 5
    for r in records:
        assert r.article.collection == "pubmed_2024"


def test_from_ris_raw_text() -> None:
    """Test passing raw RIS text content to from_ris."""
    ris_text = """TY  - JOUR
T1  - Primary Title T1
A1  - Author A1
Y1  - 2022/03/15
DO  - 10.1000/test.123
N2  - Abstract N2
T2  - Secondary Title T2
LA  - English
SN  - 1234-5678
UR  - https://example.org/article
ER  - 
"""
    records = from_ris(ris_text)
    assert len(records) == 1
    r = records[0]
    assert r.article.title == "Primary Title T1"
    assert r.article.authors == ["Author A1"]
    assert r.article.year == 2022
    assert r.article.doi == "10.1000/test.123"
    assert r.article.abstract == "Abstract N2"
    assert r.article.journal == "Secondary Title T2"
    assert r.article.languages == ["English"]
    assert r.article.journal_issn == "1234-5678"
    assert r.article.url == "https://example.org/article"
    assert r.article.collection == "ris:text"
    assert r.article.source == "ris"


def test_from_ris_missing_fields_rule_d2() -> None:
    """Test that missing RIS fields result in None / empty list and are never absent from as_dict."""
    minimal_ris = """TY  - JOUR
TI  - Minimal Article
AU  - Solo Author
PY  - 2020
ER  - 
"""
    records = from_ris(minimal_ris)
    assert len(records) == 1
    r = records[0]
    assert r.article.doi is None
    assert r.article.abstract is None
    assert r.article.journal is None
    assert r.article.url is None
    assert r.article.journal_issn is None
    assert r.article.languages == []

    d = r.as_dict()
    assert "doi" in d and d["doi"] is None
    assert "abstract" in d and d["abstract"] is None
    assert "journal" in d and d["journal"] is None
    assert "url" in d and d["url"] is None
    assert "languages" in d and d["languages"] == []


def test_from_ris_missing_dependency() -> None:
    """Test raising ImportError when rispy is not installed."""
    with patch(
        "importlib.import_module", side_effect=ImportError("No module named 'rispy'")
    ):
        with pytest.raises(ImportError, match="rispy is required"):
            from_ris("TY  - JOUR\nTI  - Test\nER  - \n")
