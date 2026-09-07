import json
from typing import Iterator

import pytest

from easyscielo.backends.base import Backend
from easyscielo.cli import main
from easyscielo.errors import BlockedError
from easyscielo.models import Article, Query


class FakeBackend(Backend):
    """Fake backend for testing the CLI."""

    name = "fake"

    def search(
        self,
        query: Query,
        n_max: int = None,
        client=None,
    ) -> Iterator[Article]:
        if query.term == "error_blocked":
            raise BlockedError("SciELO search 403 Forbidden")

        yield Article(
            title=f"Article for {query.term}",
            authors=["Author 1", "Author 2"],
            year=query.year_start if query.year_start else 2020,
            doi="10.1590/fake-doi",
            abstract=f"Abstract for query {query.term} in {query.collections}",
        )


@pytest.fixture
def patch_backend(monkeypatch):
    fake = FakeBackend()
    import easyscielo.api

    def mock_get_backend(name: str):
        return fake

    monkeypatch.setattr(easyscielo.api, "get_backend", mock_get_backend)
    return fake


def test_cli_search_json_stdout(patch_backend, capsys):
    argv = [
        "search",
        "termo",
        "--backend",
        "fake",
        "--collection",
        "cri",
        "--language",
        "es",
        "--year-start",
        "2015",
        "--year-end",
        "2020",
        "--n-max",
        "20",
        "--format",
        "json",
    ]
    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 1
    assert data[0]["title"] == "Article for termo"
    assert data[0]["year"] == 2015
    assert "cri" in data[0]["abstract"]


def test_cli_search_csv_stdout(patch_backend, capsys):
    argv = [
        "search",
        "termo",
        "--backend",
        "fake",
        "--format",
        "csv",
    ]
    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "title,authors,year,doi,abstract" in captured.out
    assert "Article for termo" in captured.out


def test_cli_search_out_file_json(patch_backend, tmp_path):
    outfile = tmp_path / "result.json"
    argv = [
        "search",
        "termo",
        "--backend",
        "fake",
        "--format",
        "json",
        "--out",
        str(outfile),
    ]
    exit_code = main(argv)
    assert exit_code == 0

    assert outfile.exists()
    data = json.loads(outfile.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["title"] == "Article for termo"


def test_cli_search_out_file_csv(patch_backend, tmp_path):
    outfile = tmp_path / "result.csv"
    argv = [
        "search",
        "termo",
        "--backend",
        "fake",
        "--format",
        "csv",
        "--out",
        str(outfile),
    ]
    exit_code = main(argv)
    assert exit_code == 0

    assert outfile.exists()
    content = outfile.read_text(encoding="utf-8")
    assert "title,authors,year,doi,abstract" in content
    assert "Article for termo" in content


def test_cli_search_blocked_error(patch_backend, capsys):
    argv = [
        "search",
        "error_blocked",
        "--backend",
        "fake",
    ]
    exit_code = main(argv)
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "Blocked:" in captured.err
    assert "SciELO search 403 Forbidden" in captured.err


def test_cli_no_subcommand(capsys):
    exit_code = main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage: easyscielo" in captured.out
