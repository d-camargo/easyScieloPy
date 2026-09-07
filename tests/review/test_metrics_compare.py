"""Tests for compare_strategies, coverage_by_year, and coverage_by_source in review metrics."""

import pytest

from easyscielo.models import Article
from easyscielo.review.metrics import (
    compare_strategies,
    coverage_by_source,
    coverage_by_year,
)
from easyscielo.review.models import ReviewRecord, Stage, make_record_id


def _make_record(
    doi: str, title: str, year: int = 2020, source: str = "scielo"
) -> ReviewRecord:
    art = Article(
        title=title, authors=["Author Test"], year=year, doi=doi, source=source
    )
    rec_id = make_record_id(art)
    return ReviewRecord(record_id=rec_id, article=art, stage=Stage.IDENTIFIED)


def test_compare_three_synthetic_strategies() -> None:
    # 4 gold standard articles
    g1 = _make_record("10.1000/g1", "Gold Standard 1")
    g2 = _make_record("10.1000/g2", "Gold Standard 2")
    g3 = _make_record("10.1000/g3", "Gold Standard 3")
    g4 = _make_record("10.1000/g4", "Gold Standard 4")
    gold_standard = [g1, g2, g3, g4]

    # Strategy High (Best): Retrieves all 4 gold standard records, 0 FP -> TP=4, FP=0, FN=0 -> F1=1.0
    strat_high = [g1, g2, g3, g4]

    # Strategy Medium: Retrieves g1, g2, g3 + 2 FP -> TP=3, FP=2, FN=1 -> Precision=0.6, Recall=0.75, F1=0.6667
    fp1 = _make_record("10.1000/fp1", "False Positive 1")
    fp2 = _make_record("10.1000/fp2", "False Positive 2")
    strat_med = [g1, g2, g3, fp1, fp2]

    # Strategy Low: Retrieves g1 + 4 FP -> TP=1, FP=4, FN=3 -> Precision=0.2, Recall=0.25, F1=0.2222
    fp3 = _make_record("10.1000/fp3", "False Positive 3")
    fp4 = _make_record("10.1000/fp4", "False Positive 4")
    strat_low = [g1, fp1, fp2, fp3, fp4]

    results = {
        "Strategy Medium": strat_med,
        "Strategy Low": strat_low,
        "Strategy High": strat_high,
    }

    comparisons = compare_strategies(results, gold_standard)

    # 1. Verify 3 results returned
    assert len(comparisons) == 3

    # 2. Verify ordering by F1 descending
    assert comparisons[0].name == "Strategy High"
    assert comparisons[1].name == "Strategy Medium"
    assert comparisons[2].name == "Strategy Low"

    assert comparisons[0].metrics.f1 == pytest.approx(1.0)
    assert comparisons[1].metrics.f1 == pytest.approx(2 * 0.6 * 0.75 / (0.6 + 0.75))
    assert comparisons[2].metrics.f1 == pytest.approx(2 * 0.2 * 0.25 / (0.2 + 0.25))

    # 3. Verify winner marking
    assert comparisons[0].is_best is True
    assert comparisons[0].best is True
    assert comparisons[1].is_best is False
    assert comparisons[2].is_best is False


def test_compare_strategies_empty_and_ties() -> None:
    # Test empty dict
    assert compare_strategies({}, []) == []

    # Test tied F1
    g1 = _make_record("10.1000/g1", "Gold 1")
    gold = [g1]
    res = {
        "Strat A": [g1],
        "Strat B": [g1],
    }
    comps = compare_strategies(res, gold)
    assert len(comps) == 2
    assert comps[0].is_best is True
    assert comps[1].is_best is True


def test_coverage_by_source() -> None:
    records = [
        _make_record("10.1000/s1", "SciELO Art 1", source="scielo"),
        _make_record("10.1000/s2", "SciELO Art 2", source="scielo"),
        _make_record("10.1000/o1", "OpenAlex Art 1", source="openalex"),
        _make_record("10.1000/o2", "OpenAlex Art 2", source="openalex"),
        _make_record("10.1000/o3", "OpenAlex Art 3", source="openalex"),
        _make_record("10.1000/c1", "CrossRef Art 1", source="crossref"),
        _make_record("10.1000/u1", "Unknown Source 1", source=""),
        _make_record("10.1000/u2", "Unknown Source 2", source="   "),
    ]

    counts = coverage_by_source(records)

    assert counts["crossref"] == 1
    assert counts["openalex"] == 3
    assert counts["scielo"] == 2
    assert counts["unknown"] == 2

    # Check ordering: alphabetical, unknown at end
    assert list(counts.keys()) == ["crossref", "openalex", "scielo", "unknown"]


def test_coverage_by_year() -> None:
    records = [
        _make_record("10.1000/y1", "Art 2020-1", year=2020),
        _make_record("10.1000/y2", "Art 2020-2", year=2020),
        _make_record("10.1000/y3", "Art 2018", year=2018),
        _make_record("10.1000/y4", "Art 2021-1", year=2021),
        _make_record("10.1000/y5", "Art 2021-2", year=2021),
        _make_record("10.1000/y6", "Art 2021-3", year=2021),
        _make_record("10.1000/y7", "Art Zero", year=0),
        Article(title="Art None", authors=["A"], year=None),  # type: ignore[arg-type]
    ]

    counts = coverage_by_year(records)

    assert counts[2018] == 1
    assert counts[2020] == 2
    assert counts[2021] == 3
    assert counts["unknown"] == 2

    # Check key ordering: numeric years ascending, unknown at end
    assert list(counts.keys()) == [2018, 2020, 2021, "unknown"]
