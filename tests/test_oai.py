"""Tests for OAI-PMH backend in easyscielo."""

import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from easyscielo.backends import get_backend
from easyscielo.backends.oai import OaiBackend, parse_oai_record
from easyscielo.http import HttpClient

FIXTURE_DIR = Path(__file__).parent / "fixtures"
OAI_FIXTURE_PATH = FIXTURE_DIR / "oai_listrecords.xml"


def test_oai_backend_init():
    """Test default and custom endpoint initialization for OaiBackend."""
    backend_default = OaiBackend()
    assert backend_default.name == "oai"
    assert backend_default.endpoint == "https://www.scielo.br/oai/scielo-oai.php"

    custom_url = "https://oai.custom.org/oai.php"
    backend_custom = OaiBackend(endpoint=custom_url)
    assert backend_custom.endpoint == custom_url


def test_get_backend_oai():
    """Test factory function get_backend for 'oai'."""
    backend = get_backend("oai")
    assert isinstance(backend, OaiBackend)
    assert backend.name == "oai"


def test_parse_oai_record_from_fixture():
    """Test parsing oai_dc fields from the XML fixture."""
    content = OAI_FIXTURE_PATH.read_text(encoding="utf-8")
    root = ET.fromstring(content)
    records = root.findall(".//{http://www.openarchives.org/OAI/2.0/}record")
    assert len(records) == 2

    # Record 1
    art1 = parse_oai_record(records[0])
    assert art1 is not None
    assert art1.title == "Epidemiological analysis of Dengue"
    assert art1.authors == ["Silva, Ana", "Santos, Carlos"]
    assert art1.year == 2023
    assert art1.doi == "10.1590/0102-311X00012323"
    assert (
        art1.abstract
        == "This study presents an epidemiological overview of dengue in urban areas."
    )
    assert art1.languages == ["en"]
    assert art1.pid == "S0102-311X2023000100200"

    # Record 2
    art2 = parse_oai_record(records[1])
    assert art2 is not None
    assert art2.title == "Public health strategies for vector control"
    assert art2.authors == ["Gomez, Maria", "Rodriguez, Juan"]
    assert art2.year == 2022
    assert art2.doi == "10.1590/S0034-89102022000100200"
    assert (
        art2.abstract
        == "An evaluation of vector control initiatives and public policy."
    )
    assert art2.languages == ["es"]


def test_doi_only_when_identifier_is_doi():
    """Test that DOI is extracted only when dc:identifier is a DOI format."""
    xml_non_doi = """
    <record xmlns="http://www.openarchives.org/OAI/2.0/">
        <header>
            <identifier>oai:scielo:S0000-00002021000100001</identifier>
        </header>
        <metadata>
            <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                       xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title>Test Non DOI Record</dc:title>
                <dc:creator>Author, Test</dc:creator>
                <dc:date>2021</dc:date>
                <dc:identifier>http://www.scielo.br/scielo.php?pid=S0000-00002021000100001</dc:identifier>
                <dc:identifier>oai:scielo:S0000-00002021000100001</dc:identifier>
            </oai_dc:dc>
        </metadata>
    </record>
    """
    rec_elem = ET.fromstring(xml_non_doi)
    art = parse_oai_record(rec_elem)
    assert art is not None
    assert art.doi is None

    xml_with_doi = """
    <record xmlns="http://www.openarchives.org/OAI/2.0/">
        <header>
            <identifier>oai:scielo:S0000-00002021000100002</identifier>
        </header>
        <metadata>
            <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                       xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title>Test DOI Record</dc:title>
                <dc:creator>Author, Test</dc:creator>
                <dc:date>2021</dc:date>
                <dc:identifier>http://www.scielo.br/scielo.php?pid=S0000-00002021000100002</dc:identifier>
                <dc:identifier>https://doi.org/10.1590/1234-5678.2021.001</dc:identifier>
            </oai_dc:dc>
        </metadata>
    </record>
    """
    rec_elem_doi = ET.fromstring(xml_with_doi)
    art_doi = parse_oai_record(rec_elem_doi)
    assert art_doi is not None
    assert art_doi.doi == "10.1590/1234-5678.2021.001"


def test_oai_backend_resumption_token_continuation():
    """Test pagination continuation via resumptionToken using MockTransport."""
    page1_xml = OAI_FIXTURE_PATH.read_text(encoding="utf-8")
    page2_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
             xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
             xmlns:dc="http://purl.org/dc/elements/1.1/">
        <responseDate>2026-09-07T02:05:00Z</responseDate>
        <request verb="ListRecords" resumptionToken="TOKEN_PAGE_2">https://www.scielo.br/oai/scielo-oai.php</request>
        <ListRecords>
            <record>
                <header>
                    <identifier>oai:scielo:S0100-00002020000100300</identifier>
                    <datestamp>2020-04-12</datestamp>
                </header>
                <metadata>
                    <oai_dc:dc>
                        <dc:title>Third Page Article</dc:title>
                        <dc:creator>Oliveira, Joao</dc:creator>
                        <dc:date>2020</dc:date>
                        <dc:identifier>10.1590/0100-00002020000100300</dc:identifier>
                    </oai_dc:dc>
                </metadata>
            </record>
            <resumptionToken cursor="2" completeListSize="3"></resumptionToken>
        </ListRecords>
    </OAI-PMH>
    """

    requested_params = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = request.url
        params = dict(url.params)
        requested_params.append(params)

        if params.get("verb") == "ListRecords":
            if "resumptionToken" in params:
                if params["resumptionToken"] == "TOKEN_PAGE_2":
                    assert "metadataPrefix" not in params
                    return httpx.Response(200, text=page2_xml)
            else:
                assert params.get("metadataPrefix") == "oai_dc"
                return httpx.Response(200, text=page1_xml)

        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = OaiBackend(client=client)

    articles = list(backend.search())

    assert len(requested_params) == 2
    assert requested_params[0] == {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
    assert requested_params[1] == {
        "verb": "ListRecords",
        "resumptionToken": "TOKEN_PAGE_2",
    }

    assert len(articles) == 3
    assert articles[0].title == "Epidemiological analysis of Dengue"
    assert articles[1].title == "Public health strategies for vector control"
    assert articles[2].title == "Third Page Article"


def test_oai_backend_from_until_set_params():
    """Test from, until, and set parameters sending in request."""
    requested_params = []

    empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
        <ListRecords>
        </ListRecords>
    </OAI-PMH>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        requested_params.append(dict(request.url.params))
        return httpx.Response(200, text=empty_xml)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = OaiBackend(client=client)

    list(
        backend.search(
            from_date="2022-01-01",
            until="2023-12-31",
            set_spec="0102-311X",
        )
    )

    assert len(requested_params) == 1
    assert requested_params[0] == {
        "verb": "ListRecords",
        "metadataPrefix": "oai_dc",
        "from": "2022-01-01",
        "until": "2023-12-31",
        "set": "0102-311X",
    }


def test_oai_backend_n_max_limit():
    """Test n_max limit stops yielding articles early."""
    page1_xml = OAI_FIXTURE_PATH.read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=page1_xml)

    transport = httpx.MockTransport(handler)
    client = HttpClient(transport=transport, delay=(0, 0))
    backend = OaiBackend(client=client)

    articles = list(backend.search(n_max=1))
    assert len(articles) == 1
    assert articles[0].title == "Epidemiological analysis of Dengue"
