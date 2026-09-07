"""Tests for filter normalizers."""

from datetime import datetime

import pytest

from easyscielo.errors import ValidationError
from easyscielo.filters import (
    normalize_categories,
    normalize_collections,
    normalize_journals,
    normalize_languages,
    normalize_n_max,
    normalize_nmax,
    normalize_years,
)

# ---- normalize_collections tests ----


def test_normalize_collections_valid_single():
    assert normalize_collections("Costa Rica") == ["cri"]
    assert normalize_collections("cri") == ["cri"]
    assert normalize_collections("MÉXICO") == ["mex"]
    assert normalize_collections("peru") == ["per"]


def test_normalize_collections_valid_multi():
    assert normalize_collections(["Costa Rica", "Brasil"]) == ["cri", "bra"]
    assert normalize_collections(("pan", "Chile")) == ["pan", "chl"]


def test_normalize_collections_invalid():
    with pytest.raises(ValidationError) as exc:
        normalize_collections("Canada")
    assert "Invalid collection: 'Canada'" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_collections("x")
    assert "too short" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_collections(123)
    assert "'collections' must be a character vector." in str(exc.value)


# ---- normalize_languages tests ----


def test_normalize_languages_valid_single():
    assert normalize_languages("EN") == ["en"]
    assert normalize_languages("pt") == ["pt"]


def test_normalize_languages_valid_multi():
    assert normalize_languages(["es", "PT"]) == ["es", "pt"]


def test_normalize_languages_invalid():
    with pytest.raises(ValidationError) as exc:
        normalize_languages("fr")
    assert "Invalid language code: 'fr'. Allowed values are: es, pt, en." in str(
        exc.value
    )

    with pytest.raises(ValidationError) as exc:
        normalize_languages(123)
    assert "The language code must be a character string." in str(exc.value)


# ---- normalize_journals tests ----


def test_normalize_journals_valid_single():
    assert normalize_journals("Revista Ambiente & Água") == ["Revista Ambiente & Água"]


def test_normalize_journals_valid_multi():
    assert normalize_journals(["Journal A", "Journal B"]) == ["Journal A", "Journal B"]


def test_normalize_journals_invalid():
    with pytest.raises(ValidationError) as exc:
        normalize_journals("a")
    assert "The journal name must be at least 2 characters long." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_journals(123)
    assert "The journal name must be a character string." in str(exc.value)


# ---- normalize_categories tests ----


def test_normalize_categories_valid_single():
    assert normalize_categories("environmental sciences") == ["environmental sciences"]


def test_normalize_categories_valid_multi():
    assert normalize_categories(["Category A", "Category B"]) == [
        "Category A",
        "Category B",
    ]


def test_normalize_categories_invalid():
    with pytest.raises(ValidationError) as exc:
        normalize_categories("x")
    assert "The subject category must be at least 2 characters long." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_categories(123)
    assert "The subject category must be a character string." in str(exc.value)


# ---- normalize_years tests ----


def test_normalize_years_valid():
    assert normalize_years(2018, 2022) == (2018, 2022)
    assert normalize_years("2018", "2022") == (2018, 2022)


def test_normalize_years_valid_none():
    assert normalize_years() == (None, None)
    assert normalize_years(None, None) == (None, None)


def test_normalize_years_invalid():
    with pytest.raises(ValidationError) as exc:
        normalize_years(2018, None)
    assert "Both 'start_year' and 'end_year' must be provided." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_years(2022, 2018)
    assert "'start_year' must be less than or equal to 'end_year'." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_years(1499, 2020)
    assert "'start_year' must be between 1500 and" in str(exc.value)

    current_year = datetime.now().year
    with pytest.raises(ValidationError) as exc:
        normalize_years(2020, current_year + 5)
    assert "'end_year' must be between 1500 and" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        normalize_years("abc", 2020)
    assert "'start_year' must be an integer number." in str(exc.value)


# ---- normalize_n_max tests ----


def test_normalize_n_max_valid():
    assert normalize_n_max(10) == 10
    assert normalize_n_max("10") == 10
    assert normalize_nmax(5) == 5


def test_normalize_n_max_valid_none():
    assert normalize_n_max(None) is None


def test_normalize_n_max_invalid():
    with pytest.raises(ValidationError) as exc:
        normalize_n_max(0)
    assert "The 'n_max' parameter must be a positive numeric value or NULL." in str(
        exc.value
    )

    with pytest.raises(ValidationError) as exc:
        normalize_n_max(-5)
    assert "The 'n_max' parameter must be a positive numeric value or NULL." in str(
        exc.value
    )

    with pytest.raises(ValidationError) as exc:
        normalize_n_max("abc")
    assert "The 'n_max' parameter must be a positive numeric value or NULL." in str(
        exc.value
    )

    with pytest.raises(ValidationError) as exc:
        normalize_n_max(True)
    assert "The 'n_max' parameter must be a positive numeric value or NULL." in str(
        exc.value
    )
