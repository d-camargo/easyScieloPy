"""Script to capture and save raw HTML and JSON fixtures from SciELO APIs."""

import json
from pathlib import Path
from typing import Any

import httpx

from easyscielo.backends.search_html import build_search_url
from easyscielo.models import Query

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "search_page.html"
ARTICLEMETA_COLLECTIONS_FILE = FIXTURE_DIR / "articlemeta_collections.json"
ARTICLEMETA_IDENTIFIERS_FILE = FIXTURE_DIR / "articlemeta_identifiers.json"
ARTICLEMETA_ARTICLE_FILE = FIXTURE_DIR / "articlemeta_article.json"
OAI_LISTRECORDS_FILE = FIXTURE_DIR / "oai_listrecords.xml"

ARTICLEMETA_BASE_URL = "https://articlemeta.scielo.org/api/v1/"
OAI_BASE_URL = "https://www.scielo.br/oai/scielo-oai.php"

FALLBACK_HTML = """<!-- FIXTURE SINTÉTICA (regra D8): página mínima gerada à mão porque a rede estava indisponível na captura; reproduz a estrutura documentada de search.scielo.org. -->
<!DOCTYPE html>
<html>
<head>
    <title>SciELO Search Results</title>
</head>
<body>
    <div class="results">
        <div class="item" id="art-001">
            <strong class="title">Epidemiological analysis</strong>
            <div class="authors">
                <a class="author">Silva, Ana</a>;
                <a class="author">Santos, Carlos</a>
            </div>
            <div class="source">
                <span>Cadernos de Saude Publica</span>, <span>2023</span>
            </div>
            <div class="DOIResults">
                <a href="https://doi.org/10.1590/0102-311X00012323">
                    https://doi.org/10.1590/0102-311X00012323
                </a>
            </div>
            <div id="art-001_en" class="abstract">
                This study presents an epidemiological overview of disease patterns.
            </div>
        </div>
        <div class="item" id="art-002">
            <strong class="title">Public health strategies for vector control</strong>
            <div class="authors">
                <a class="author">Gomez, Maria</a>;
                <a class="author">Rodriguez, Juan</a>
            </div>
            <div class="source">
                <span>Revista de Saude Publica</span>, <span>2022</span>
            </div>
            <div class="DOIResults">
                <a href="https://doi.org/10.1590/S0034-89102022000100200">
                    https://doi.org/10.1590/S0034-89102022000100200
                </a>
            </div>
            <div id="art-002_en" class="abstract">
                An evaluation of vector control initiatives and public policy.
            </div>
        </div>
    </div>
</body>
</html>
"""

FALLBACK_ARTICLEMETA_COLLECTIONS = [
    {
        "acron": "scl",
        "code": "scl",
        "domain": "www.scielo.br",
        "name": {"en": "Brazil", "pt": "Brasil", "es": "Brasil"},
        "status": "certified",
    }
]

FALLBACK_ARTICLEMETA_IDENTIFIERS = {
    "meta": {
        "limit": 5,
        "offset": 0,
        "filter": {"collection": "scl", "code_title": "0102-311X"},
        "total": 1,
    },
    "objects": [
        {
            "code": "S0102-311X2001000300027",
            "collection": "scl",
            "processing_date": "2001-06-05",
        }
    ],
}

FALLBACK_ARTICLEMETA_ARTICLE = {
    "code": "S0102-311X2001000300027",
    "collection": "scl",
    "processing_date": "2001-06-05",
    "document_type": "research-article",
    "title": {"en": "Epidemiological analysis"},
    "authors": [{"given_names": "Ana", "surname": "Silva"}],
}

FALLBACK_OAI_LISTRECORDS = """<?xml version="1.0" encoding="UTF-8"?>
<!-- FIXTURE SINTÉTICA (regra D8): amostra mínima gerada à mão porque a rede estava indisponível na captura; reproduz a estrutura documentada do OAI-PMH ListRecords oai_dc. -->
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
         xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <responseDate>2026-09-07T02:00:00Z</responseDate>
    <request verb="ListRecords" metadataPrefix="oai_dc">https://www.scielo.br/oai/scielo-oai.php</request>
    <ListRecords>
        <record>
            <header>
                <identifier>oai:scielo:S0102-311X2023000100200</identifier>
                <datestamp>2023-01-15</datestamp>
                <setSpec>0102-311X</setSpec>
            </header>
            <metadata>
                <oai_dc:dc>
                    <dc:title>Epidemiological analysis of Dengue</dc:title>
                    <dc:creator>Silva, Ana</dc:creator>
                    <dc:creator>Santos, Carlos</dc:creator>
                    <dc:date>2023-01-15</dc:date>
                    <dc:identifier>http://www.scielo.br/scielo.php?script=sci_arttext&amp;pid=S0102-311X2023000100200</dc:identifier>
                    <dc:identifier>https://doi.org/10.1590/0102-311X00012323</dc:identifier>
                    <dc:description>This study presents an epidemiological overview of dengue in urban areas.</dc:description>
                    <dc:language>en</dc:language>
                </oai_dc:dc>
            </metadata>
        </record>
        <record>
            <header>
                <identifier>oai:scielo:S0034-89102022000100200</identifier>
                <datestamp>2022-05-10</datestamp>
                <setSpec>0034-8910</setSpec>
            </header>
            <metadata>
                <oai_dc:dc>
                    <dc:title>Public health strategies for vector control</dc:title>
                    <dc:creator>Gomez, Maria</dc:creator>
                    <dc:creator>Rodriguez, Juan</dc:creator>
                    <dc:date>2022</dc:date>
                    <dc:identifier>10.1590/S0034-89102022000100200</dc:identifier>
                    <dc:identifier>oai:scielo:S0034-89102022000100200</dc:identifier>
                    <dc:description>An evaluation of vector control initiatives and public policy.</dc:description>
                    <dc:language>es</dc:language>
                </oai_dc:dc>
            </metadata>
        </record>
        <resumptionToken cursor="0" completeListSize="100">TOKEN_PAGE_2</resumptionToken>
    </ListRecords>
</OAI-PMH>
"""


def capture_search_fixture() -> Path:
    """Fetch search result page from SciELO or save fallback fixture under Rule D8."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    url = build_search_url(Query(term="epidemiology"), from_idx=1, count=10)

    html_content = None
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and "item" in resp.text:
                html_content = resp.text
            else:
                print(
                    f"Warning: HTTP request returned status {resp.status_code} "
                    "or unexpected content. Using fallback fixture (Rule D8)."
                )
    except Exception as err:
        print(
            f"Warning: Network error fetching {url} ({err}). "
            "Using fallback fixture (Rule D8)."
        )

    if not html_content:
        html_content = FALLBACK_HTML

    FIXTURE_FILE.write_text(html_content, encoding="utf-8")
    print(f"Search fixture saved to {FIXTURE_FILE}")
    return FIXTURE_FILE


def capture_articlemeta_fixtures(
    collection: str = "scl", issn: str = "0102-311X"
) -> dict[str, Path]:
    """Fetch ArticleMeta sample responses or save fallback fixtures under Rule D8."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "easyscielopy/0.1.0"}

    collections_data: Any = None
    identifiers_data: Any = None
    article_data: Any = None

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            # 1. collection/identifiers/
            col_url = f"{ARTICLEMETA_BASE_URL}collection/identifiers/"
            col_resp = client.get(col_url, headers=headers)
            if col_resp.status_code == 200:
                collections_data = col_resp.json()

            # 2. article/identifiers/?collection=<col>&issn=<issn>&limit=5
            ids_url = (
                f"{ARTICLEMETA_BASE_URL}article/identifiers/"
                f"?collection={collection}&issn={issn}&limit=5"
            )
            ids_resp = client.get(ids_url, headers=headers)
            if ids_resp.status_code == 200:
                identifiers_data = ids_resp.json()

            pid = "S0102-311X2001000300027"
            if (
                isinstance(identifiers_data, dict)
                and "objects" in identifiers_data
                and identifiers_data["objects"]
            ):
                first_obj = identifiers_data["objects"][0]
                if isinstance(first_obj, dict):
                    pid = first_obj.get("code", pid)

            # 3. article/?collection=<col>&code=<pid>
            art_url = (
                f"{ARTICLEMETA_BASE_URL}article/?collection={collection}&code={pid}"
            )
            art_resp = client.get(art_url, headers=headers)
            if art_resp.status_code == 200:
                article_data = art_resp.json()
    except Exception as err:
        print(
            f"Warning: Network error fetching ArticleMeta endpoints ({err}). "
            "Using fallback fixtures (Rule D8)."
        )

    if not collections_data:
        collections_data = FALLBACK_ARTICLEMETA_COLLECTIONS
    if not identifiers_data:
        identifiers_data = FALLBACK_ARTICLEMETA_IDENTIFIERS
    if not article_data:
        article_data = FALLBACK_ARTICLEMETA_ARTICLE

    ARTICLEMETA_COLLECTIONS_FILE.write_text(
        json.dumps(collections_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ARTICLEMETA_IDENTIFIERS_FILE.write_text(
        json.dumps(identifiers_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    ARTICLEMETA_ARTICLE_FILE.write_text(
        json.dumps(article_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"ArticleMeta fixtures saved to {FIXTURE_DIR}")
    return {
        "collections": ARTICLEMETA_COLLECTIONS_FILE,
        "identifiers": ARTICLEMETA_IDENTIFIERS_FILE,
        "article": ARTICLEMETA_ARTICLE_FILE,
    }


def capture_oai_fixture() -> Path:
    """Fetch OAI ListRecords sample response or save fallback fixture under Rule D8."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{OAI_BASE_URL}?verb=ListRecords&metadataPrefix=oai_dc"
    xml_content = None

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200 and "ListRecords" in resp.text:
                xml_content = resp.text
            else:
                print(
                    f"Warning: HTTP request returned status {resp.status_code} "
                    "or unexpected content. Using fallback fixture (Rule D8)."
                )
    except Exception as err:
        print(
            f"Warning: Network error fetching {url} ({err}). "
            "Using fallback fixture (Rule D8)."
        )

    if not xml_content:
        xml_content = FALLBACK_OAI_LISTRECORDS

    OAI_LISTRECORDS_FILE.write_text(xml_content, encoding="utf-8")
    print(f"OAI ListRecords fixture saved to {OAI_LISTRECORDS_FILE}")
    return OAI_LISTRECORDS_FILE


if __name__ == "__main__":
    capture_search_fixture()
    capture_articlemeta_fixtures()
    capture_oai_fixture()
