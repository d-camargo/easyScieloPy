"""Tests for SciELO HTML search parser."""

from pathlib import Path

from easyscielo.backends.search_html import parse_search_page, parse_total_hits
from easyscielo.models import Article


def test_parse_search_page_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "search_page.html"
    html = fixture_path.read_text(encoding="utf-8")

    articles = parse_search_page(html, lang="en")

    # Número de itens > 0
    assert len(articles) > 0

    # Primeiro artigo com título e autores não vazios
    first = articles[0]
    assert isinstance(first, Article)
    assert first.title != ""
    assert len(first.authors) > 0

    # Nenhum campo do schema faltando (D2): campos que o backend não
    # conhece vêm como None/lista vazia, nunca ausentes
    expected_fields = {
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
    }
    article_dict = first.as_dict()
    assert set(article_dict.keys()) == expected_fields
    assert article_dict["source"] == "search"

    # Verificações dos valores específicos do fixture
    assert first.title == "Epidemiological analysis"
    assert first.authors == ["Silva, Ana", "Santos, Carlos"]
    assert first.year == 2023
    assert first.doi == "https://doi.org/10.1590/0102-311X00012323"
    assert first.pid == "art-001"
    assert first.journal == "Cadernos de Saude Publica"
    assert (
        first.abstract
        == "This study presents an epidemiological overview of disease patterns."
    )


def test_parse_search_page_lang_fallback():
    html_sample = """
    <div class="item" id="art-999">
        <strong class="title">Estudo de Caso</strong>
        <div class="authors"><a class="author">Silva, B.</a></div>
        <div class="source"><span>2021</span></div>
        <div id="art-999_es" class="abstract">Resumen en español</div>
    </div>
    """
    articles = parse_search_page(html_sample, lang="es")
    assert len(articles) == 1
    assert articles[0].abstract == "Resumen en español"


def test_parse_total_hits_none():
    fixture_path = Path(__file__).parent / "fixtures" / "search_page.html"
    html = fixture_path.read_text(encoding="utf-8")
    assert parse_total_hits(html) is None


def test_parse_total_hits_present():
    html_span = '<div><span id="TotalHits">1,234</span></div>'
    assert parse_total_hits(html_span) == 1234

    html_input = '<div><input id="TotalHits" value="500"/></div>'
    assert parse_total_hits(html_input) == 500
