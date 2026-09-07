"""Tests for easyscielo.review.dedup module."""

import pytest

from easyscielo.models import Article
from easyscielo.review.dedup import DedupResult, deduplicate
from easyscielo.review.models import ReviewRecord, Stage, make_record_id

pytest.importorskip("rapidfuzz")


def test_deduplicate_doi_only() -> None:
    a1 = Article(
        title="Title One",
        authors=["Author A"],
        year=2020,
        doi="10.1590/s0104-11692011000100002",
        journal="Journal A",
    )
    a2 = Article(
        title="Different Title Two",
        authors=["Author B"],
        year=2021,
        doi="https://doi.org/10.1590/S0104-11692011000100002",
    )
    res = deduplicate([a1, a2])

    assert len(res.unique) == 1
    assert len(res.duplicates) == 1
    assert len(res.groups) == 1
    assert res.duplicates[0].duplicate_of == res.unique[0].record_id
    assert res.unique[0].article.doi == "10.1590/s0104-11692011000100002"


def test_deduplicate_title_accent_only() -> None:
    a1 = Article(
        title="Análise Epidemiológica de Infecções",
        authors=["Silva, J."],
        year=2020,
    )
    a2 = Article(
        title="Analise Epidemiologica de Infeccoes",
        authors=["Silva, J."],
        year=2020,
    )
    res = deduplicate([a1, a2])

    assert len(res.unique) == 1
    assert len(res.duplicates) == 1
    assert len(res.groups) == 1
    assert res.duplicates[0].duplicate_of == res.unique[0].record_id


def test_deduplicate_fuzzy_matching() -> None:
    a1 = Article(
        title="A Systematic Review of Public Health Interventions",
        authors=["Author A"],
        year=2020,
    )
    a2 = Article(
        title="A Systematic Review on Public Health Intervention",
        authors=["Author A"],
        year=2020,
    )
    res = deduplicate([a1, a2], threshold=0.90, fuzzy=True)

    assert len(res.unique) == 1
    assert len(res.duplicates) == 1
    assert len(res.groups) == 1
    assert res.duplicates[0].duplicate_of == res.unique[0].record_id


def test_deduplicate_distinct_pair_does_not_collapse() -> None:
    a1 = Article(
        title="Public Health in Brazil",
        authors=["Author A"],
        year=2020,
        doi="10.1000/111",
    )
    a2 = Article(
        title="Cardiology Advances in 2020",
        authors=["Author B"],
        year=2020,
        doi="10.1000/222",
    )
    res = deduplicate([a1, a2])

    assert len(res.unique) == 2
    assert len(res.duplicates) == 0
    assert len(res.groups) == 2
    assert res.unique[0].duplicate_of is None
    assert res.unique[1].duplicate_of is None


def test_deduplicate_openalex_and_crossref_collapse() -> None:
    # OpenAlex record has more filled fields
    a_openalex = Article(
        title="Study on COVID-19",
        authors=["Alice", "Bob"],
        year=2021,
        doi="10.1016/j.cell.2021.01.001",
        abstract="Full abstract text describing the experiment...",
        journal="Cell",
        collection="scl",
        pid="S0000",
        url="https://doi.org/10.1016/j.cell.2021.01.001",
        journal_issn="1234-5678",
        categories=["Medicine"],
        source="openalex",
    )
    # Crossref record has fewer filled fields
    a_crossref = Article(
        title="Study on COVID-19",
        authors=["Alice"],
        year=2021,
        doi="https://doi.org/10.1016/j.cell.2021.01.001",
        source="crossref",
    )

    r_crossref = ReviewRecord(
        record_id=make_record_id(a_crossref),
        article=a_crossref,
        stage=Stage.IDENTIFIED,
    )
    r_openalex = ReviewRecord(
        record_id=make_record_id(a_openalex),
        article=a_openalex,
        stage=Stage.IDENTIFIED,
    )

    # Pass in order where crossref is first
    res = deduplicate([r_crossref, r_openalex])

    assert len(res.unique) == 1
    assert len(res.duplicates) == 1
    # Canonical must be r_openalex because it has more fields
    assert res.unique[0].article.source == "openalex"
    assert res.duplicates[0].article.source == "crossref"
    assert res.duplicates[0].duplicate_of == res.unique[0].record_id


def test_deduplicate_fuzzy_false_skips_third_pass() -> None:
    a1 = Article(
        title="A Systematic Review of Public Health Interventions",
        authors=["Author A"],
        year=2020,
    )
    a2 = Article(
        title="A Systematic Review on Public Health Intervention",
        authors=["Author A"],
        year=2020,
    )
    res = deduplicate([a1, a2], fuzzy=False)

    assert len(res.unique) == 2
    assert len(res.duplicates) == 0
    assert len(res.groups) == 2


def test_deduplicate_empty_input() -> None:
    res = deduplicate([])
    assert isinstance(res, DedupResult)
    assert res.unique == []
    assert res.duplicates == []
    assert res.groups == []
