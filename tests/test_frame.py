import csv
import sys
from pathlib import Path

import pytest

from easyscielo.frame import to_csv, to_dataframe
from easyscielo.models import Article


@pytest.fixture
def sample_articles():
    return [
        Article(
            title="First Article",
            authors=["Author One", "Author Two"],
            year=2021,
            doi="10.1000/1",
            abstract="Abstract 1",
        ),
        Article(
            title="Second Article",
            authors=["Author Three"],
            year=2022,
            doi="10.1000/2",
            abstract="Abstract 2",
        ),
    ]


def test_to_csv_without_pandas(tmp_path: Path, sample_articles):
    csv_file = tmp_path / "articles.csv"
    to_csv(sample_articles, csv_file)

    assert csv_file.exists()

    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Column order comes from Article.as_dict(): the five R-parity
    # columns first, then the remaining schema fields
    expected_columns = list(sample_articles[0].as_dict().keys())
    assert reader.fieldnames == expected_columns
    assert reader.fieldnames[:5] == ["title", "authors", "year", "doi", "abstract"]

    assert len(rows) == 2
    assert rows[0]["title"] == "First Article"
    assert rows[0]["year"] == "2021"
    assert rows[0]["doi"] == "10.1000/1"
    assert rows[1]["title"] == "Second Article"


def test_to_csv_accepts_str_path(tmp_path: Path, sample_articles):
    csv_file_str = str(tmp_path / "articles_str.csv")
    to_csv(sample_articles, csv_file_str)

    assert Path(csv_file_str).exists()


def test_to_csv_empty_articles(tmp_path: Path):
    csv_file = tmp_path / "empty.csv"
    to_csv([], csv_file)

    assert csv_file.exists()

    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["title", "authors", "year", "doi", "abstract"]
        rows = list(reader)
        assert len(rows) == 0


def test_to_dataframe_with_pandas(sample_articles):
    pd = pytest.importorskip("pandas")

    df = to_dataframe(sample_articles)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns)[:5] == ["title", "authors", "year", "doi", "abstract"]
    assert df.iloc[0]["title"] == "First Article"
    assert df.iloc[0]["year"] == 2021


def test_to_dataframe_pandas_missing(monkeypatch, sample_articles):
    monkeypatch.setitem(sys.modules, "pandas", None)

    with pytest.raises(ImportError, match=r"pip install easyscielopy\[pandas\]"):
        to_dataframe(sample_articles)
