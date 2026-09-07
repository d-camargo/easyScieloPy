"""Tests for SciELO ArticleMeta backend and article mapper."""

import json
from pathlib import Path

import httpx

from easyscielo.backends.articlemeta import ArticleMetaBackend, article_to_record
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query


def test_article_to_record_with_fixture():
    """Test article_to_record mapper against tests/fixtures/articlemeta_article.json."""
    fixture_path = Path(__file__).parent / "fixtures" / "articlemeta_article.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    article = article_to_record(payload)

    expected_title = (
        "Adiestramiento en el diagnóstico de las parasitosis "
        "intestinales en la red de laboratorios de Cuba"
    )
    assert isinstance(article, Article)
    assert article.title == expected_title
    assert article.authors == ["Fidel Angel Núñez", "Carlos M. Finlay"]
    assert article.year == 2001
    assert article.doi is None
    assert article.abstract is not None
    assert article.abstract.startswith("A national training project")
    assert article.journal == "Cad. Saúde Pública"
    assert article.collection == "scl"
    assert article.pid == "S0102-311X2001000300027"
    assert article.languages == ["es"]


def test_articlemeta_backend_pagination():
    """Test ArticleMetaBackend pagination by offset with MockTransport."""
    page1_ids = {
        "meta": {"total": 3, "offset": 0, "limit": 2},
        "objects": [
            {"code": "P001", "collection": "scl"},
            {"code": "P002", "collection": "scl"},
        ],
    }
    page2_ids = {
        "meta": {"total": 3, "offset": 2, "limit": 2},
        "objects": [
            {"code": "P003", "collection": "scl"},
        ],
    }

    article_payloads = {
        "P001": {
            "code": "P001",
            "collection": "scl",
            "publication_year": 2020,
            "article": {
                "v12": [{"_": "Article Title 1"}],
                "v10": [{"s": "Doe", "n": "John"}],
                "v30": [{"_": "Journal One"}],
                "v35": [{"_": "0102-311X"}],
            },
        },
        "P002": {
            "code": "P002",
            "collection": "scl",
            "publication_year": 2021,
            "article": {
                "v12": [{"_": "Article Title 2"}],
                "v10": [{"s": "Smith", "n": "Jane"}],
                "v30": [{"_": "Journal Two"}],
                "v35": [{"_": "0102-311X"}],
            },
        },
        "P003": {
            "code": "P003",
            "collection": "scl",
            "publication_year": 2022,
            "article": {
                "v12": [{"_": "Article Title 3"}],
                "v10": [{"s": "Lee", "n": "Alice"}],
                "v30": [{"_": "Journal Three"}],
                "v35": [{"_": "0102-311X"}],
            },
        },
    }

    requests_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        requests_made.append(url_str)

        if "/article/identifiers/" in url_str:
            if "offset=0" in url_str:
                return httpx.Response(200, json=page1_ids)
            elif "offset=2" in url_str:
                return httpx.Response(200, json=page2_ids)
            return httpx.Response(
                200, json={"meta": {"total": 3, "offset": 3, "limit": 2}, "objects": []}
            )
        elif "/article/?" in url_str or "/article?" in url_str:
            for code, payload in article_payloads.items():
                if f"code={code}" in url_str:
                    return httpx.Response(200, json=payload)

        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))

    backend = ArticleMetaBackend(client=client)
    articles = list(
        backend.search(
            Query(term="", collections=["scl"], journals=["0102-311X"]),
            n_max=None,
        )
    )

    assert len(articles) == 3
    assert articles[0].title == "Article Title 1"
    assert articles[0].authors == ["John Doe"]
    assert articles[0].pid == "P001"
    assert articles[1].title == "Article Title 2"
    assert articles[2].title == "Article Title 3"

    # Check identifier requests were paginated
    id_requests = [r for r in requests_made if "/article/identifiers/" in r]
    assert len(id_requests) == 2
    assert "offset=0" in id_requests[0]
    assert "offset=2" in id_requests[1]
    assert "collection=scl" in id_requests[0]
    assert "issn=0102-311X" in id_requests[0]


def test_articlemeta_backend_n_max_truncation():
    """Test that n_max parameter truncates fetching at specified limit."""
    page1_ids = {
        "meta": {"total": 10, "offset": 0, "limit": 50},
        "objects": [{"code": f"P{i:03d}", "collection": "scl"} for i in range(1, 6)],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/article/identifiers/" in url_str:
            return httpx.Response(200, json=page1_ids)
        elif "/article/?" in url_str or "/article?" in url_str:
            for i in range(1, 6):
                code = f"P{i:03d}"
                if f"code={code}" in url_str:
                    payload = {
                        "code": code,
                        "collection": "scl",
                        "publication_year": 2020,
                        "article": {
                            "v12": [{"_": f"Test Title {i}"}],
                            "v10": [{"s": f"Author{i}", "n": "Test"}],
                        },
                    }
                    return httpx.Response(200, json=payload)
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))

    backend = ArticleMetaBackend(client=client)
    articles = list(backend.search(Query(term="test", collection="scl"), n_max=2))

    assert len(articles) == 2
    assert articles[0].title == "Test Title 1"
    assert articles[1].title == "Test Title 2"
