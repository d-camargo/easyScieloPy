import pytest

from easyscielo.models import Article
from easyscielo.review.metrics import Confusion, SearchMetrics
from easyscielo.review.models import Corpus, ReviewRecord, Stage
from easyscielo.review.prisma import prisma_counts
from easyscielo.review.protocol import ReviewProtocol, provenance
from easyscielo.review.report import render_report

pytest.importorskip("jinja2")


@pytest.fixture
def sample_corpus():
    art1 = Article(
        title="Vacina A", year=2021, doi="10.1000/a", source="search", authors=["Silva"]
    )
    art2 = Article(
        title="Vacina B",
        year=2022,
        doi="10.1000/b",
        source="search",
        authors=["Santos"],
    )
    art3 = Article(
        title="Vacina C", year=2021, doi="10.1000/c", source="oai", authors=["Oliveira"]
    )

    rec1 = ReviewRecord(record_id="rec1", article=art1, stage=Stage.INCLUDED)
    rec2 = ReviewRecord(
        record_id="rec2",
        article=art2,
        stage=Stage.EXCLUDED,
        decision_reason="fora do escopo",
    )
    rec3 = ReviewRecord(record_id="rec3", article=art3, stage=Stage.INCLUDED)

    return Corpus(records=[rec1, rec2, rec3])


@pytest.fixture
def sample_protocol():
    return ReviewProtocol(
        title="Revisão sobre Vacinas COVID-19",
        question="Qual a eficácia das vacinas?",
        queries=["vacina AND covid"],
        sources=["search", "oai"],
    )


def test_render_report_markdown_full(sample_corpus, sample_protocol):
    counts = prisma_counts(sample_corpus)
    prov = provenance(sample_corpus, sample_protocol)
    metrics = SearchMetrics(
        precision=0.8,
        recall=0.9,
        f1=0.847,
        confusion=Confusion(tp=8, fp=2, fn=1, tn=90),
    )

    report_md = render_report(
        corpus=sample_corpus,
        counts=counts,
        metrics=metrics,
        protocol=sample_protocol,
        provenance=prov,
        fmt="md",
    )

    # Check protocol title
    assert "Revisão sobre Vacinas COVID-19" in report_md
    assert "Qual a eficácia das vacinas?" in report_md

    # Check PRISMA numbers
    assert "Total Identificado:" in report_md
    assert str(counts["total_identified"]) in report_md
    assert str(counts["included"]) in report_md

    # Check Mermaid diagram
    assert "flowchart TD" in report_md

    # Check corpus_sha256 in provenance
    assert "SHA-256 do Corpus:" in report_md
    assert prov["corpus_sha256"] in report_md

    # Check metrics section
    assert "## Métricas" in report_md
    assert "0.8000" in report_md
    assert "0.9000" in report_md


def test_render_report_without_metrics(sample_corpus, sample_protocol):
    counts = prisma_counts(sample_corpus)
    prov = provenance(sample_corpus, sample_protocol)

    report_md = render_report(
        corpus=sample_corpus,
        counts=counts,
        metrics=None,
        protocol=sample_protocol,
        provenance=prov,
        fmt="md",
    )

    # Check protocol title, PRISMA numbers, and corpus_sha256
    assert "Revisão sobre Vacinas COVID-19" in report_md
    assert "Total Identificado:" in report_md
    assert prov["corpus_sha256"] in report_md

    # Check metrics section is NOT present
    assert "## Métricas" not in report_md


def test_render_report_html(sample_corpus, sample_protocol):
    counts = prisma_counts(sample_corpus)
    prov = provenance(sample_corpus, sample_protocol)
    metrics = SearchMetrics(precision=0.75, recall=0.85, f1=0.796)

    report_html = render_report(
        corpus=sample_corpus,
        counts=counts,
        metrics=metrics,
        protocol=sample_protocol,
        provenance=prov,
        fmt="html",
    )

    assert "<!DOCTYPE html>" in report_html
    assert "Revisão sobre Vacinas COVID-19" in report_html
    assert str(counts["total_identified"]) in report_html
    assert prov["corpus_sha256"] in report_html
    assert '<section id="metrics">' in report_html


def test_render_report_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported format"):
        render_report(fmt="docx")


def test_render_report_omits_none_sections():
    report_md = render_report(
        corpus=None,
        counts=None,
        metrics=None,
        protocol=None,
        provenance=None,
        fmt="md",
    )

    assert "## Protocolo" not in report_md
    assert "## Fluxo PRISMA" not in report_md
    assert "## Métricas" not in report_md
    assert "## Cobertura" not in report_md
    assert "## Proveniência" not in report_md
    assert "# Relatório de Revisão Sistemática" in report_md


def test_render_report_missing_jinja2(monkeypatch):
    def mock_require(module, extra):
        raise ImportError("jinja2 is required for this feature")

    monkeypatch.setattr("easyscielo.review.report.require", mock_require)

    with pytest.raises(ImportError, match="jinja2 is required"):
        render_report()
