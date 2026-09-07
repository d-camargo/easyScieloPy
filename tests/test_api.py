import httpx
import pytest

from easyscielo import search_scielo, to_dataframe


def make_synthetic_page(total_hits: int, start_idx: int, count: int) -> str:
    html = f'<html><body><input id="TotalHits" value="{total_hits}"/>'
    for i in range(start_idx, start_idx + count):
        html += f"""
        <div class="item" id="art_{i}">
            <div class="title">Article Title {i}</div>
            <div class="authors">
                <a class="author">Author {i}</a>
            </div>
            <div class="source"><span>2020</span></div>
            <div class="DOIResults"><a href="https://doi.org/10.1000/{i}">doi</a></div>
            <div id="art_{i}_en">Abstract {i}</div>
        </div>
        """
    html += "</body></html>"
    return html


@pytest.fixture
def mock_transport(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        html = make_synthetic_page(total_hits=10, start_idx=1, count=10)
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)

    import easyscielo.http

    original_client = easyscielo.http.httpx.Client

    def mock_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(easyscielo.http.httpx, "Client", mock_client)

    # Also patch delay to be zero so tests run fast

    monkeypatch.setattr(easyscielo.http.HttpClient, "_apply_delay", lambda self: None)

    return transport


def test_example_1_simple_search(mock_transport):
    res = search_scielo("salud ambiental")
    assert len(res) == 10
    pytest.importorskip("pandas")
    df = to_dataframe(res)
    assert len(df) == 10


def test_example_2_n_max(mock_transport):
    res = search_scielo("salud ambiental", n_max=5)
    assert len(res) == 5


def test_example_3_collections_name(mock_transport):
    res = search_scielo("salud ambiental", collections="Ecuador")
    assert len(res) > 0


def test_example_4_collections_code(mock_transport):
    res = search_scielo("salud ambiental", collections="cri")
    assert len(res) > 0


def test_example_5_languages(mock_transport):
    res = search_scielo("salud ambiental", languages="es")
    assert len(res) > 0


def test_example_6_journals(mock_transport):
    res = search_scielo("salud ambiental", journals="Revista Ambiente & Agua")
    assert len(res) > 0


def test_example_7_categories(mock_transport):
    res = search_scielo("salud ambiental", categories="environmental sciences")
    assert len(res) > 0


def test_example_8_years(mock_transport):
    res = search_scielo("salud ambiental", year_start=2015, year_end=2020)
    assert len(res) > 0
