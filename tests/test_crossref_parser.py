"""Tests for Crossref pure parser and mapper (item_to_record)."""

import json
from pathlib import Path

from easyscielo.backends.crossref import _clean_abstract, item_to_record
from easyscielo.models import Article


def test_clean_abstract_synthetic():
    """Test _clean_abstract with JATS tags, empty, and None inputs."""
    assert _clean_abstract(None) is None
    assert _clean_abstract("") is None
    assert _clean_abstract("   ") is None
    assert (
        _clean_abstract("<jats:p>Hello <jats:bold>world</jats:bold>!</jats:p>")
        == "Hello world!"
    )


def test_crossref_fixture_parsing():
    """Test parsing items from crossref_works.json fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "crossref_works.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["message"]["items"]

    assert len(items) == 5

    articles = [item_to_record(item) for item in items]

    assert len(articles) == 5
    for art in articles:
        assert isinstance(art, Article)
        assert art.source == "crossref"

    # Record 0: Full record with author given+family and author without given (fallback to name)
    art0 = articles[0]
    assert art0.title == "Structural health monitoring of bridges"
    assert art0.authors == ["Ana Silva", "IEEE Structural Health Committee"]
    assert art0.year == 2023
    assert art0.doi == "10.1016/j.ymssp.2023.100000"
    assert art0.pid == "10.1016/j.ymssp.2023.100000"
    assert art0.journal == "Mechanical Systems and Signal Processing"
    assert art0.journal_issn == "0888-3270"
    assert art0.categories == [
        "Mechanical Engineering",
        "Civil and Structural Engineering",
    ]
    assert (
        art0.abstract
        == "Structural health monitoring is critical for bridge maintenance."
    )

    # Record 1: Item without abstract
    art1 = articles[1]
    assert art1.abstract is None
    assert art1.authors == ["Maria Gomez"]

    # Record 2: Item without author key
    art2 = articles[2]
    assert art2.authors == []
    assert (
        art2.abstract
        == "Vibration analysis techniques for structural damage detection."
    )


def test_item_to_record_author_family_only():
    """Test author with family only (no given, no name)."""
    item = {"title": ["Test"], "author": [{"family": "Einstein"}]}
    art = item_to_record(item)
    assert art.authors == ["Einstein"]


def test_item_to_record_missing_issued_defaults_to_zero():
    """Test item without issued or date-parts defaults year to 0."""
    item = {"title": ["No Year"]}
    art = item_to_record(item)
    assert art.year == 0
