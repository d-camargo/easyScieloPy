import httpx
import pytest

from easyscielo.backends.search_html import SearchBackend
from easyscielo.http import HttpClient
from easyscielo.models import Query


def make_synthetic_page(total_hits: int, start_idx: int, count: int) -> str:
    html = f'<html><body><input id="TotalHits" value="{total_hits}"/>'
    for i in range(start_idx, start_idx + count):
        html += f"""
        <div class="item" id="art_{i}">
            <div class="title">Article Title {i}</div>
            <div class="authors">
                <a class="author">Author {i}</a>
            </div>
            <div class="source"><span>2023</span></div>
            <div class="DOIResults"><a href="https://doi.org/10.1000/{i}">doi</a></div>
            <div id="art_{i}_en">Abstract {i}</div>
        </div>
        """
    html += "</body></html>"
    return html


def test_search_n_max_none_fetches_total_announced():
    """Test that n_max=None discovers #TotalHits and fetches all announced articles."""
    page1 = make_synthetic_page(total_hits=35, start_idx=1, count=15)
    page2 = make_synthetic_page(total_hits=35, start_idx=16, count=15)
    page3 = make_synthetic_page(total_hits=35, start_idx=31, count=5)

    requests_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        requests_made.append(url_str)
        if "from=1&" in url_str or "page=1" in url_str:
            return httpx.Response(200, text=page1)
        elif "from=16" in url_str or "page=2" in url_str:
            return httpx.Response(200, text=page2)
        elif "from=31" in url_str or "page=3" in url_str:
            return httpx.Response(200, text=page3)
        return httpx.Response(200, text="<html><body></body></html>")

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))

    backend = SearchBackend(client=client)
    articles = list(backend.search(Query(term="python"), n_max=None))

    assert len(articles) == 35
    assert articles[0].title == "Article Title 1"
    assert articles[34].title == "Article Title 35"
    assert len(requests_made) == 3


def test_search_n_max_7_truncates_at_7():
    """Test that n_max=7 stops after 7 items without fetching unnecessary pages."""
    page1 = make_synthetic_page(total_hits=35, start_idx=1, count=15)

    requests_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_made.append(str(request.url))
        return httpx.Response(200, text=page1)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))

    backend = SearchBackend(client=client)
    articles = list(backend.search(Query(term="python"), n_max=7))

    assert len(articles) == 7
    assert articles[0].title == "Article Title 1"
    assert articles[6].title == "Article Title 7"
    assert len(requests_made) == 1


def test_search_empty_page_in_middle_ends_gracefully():
    """Test that an empty page in the middle triggers retry and then stops gracefully."""
    page1 = make_synthetic_page(total_hits=35, start_idx=1, count=15)
    empty_page = "<html><body><input id='TotalHits' value='35'/></body></html>"

    requests_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        requests_made.append(url_str)
        if "from=1&" in url_str or "page=1" in url_str:
            return httpx.Response(200, text=page1)
        return httpx.Response(200, text=empty_page)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))

    backend = SearchBackend(client=client)
    articles = list(backend.search(Query(term="python"), n_max=None))

    assert len(articles) == 15
    # Initial page 1 (1) + page 2 initial (1) + page 2 retry (1) = 3 requests
    assert len(requests_made) == 3


def test_search_warning_when_total_hits_missing():
    """Test warning and fallback to 100 when #TotalHits cannot be found."""
    page1_no_hits = """<html><body>
        <div class="item" id="art_1">
            <div class="title">Article Title 1</div>
            <div class="authors"><a class="author">Author 1</a></div>
            <div class="source"><span>2023</span></div>
        </div>
    </body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "from=1&" in url_str or "page=1" in url_str:
            return httpx.Response(200, text=page1_no_hits)
        return httpx.Response(200, text="<html><body></body></html>")

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))

    backend = SearchBackend(client=client)
    with pytest.warns(
        UserWarning, match="Could not determine total hits. Defaulting to 100."
    ):
        articles = list(backend.search(Query(term="python"), n_max=None))

    assert len(articles) == 1
