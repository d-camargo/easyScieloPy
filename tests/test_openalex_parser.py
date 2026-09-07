"""Tests for OpenAlex pure parser and mapper (invert_abstract, work_to_record)."""

import json
from pathlib import Path

from easyscielo.backends.openalex import invert_abstract, work_to_record
from easyscielo.models import Article


def test_invert_abstract_synthetic():
    """Test invert_abstract with synthetic dictionary, empty, and None inputs."""
    assert invert_abstract(None) is None
    assert invert_abstract({}) is None
    assert invert_abstract({"word": []}) is None

    index = {
        "fox": [3],
        "The": [0],
        "brown": [2],
        "quick": [1],
    }
    assert invert_abstract(index) == "The quick brown fox"


def test_openalex_fixture_parsing():
    """Test that all 5 records from openalex_works.json fixture parse into Article objects."""
    fixture_path = Path(__file__).parent / "fixtures" / "openalex_works.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    results = data["results"]

    assert len(results) == 5

    articles = [work_to_record(item) for item in results]

    assert len(articles) == 5
    for art in articles:
        assert isinstance(art, Article)
        assert art.source == "openalex"

    # Test inverted abstract reconstruction order on record 0
    art0 = articles[0]
    assert art0.abstract is not None
    assert art0.abstract.startswith("The process of implementing a")

    # Test work without abstract index gives abstract is None (record 2)
    art2 = articles[2]
    assert art2.abstract is None

    # Test DOI loses prefix https://doi.org/ (records 0 and 1)
    assert art0.doi == "10.1098/rsta.2006.1928"
    assert articles[1].doi == "10.1002/9781118443118"

    # Test work without DOI gives None (record 3 and 4)
    assert articles[3].doi is None
    assert articles[4].doi is None

    # Verify additional parsed fields on record 0
    assert art0.pid == "W2027456229"
    assert art0.url == "https://openalex.org/W2027456229"
    assert art0.year == 2006
    assert art0.authors == ["Charles R. Farrar", "Keith Worden"]
    assert art0.journal == (
        "Philosophical Transactions of the Royal Society A "
        "Mathematical Physical and Engineering Sciences"
    )
    assert art0.journal_issn == "1364-503X"
    assert art0.languages == ["en"]
    assert art0.categories == [
        "Structural Health Monitoring Techniques",
        "Non-Destructive Testing Techniques",
        "Concrete Corrosion and Durability",
    ]


def test_work_to_record_concepts_fallback():
    """Test that categories falls back to concepts if topics is empty or missing."""
    work = {
        "id": "https://openalex.org/W12345",
        "display_name": "Sample Title",
        "publication_year": 2023,
        "topics": [],
        "concepts": [
            {"display_name": "Computer Science"},
            {"display_name": "Artificial Intelligence"},
        ],
    }
    art = work_to_record(work)
    assert art.categories == ["Computer Science", "Artificial Intelligence"]


def test_work_to_record_missing_year():
    """Test that missing publication_year defaults to 0."""
    work = {"display_name": "No Year"}
    art = work_to_record(work)
    assert art.year == 0
