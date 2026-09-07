import json
from typing import Iterator, Optional
from unittest.mock import patch

from easyscielo.backends import _BACKENDS
from easyscielo.backends.base import Backend
from easyscielo.cli import main
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query


class FakeSourceOpenAlex(Backend):
    name = "fake_openalex"

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        yield Article(
            title=f"OpenAlex article for {query.term}",
            authors=["OpenAlex Author"],
            year=2021,
            source="fake_openalex",
        )


class FakeSourceCrossref(Backend):
    name = "fake_crossref"

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        yield Article(
            title=f"Crossref article for {query.term}",
            authors=["Crossref Author"],
            year=2022,
            source="fake_crossref",
        )


class FakeSourceMissingExtra(Backend):
    name = "fake_missing"

    def search(
        self,
        query: Query,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        raise ImportError(
            "pyalex is required for this feature. Please install it using 'pip install easyscielopy[openalex]'."
        )


def test_cli_sources_subcommand(capsys):
    exit_code = main(["sources"])
    assert exit_code == 0

    captured = capsys.readouterr()
    stdout = captured.out
    assert "openalex" in stdout
    assert "crossref" in stdout
    assert "search" in stdout
    assert "articlemeta" in stdout
    assert "oai" in stdout


def test_cli_search_repeated_source(capsys):
    with patch.dict(
        _BACKENDS,
        {"fake_openalex": FakeSourceOpenAlex, "fake_crossref": FakeSourceCrossref},
    ):
        argv = [
            "search",
            "dengue",
            "--source",
            "fake_openalex",
            "--source",
            "fake_crossref",
        ]
        exit_code = main(argv)
        assert exit_code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 2
        assert data[0]["source"] == "fake_openalex"
        assert data[0]["title"] == "OpenAlex article for dengue"
        assert data[1]["source"] == "fake_crossref"
        assert data[1]["title"] == "Crossref article for dengue"


def test_cli_search_conflict_source_and_backend(capsys):
    argv = ["search", "dengue", "--backend", "search", "--source", "openalex"]
    exit_code = main(argv)
    assert exit_code != 0

    captured = capsys.readouterr()
    assert "Error:" in captured.err or "Cannot" in captured.err


def test_cli_search_import_error_missing_extra(capsys):
    with patch.dict(_BACKENDS, {"fake_missing": FakeSourceMissingExtra}):
        argv = ["search", "dengue", "--source", "fake_missing"]
        exit_code = main(argv)
        assert exit_code == 2

        captured = capsys.readouterr()
        assert "ImportError:" in captured.err
        assert "pyalex is required for this feature" in captured.err
