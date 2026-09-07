from pathlib import Path

import httpx
import pytest

from easyscielo.errors import ReviewError
from easyscielo.models import Article
from easyscielo.review import (
    ReviewProtocol,
    ScreeningCriteria,
    SystematicReview,
    prisma_counts,
)

pytest.importorskip("rapidfuzz")
pytest.importorskip("jinja2")


# A helper to read the search page fixture
def read_fixture(name: str) -> str:
    path = Path(__file__).parent.parent / "fixtures" / name
    return path.read_text(encoding="utf-8")


@pytest.fixture
def mock_scielo_transport(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        html = read_fixture("search_page.html")
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)

    import easyscielo.http

    original_client = easyscielo.http.httpx.Client

    def mock_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(easyscielo.http.httpx, "Client", mock_client)
    monkeypatch.setattr(easyscielo.http.HttpClient, "_apply_delay", lambda self: None)

    return transport


@pytest.fixture
def mock_openalex_pager(monkeypatch):
    import json

    def fake_pager(query, *args, **kwargs):
        path = Path(__file__).parent.parent / "fixtures" / "openalex_works.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        # OpenAlex API returns items in 'results' or as a list
        # based on pyalex behavior, let's yield items
        items = data.get("results", []) if isinstance(data, dict) else data
        for item in items:
            yield item

    monkeypatch.setattr("easyscielo.backends.openalex._pyalex_pager", fake_pager)


def test_pipeline_out_of_order():
    protocol = ReviewProtocol(sources=["search"], queries=["test"])
    pipeline = SystematicReview(protocol)

    with pytest.raises(ReviewError, match="Missing stage"):
        pipeline.deduplicate()

    pipeline.identify()

    with pytest.raises(ReviewError, match="Missing stage"):
        pipeline.screen()


def test_pipeline_run_end_to_end(mock_scielo_transport, mock_openalex_pager):
    protocol = ReviewProtocol(
        sources=["search", "openalex"],
        queries=["test query"],
        criteria=ScreeningCriteria(year_min=2020),
    )

    pipeline = SystematicReview(protocol)
    result = pipeline.run()

    assert len(result.corpus.records) > 0
    assert result.report is not None

    counts = prisma_counts(result.corpus)
    # Check that PRISMA discriminates both sources
    assert "search" in counts["identified"]
    assert "openalex" in counts["identified"]
    assert counts["identified"]["search"] > 0
    assert counts["identified"]["openalex"] > 0


def test_pipeline_identify_forwards_query_filters(monkeypatch):
    """Protocol query_filters must reach sources.iter_articles."""
    captured = {}

    def fake_iter_articles(query, *, sources=None, **kwargs):
        captured["query"] = query
        captured["sources"] = sources
        captured["filters"] = kwargs
        return iter([])

    monkeypatch.setattr("easyscielo.sources.iter_articles", fake_iter_articles)

    protocol = ReviewProtocol(
        sources=["search"],
        queries=["test query"],
        query_filters={"year_start": 2020, "collections": ["scl"]},
    )
    SystematicReview(protocol).identify()

    assert captured["filters"]["year_start"] == 2020
    assert captured["filters"]["collections"] == ["scl"]


def test_pipeline_identify_warns_on_unknown_filter(monkeypatch):
    """Unknown keys in query_filters are dropped with a warning, not an error."""
    monkeypatch.setattr(
        "easyscielo.sources.iter_articles",
        lambda query, *, sources=None, **kwargs: iter([]),
    )

    protocol = ReviewProtocol(
        sources=[],
        queries=[],
        query_filters={"nonsense_filter": 1},
    )
    with pytest.warns(UserWarning, match="nonsense_filter"):
        SystematicReview(protocol).identify()


def test_pipeline_report_includes_metrics_and_provenance():
    """With a gold standard, the report must show metrics and corpus_sha256."""
    from easyscielo.review.protocol import provenance

    art = Article(
        title="Relevant study",
        authors=["Silva, A."],
        year=2021,
        doi="10.1000/relevant",
        source="search",
    )
    protocol = ReviewProtocol(
        sources=[],
        queries=[],
        gold_standard=["10.1000/relevant"],
    )
    pipeline = SystematicReview(protocol)
    pipeline.add_source([art])
    result = pipeline.run()

    assert result.metrics is not None
    assert result.metrics.recall == 1.0
    assert result.report is not None
    assert "## Métricas" in result.report
    assert "SHA-256" in result.report
    assert provenance(result.corpus, protocol)["corpus_sha256"] in result.report


def test_pipeline_identify_sets_source_db(monkeypatch):
    """Records created by identify() carry source_db equal to the source name."""
    art = Article(title="Study", authors=["A"], year=2021, source="search")

    monkeypatch.setattr(
        "easyscielo.sources.iter_articles",
        lambda query, *, sources=None, **kwargs: iter([art]),
    )

    protocol = ReviewProtocol(sources=["search"], queries=["q"])
    pipeline = SystematicReview(protocol)
    pipeline.identify()

    assert all(r.source_db == "search" for r in pipeline.corpus.records)
