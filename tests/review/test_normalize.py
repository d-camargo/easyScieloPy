"""Tests for easyscielo.review.normalize module."""

import pytest

from easyscielo.models import Article
from easyscielo.review.normalize import (
    blocking_key,
    normalize_author,
    normalize_doi,
    normalize_title,
)

# --- normalize_doi tests ---


def test_normalize_doi_accented() -> None:
    assert normalize_doi("https://doi.org/10.1590/S0104-ÁÉÍÓÚ") == "10.1590/s0104-aeiou"


def test_normalize_doi_punctuation() -> None:
    assert normalize_doi("doi: 10.1000/182.v1(2) ") == "10.1000/182.v1(2)"


@pytest.mark.parametrize("val", [None, "", "   "])
def test_normalize_doi_empty_or_none(val: str | None) -> None:
    assert normalize_doi(val) == ""


def test_normalize_doi_standard_urls_and_prefixes() -> None:
    assert (
        normalize_doi("https://doi.org/10.1590/S0104-11692011000100002")
        == "10.1590/s0104-11692011000100002"
    )
    assert (
        normalize_doi("http://doi.org/10.1590/S0104-11692011000100002")
        == "10.1590/s0104-11692011000100002"
    )
    assert (
        normalize_doi("https://dx.doi.org/10.1590/S0104-11692011000100002")
        == "10.1590/s0104-11692011000100002"
    )
    assert normalize_doi("doi:10.1590/s0104") == "10.1590/s0104"
    assert normalize_doi(" 10.1590 / s0104 ") == "10.1590/s0104"


# --- normalize_title tests ---


def test_normalize_title_accented() -> None:
    assert (
        normalize_title("Análise Epidemiológica de Infecções")
        == "analise epidemiologica de infeccoes"
    )


def test_normalize_title_punctuation() -> None:
    assert normalize_title("COVID-19: A Study (2020)!") == "covid 19 a study 2020"


@pytest.mark.parametrize("val", [None, "", "   "])
def test_normalize_title_empty_or_none(val: str | None) -> None:
    assert normalize_title(val) == ""


def test_normalize_title_collapses_whitespace() -> None:
    assert normalize_title("  Title   with    spaces  ") == "title with spaces"


# --- normalize_author tests ---


def test_normalize_author_accented() -> None:
    assert normalize_author("Gonçalves, Á. M.") == "goncalves a m"


def test_normalize_author_punctuation() -> None:
    assert normalize_author("Silva, N.") == "silva n"


@pytest.mark.parametrize("val", [None, "", "   "])
def test_normalize_author_empty_or_none(val: str | None) -> None:
    assert normalize_author(val) == ""


def test_normalize_author_formats() -> None:
    assert normalize_author("Sobrenome, N") == "sobrenome n"
    assert normalize_author("Silva, João Maria") == "silva joao maria"
    assert normalize_author("João Silva") == "joao silva"


# --- blocking_key tests ---


def test_blocking_key_accented() -> None:
    article = Article(title="Éxito Escolar", authors=["Silva, N"], year=2020)
    assert blocking_key(article) == "2020exit"


def test_blocking_key_punctuation() -> None:
    article = Article(title="[COVID-19] Study", authors=["Silva, N"], year=2021)
    assert blocking_key(article) == "2021covi"


@pytest.mark.parametrize(
    "article",
    [
        None,
        Article(title=None, authors=[], year=None),
        Article(title="", authors=[], year=2022),
    ],
)
def test_blocking_key_empty_or_none(article: Article | None) -> None:
    assert blocking_key(article) in ("", "2022")


def test_blocking_key_short_title() -> None:
    article = Article(title="AI", authors=[], year=2023)
    assert blocking_key(article) == "2023ai"
