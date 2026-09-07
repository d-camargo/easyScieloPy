"""Tests for easyscielo review CLI subcommands."""

import json

import pytest

from easyscielo.cli import main
from easyscielo.errors import ReviewError
from easyscielo.models import Article

pytest.importorskip("rapidfuzz")
pytest.importorskip("jinja2")
pytest.importorskip("rispy")


def test_cli_review_no_subcommand(capsys):
    """Verify 'easyscielo review' without subcommands prints help and exits with 0."""
    exit_code = main(["review"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage: easyscielo" in captured.out or "review" in captured.out


def test_cli_review_run_minimal_protocol(tmp_path):
    """Verify 'easyscielo review run' creates required 5 output files."""
    proto_data = {
        "title": "Minimal Review Protocol",
        "question": "What is the effect of X on Y?",
        "queries": ["test query"],
        "sources": [],
        "query_filters": {},
        "criteria": {
            "include_terms": [],
            "exclude_terms": [],
        },
        "gold_standard": [],
    }
    proto_path = tmp_path / "protocolo.json"
    proto_path.write_text(json.dumps(proto_data, indent=2), encoding="utf-8")

    out_dir = tmp_path / "out"

    argv = [
        "review",
        "run",
        "--protocol",
        str(proto_path),
        "--out-dir",
        str(out_dir),
    ]

    exit_code = main(argv)
    assert exit_code == 0

    assert (out_dir / "corpus.csv").exists()
    assert (out_dir / "included.ris").exists()
    assert (out_dir / "prisma.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "provenance.json").exists()

    prisma = json.loads((out_dir / "prisma.json").read_text(encoding="utf-8"))
    assert "total_identified" in prisma

    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance.get("protocol_title") == "Minimal Review Protocol"


def test_cli_review_run_with_mocked_articles(tmp_path, monkeypatch):
    """Verify 'easyscielo review run' populates files when articles are found."""
    art1 = Article(
        title="Study on SciELO search",
        authors=["Silva, A."],
        year=2021,
        doi="10.1590/11111",
        source="search",
    )
    art2 = Article(
        title="Study on SciELO search",
        authors=["Silva, A."],
        year=2021,
        doi="10.1590/11111",
        source="search",
    )

    def mock_iter_articles(query, sources=None, **kwargs):
        yield art1
        yield art2

    monkeypatch.setattr("easyscielo.sources.iter_articles", mock_iter_articles)

    proto_data = {
        "title": "Search Protocol",
        "queries": ["query"],
        "sources": ["search"],
    }
    proto_path = tmp_path / "protocol.json"
    proto_path.write_text(json.dumps(proto_data), encoding="utf-8")

    out_dir = tmp_path / "review_out"
    argv = [
        "review",
        "run",
        "--protocol",
        str(proto_path),
        "--out-dir",
        str(out_dir),
    ]

    exit_code = main(argv)
    assert exit_code == 0

    csv_content = (out_dir / "corpus.csv").read_text(encoding="utf-8")
    assert "Study on SciELO search" in csv_content


def test_cli_review_dedup_csv(tmp_path):
    """Verify 'easyscielo review dedup' deduplicates a standalone CSV file."""
    csv_content = (
        "title,authors,year,doi,abstract,collection,source\n"
        'Article One,["Author A"],2020,10.1590/0001,Abstract 1,col,source1\n'
        'Article One,["Author A"],2020,10.1590/0001,Abstract 1,col,source2\n'
        'Article Two,["Author B"],2021,10.1590/0002,Abstract 2,col,source1\n'
    )
    in_file = tmp_path / "entrada.csv"
    in_file.write_text(csv_content, encoding="utf-8")

    out_file = tmp_path / "saida.csv"
    argv = ["review", "dedup", str(in_file), "--out", str(out_file)]

    exit_code = main(argv)
    assert exit_code == 0

    assert out_file.exists()
    res_content = out_file.read_text(encoding="utf-8")
    assert "Article One" in res_content
    assert "Article Two" in res_content
    lines = [line for line in res_content.strip().splitlines() if line]
    assert len(lines) == 3


def test_cli_review_metrics(tmp_path, capsys):
    """Verify 'easyscielo review metrics' prints the evaluation table."""
    csv_content = (
        "title,authors,year,doi,abstract,collection,source\n"
        'Article Alpha,["Author A"],2020,10.1590/alpha,Abstract 1,col,source1\n'
        'Article Beta,["Author B"],2021,10.1590/beta,Abstract 2,col,source1\n'
    )
    corpus_file = tmp_path / "corpus.csv"
    corpus_file.write_text(csv_content, encoding="utf-8")

    gold_file = tmp_path / "gold.txt"
    gold_file.write_text("10.1590/alpha\n", encoding="utf-8")

    argv = [
        "review",
        "metrics",
        str(corpus_file),
        "--gold",
        str(gold_file),
    ]

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "| Métrica | Valor |" in captured.out
    assert "Precisão" in captured.out
    assert "Recall" in captured.out
    assert "F1" in captured.out
    assert "TP" in captured.out


def test_cli_review_error_handling_review_error(monkeypatch, capsys, tmp_path):
    """Verify ReviewError yields exit code 2 and short error message."""
    proto_data = {"title": "Error Proto", "queries": ["test"], "sources": []}
    proto_path = tmp_path / "proto_err.json"
    proto_path.write_text(json.dumps(proto_data), encoding="utf-8")

    def mock_run(self):
        raise ReviewError("Pipeline out of order or invalid configuration")

    monkeypatch.setattr("easyscielo.review.pipeline.SystematicReview.run", mock_run)

    argv = [
        "review",
        "run",
        "--protocol",
        str(proto_path),
        "--out-dir",
        str(tmp_path / "out_err"),
    ]

    exit_code = main(argv)
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "ReviewError: Pipeline out of order or invalid configuration" in captured.err


def test_cli_review_error_handling_import_error(monkeypatch, capsys, tmp_path):
    """Verify missing extra ImportError yields exit code 2 and short error message."""
    proto_data = {"title": "Import Error Proto", "queries": ["test"], "sources": []}
    proto_path = tmp_path / "proto_imp.json"
    proto_path.write_text(json.dumps(proto_data), encoding="utf-8")

    def mock_run(self):
        raise ImportError("No module named 'rispy'. Install extra 'review'.")

    monkeypatch.setattr("easyscielo.review.pipeline.SystematicReview.run", mock_run)

    argv = [
        "review",
        "run",
        "--protocol",
        str(proto_path),
        "--out-dir",
        str(tmp_path / "out_imp"),
    ]

    exit_code = main(argv)
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "ImportError: No module named 'rispy'" in captured.err
