"""Tests for CSV importer (from_csv) and from_articles importer."""

from pathlib import Path

from easyscielo.frame import to_csv, to_csv_string
from easyscielo.models import Article
from easyscielo.review.importers import from_articles, from_csv
from easyscielo.review.models import Stage, make_record_id


def test_csv_roundtrip_to_csv_and_from_csv(tmp_path: Path) -> None:
    """Test round-trip: export articles with frame.py::to_csv and reimport with from_csv."""
    art1 = Article(
        title="Estudo sobre vacinação e imunologia em populações vulneráveis no Brasil",
        authors=["Silva, João Carlos", "Santos, Maria Eduarda"],
        year=2023,
        doi="10.11606/s1518-8787.2023057004500",
        abstract="O objetivo deste estudo é analisar a cobertura vacinal em regiões vulneráveis.",
        journal="Revista de Saúde Pública",
        collection="scielo",
        languages=["pt", "en"],
        journal_issn="1518-8787",
        categories=["Public Health"],
        source="scielo",
    )

    art2 = Article(
        title="Análise histórica da saúde coletiva na América Latina durante o século XX",
        authors=["Gómez, Fernando", "Gonçalves, Beatriz"],
        year=2021,
        doi=None,
        abstract=None,
        journal="Cadernos de História da Ciência",
        collection="scielo",
        source="scielo",
    )

    articles = [art1, art2]
    original_ids = [make_record_id(a) for a in articles]

    # Write to CSV file using frame.py::to_csv
    csv_file = tmp_path / "exported.csv"
    to_csv(articles, csv_file)

    # Reimport using from_csv
    imported_records = from_csv(csv_file)
    assert len(imported_records) == 2

    # Assert round-trip devolve os mesmos record_id
    reimported_ids = [r.record_id for r in imported_records]
    assert reimported_ids == original_ids

    # Check first imported record details
    r1 = imported_records[0]
    assert r1.stage == Stage.IDENTIFIED
    assert r1.article.title == art1.title
    assert r1.article.authors == art1.authors
    assert r1.article.year == 2023
    assert r1.article.doi == art1.doi
    assert r1.article.abstract == art1.abstract
    assert r1.article.journal == art1.journal
    assert r1.article.languages == ["pt", "en"]
    assert r1.article.categories == ["Public Health"]
    assert r1.article.collection == "scielo"

    # Check second imported record (no DOI)
    r2 = imported_records[1]
    assert r2.article.doi is None
    assert r2.article.abstract is None
    assert r2.article.authors == ["Gómez, Fernando", "Gonçalves, Beatriz"]
    assert r2.article.year == 2021


def test_from_csv_string_content() -> None:
    """Test importing from CSV string content directly."""
    art = Article(
        title="String Test Title",
        authors=["Author A", "Author B"],
        year=2020,
        doi="10.1000/string.test",
        source="custom",
    )
    csv_str = to_csv_string([art])

    records = from_csv(csv_str)
    assert len(records) == 1
    r = records[0]
    assert r.record_id == make_record_id(art)
    assert r.article.title == "String Test Title"
    assert r.article.authors == ["Author A", "Author B"]
    assert r.article.year == 2020


def test_from_csv_custom_source_db(tmp_path: Path) -> None:
    """Test specifying an explicit source_db in from_csv."""
    art = Article(
        title="Custom Source Test",
        authors=["Author X"],
        year=2019,
        doi="10.1000/custom.test",
    )
    csv_file = tmp_path / "custom.csv"
    to_csv([art], csv_file)

    records = from_csv(csv_file, source_db="my_custom_db")
    assert len(records) == 1
    assert records[0].article.collection == "my_custom_db"


def test_from_articles_default_source_db() -> None:
    """Test default source_db in from_articles derived from article.source."""
    openalex_article = Article(
        title="OpenAlex Article Title",
        authors=["Alex, Open"],
        year=2022,
        doi="10.1000/openalex.123",
        source="openalex",
    )

    crossref_article = Article(
        title="Crossref Article Title",
        authors=["Cross, Ref"],
        year=2023,
        doi="10.1000/crossref.456",
        source="crossref",
    )

    records = from_articles([openalex_article, crossref_article])
    assert len(records) == 2

    # OpenAlex and Crossref identify themselves in the corpus
    r_openalex = records[0]
    assert r_openalex.stage == Stage.IDENTIFIED
    assert r_openalex.article.source == "openalex"
    assert r_openalex.article.collection == "openalex"
    assert r_openalex.record_id == make_record_id(openalex_article)

    r_crossref = records[1]
    assert r_crossref.stage == Stage.IDENTIFIED
    assert r_crossref.article.source == "crossref"
    assert r_crossref.article.collection == "crossref"
    assert r_crossref.record_id == make_record_id(crossref_article)


def test_from_articles_explicit_source_db() -> None:
    """Test specifying explicit source_db parameter in from_articles."""
    art = Article(
        title="Explicit Source DB Article",
        authors=["Author Y"],
        year=2024,
        source="openalex",
    )

    records = from_articles([art], source_db="override_db")
    assert len(records) == 1
    assert records[0].article.collection == "override_db"
