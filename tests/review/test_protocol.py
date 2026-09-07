"""Tests for review protocol specification, serialization, provenance, and credential isolation."""

import json
from datetime import datetime
from pathlib import Path

import pytest

import easyscielo
from easyscielo.models import Article, Query
from easyscielo.review.models import Corpus, Decision, ReviewRecord, Stage
from easyscielo.review.protocol import ReviewProtocol, compute_corpus_sha256, provenance
from easyscielo.review.screening import ScreeningCriteria


def test_review_protocol_defaults() -> None:
    protocol = ReviewProtocol()
    assert protocol.title == ""
    assert protocol.question == ""
    assert protocol.queries == []
    assert protocol.sources == []
    assert protocol.query_filters == {}
    assert isinstance(protocol.criteria, ScreeningCriteria)
    assert protocol.gold_standard == []


def test_review_protocol_custom_init() -> None:
    criteria = ScreeningCriteria(
        include_terms=["dengue", "zika"],
        exclude_terms=["covid"],
        year_min=2015,
        year_max=2023,
        languages=["en", "es"],
    )
    query_obj = Query(year_start=2015, year_end=2023, languages=["en", "es"])

    protocol = ReviewProtocol(
        title="Dengue Systematic Review",
        question="What is the efficacy of dengue vector control?",
        queries=["dengue AND vector", "zika AND mosquito"],
        sources=["search", "articlemeta", "openalex"],
        query_filters=query_obj,
        criteria=criteria,
        gold_standard=["10.1016/j.actatropica.2020.105432", "rec_123456"],
    )

    assert protocol.title == "Dengue Systematic Review"
    assert protocol.question == "What is the efficacy of dengue vector control?"
    assert protocol.queries == ["dengue AND vector", "zika AND mosquito"]
    assert protocol.sources == ["search", "articlemeta", "openalex"]
    assert protocol.query_filters["year_start"] == 2015
    assert protocol.criteria.year_min == 2015
    assert protocol.gold_standard == ["10.1016/j.actatropica.2020.105432", "rec_123456"]


def test_review_protocol_round_trip_json_file(tmp_path: Path) -> None:
    criteria = ScreeningCriteria(
        include_terms=["vaccine"],
        exclude_terms=["rat"],
        year_min=2020,
        year_max=2024,
        languages=["en"],
    )
    protocol = ReviewProtocol(
        title="Vaccine Efficacy Review",
        question="How effective are vaccines?",
        queries=["vaccine efficacy"],
        sources=["search", "crossref"],
        query_filters={"year_start": 2020, "year_end": 2024},
        criteria=criteria,
        gold_standard=["10.1234/5678"],
    )

    json_file = tmp_path / "protocol.json"
    protocol.to_json(json_file)

    assert json_file.exists()

    restored = ReviewProtocol.from_json(json_file)
    assert restored == protocol
    assert restored.title == protocol.title
    assert restored.question == protocol.question
    assert restored.queries == protocol.queries
    assert restored.sources == protocol.sources
    assert restored.query_filters == protocol.query_filters
    assert restored.criteria == protocol.criteria
    assert restored.gold_standard == protocol.gold_standard


def test_review_protocol_round_trip_json_str() -> None:
    criteria = ScreeningCriteria(include_terms=["health"])
    protocol = ReviewProtocol(
        title="Health Review",
        question="Public health impacts?",
        queries=["public health"],
        sources=["oai"],
        query_filters={"collections": ["bra"]},
        criteria=criteria,
        gold_standard=["id_999"],
    )

    json_str = protocol.to_json()
    assert isinstance(json_str, str)

    restored = ReviewProtocol.from_json(json_str)
    assert restored == protocol


def test_provenance_structure_and_values() -> None:
    art1 = Article(
        title="Article 1", authors=["A"], year=2020, doi="10.1/1", source="search"
    )
    art2 = Article(
        title="Article 2", authors=["B"], year=2021, doi="10.1/2", source="openalex"
    )
    art3 = Article(
        title="Article 3", authors=["C"], year=2022, doi="10.1/3", source="search"
    )

    r1 = ReviewRecord("rec001", art1, Stage.IDENTIFIED)
    r2 = ReviewRecord("rec002", art2, Stage.SCREENED, Decision.INCLUDE)
    r3 = ReviewRecord("rec003", art3, Stage.EXCLUDED, Decision.EXCLUDE)

    corpus = Corpus([r1, r2, r3])
    protocol = ReviewProtocol(title="Provenance Test Review")

    prov = provenance(corpus, protocol)

    assert isinstance(prov, dict)
    assert prov["easyscielo_version"] == easyscielo.__version__
    assert prov["easyscielo.__version__"] == easyscielo.__version__

    # Validate ISO-8601 UTC timestamp format
    ts_str = prov["timestamp_utc"]
    dt = datetime.fromisoformat(ts_str)
    assert dt is not None

    # Validate stage counts
    assert prov["stage_counts"]["IDENTIFIED"] == 1
    assert prov["stage_counts"]["SCREENED"] == 1
    assert prov["stage_counts"]["EXCLUDED"] == 1
    assert prov["stage_counts"]["DEDUPLICATED"] == 0

    # Validate source counts
    assert prov["source_counts"]["search"] == 2
    assert prov["source_counts"]["openalex"] == 1

    # Validate corpus sha256
    assert isinstance(prov["corpus_sha256"], str)
    assert len(prov["corpus_sha256"]) == 64


def test_corpus_sha256_order_independence() -> None:
    art1 = Article(title="Title A", authors=["Author A"], year=2020, doi="10.1000/a")
    art2 = Article(title="Title B", authors=["Author B"], year=2021, doi="10.1000/b")
    art3 = Article(title="Title C", authors=["Author C"], year=2022, doi="10.1000/c")

    r1 = ReviewRecord("rec_aaa", art1, Stage.IDENTIFIED)
    r2 = ReviewRecord("rec_bbb", art2, Stage.SCREENED)
    r3 = ReviewRecord("rec_ccc", art3, Stage.INCLUDED)

    corpus_order1 = Corpus([r1, r2, r3])
    corpus_order2 = Corpus([r3, r1, r2])
    corpus_order3 = Corpus([r2, r3, r1])

    hash1 = compute_corpus_sha256(corpus_order1)
    hash2 = compute_corpus_sha256(corpus_order2)
    hash3 = compute_corpus_sha256(corpus_order3)

    assert hash1 == hash2 == hash3

    protocol = ReviewProtocol(title="Order Test")
    prov1 = provenance(corpus_order1, protocol)
    prov2 = provenance(corpus_order2, protocol)

    assert prov1["corpus_sha256"] == prov2["corpus_sha256"]


def test_no_credentials_in_protocol_or_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requirement D20: No credentials enter protocol or provenance output."""
    secret_key = "super_secret_api_key_xyz987"
    secret_email = "confidential_user@example.com"
    secret_mailto = "mailto_secret@domain.org"

    monkeypatch.setenv("OPENALEX_API_KEY", secret_key)
    monkeypatch.setenv("OPENALEX_EMAIL", secret_email)
    monkeypatch.setenv("CROSSREF_MAILTO", secret_mailto)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws_secret_key_123")

    protocol = ReviewProtocol(
        title="Clean Review Protocol",
        question="Clean question?",
        queries=["query"],
        sources=["search", "openalex", "crossref"],
        query_filters={"year_start": 2020},
        criteria=ScreeningCriteria(include_terms=["health"]),
        gold_standard=["gold_1"],
    )

    art = Article(title="Title", authors=["Auth"], year=2020, source="openalex")
    rec = ReviewRecord("rec_100", art, Stage.IDENTIFIED)
    corpus = Corpus([rec])

    prot_dict = protocol.to_dict()
    prot_json = protocol.to_json()
    prov_dict = provenance(corpus, protocol)

    # Convert all representations to text for deep check
    prot_dict_str = json.dumps(prot_dict)
    prov_dict_str = json.dumps(prov_dict)

    sensitive_strings = [secret_key, secret_email, secret_mailto, "aws_secret_key_123"]
    for s in sensitive_strings:
        assert s not in prot_dict_str
        assert s not in prot_json
        assert s not in prov_dict_str

    sensitive_keys = ["api_key", "email", "mailto", "secret", "password", "token"]
    for k in sensitive_keys:
        assert k not in prot_dict
        assert k not in prov_dict
