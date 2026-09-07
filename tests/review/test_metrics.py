"""Tests for review metrics (confusion, SearchMetrics, evaluate_strategy)."""

import pytest

from easyscielo.models import Article
from easyscielo.review.metrics import (
    Confusion,
    confusion,
    evaluate_strategy,
)
from easyscielo.review.models import Corpus, ReviewRecord, Stage, make_record_id


def test_confusion_without_universe() -> None:
    retrieved = ["id1", "id2", "id3"]
    relevant = ["id2", "id3", "id4"]
    conf = confusion(retrieved, relevant)

    assert conf.tp == 2
    assert conf.fp == 1
    assert conf.fn == 1
    assert conf.tn is None


def test_confusion_with_universe() -> None:
    retrieved = ["id1", "id2", "id3"]
    relevant = ["id2", "id3", "id4"]
    conf = confusion(retrieved, relevant, universe_size=10)

    assert conf.tp == 2
    assert conf.fp == 1
    assert conf.fn == 1
    assert conf.tn == 6


def test_hand_calculated_matrix() -> None:
    # N=100, retrieved=30, relevant=20, tp=15
    # fp = 30 - 15 = 15
    # fn = 20 - 15 = 5
    # tn = 100 - (15 + 15 + 5) = 65
    conf = Confusion(tp=15, fp=15, fn=5, tn=65)
    metrics = conf.metrics

    assert metrics.precision == 0.5
    assert metrics.recall == 0.75
    assert metrics.sensitivity == 0.75
    assert metrics.specificity == 0.8125  # 65 / (65 + 15)
    assert metrics.f1 == pytest.approx(0.6)  # 2 * 0.5 * 0.75 / 1.25
    assert metrics.accuracy == 0.8  # (15 + 65) / 100
    assert metrics.nnr == 2.0  # 1 / 0.5


def test_zero_denominator_cases() -> None:
    # 1) Both empty
    m1 = confusion([], []).metrics
    assert m1.precision is None
    assert m1.recall is None
    assert m1.sensitivity is None
    assert m1.specificity is None
    assert m1.f1 is None
    assert m1.accuracy is None
    assert m1.nnr is None

    # 2) Retrieved non-empty, Relevant empty
    m2 = confusion(["a"], []).metrics
    assert m2.precision == 0.0
    assert m2.recall is None
    assert m2.sensitivity is None
    assert m2.f1 is None
    assert m2.nnr is None

    # 3) Retrieved empty, Relevant non-empty
    m3 = confusion([], ["a"]).metrics
    assert m3.precision is None
    assert m3.recall == 0.0
    assert m3.sensitivity == 0.0
    assert m3.f1 is None
    assert m3.nnr is None

    # 4) Disjoint (0 overlap)
    m4 = confusion(["a"], ["b"]).metrics
    assert m4.precision == 0.0
    assert m4.recall == 0.0
    assert m4.sensitivity == 0.0
    assert m4.f1 is None
    assert m4.nnr is None


def test_empty_gold_standard() -> None:
    records = [
        Article(title="Article 1", authors=["Author 1"], year=2021, doi="10.1590/12345")
    ]
    gold_standard: list[Article] = []

    metrics = evaluate_strategy(records, gold_standard)
    assert metrics.confusion is not None
    assert metrics.confusion.tp == 0
    assert metrics.confusion.fp == 1
    assert metrics.confusion.fn == 0
    assert metrics.precision == 0.0
    assert metrics.recall is None
    assert metrics.f1 is None
    assert metrics.nnr is None


def test_evaluate_strategy_doi_and_record_id_matching() -> None:
    # Article 1: Matching by DOI
    art1_ret = Article(
        title="Article One",
        authors=["A"],
        year=2020,
        doi="10.1590/S0104-11692004000100001",
    )
    art1_gold = Article(
        title="Article One Full",
        authors=["A"],
        year=2020,
        doi="https://doi.org/10.1590/s0104-11692004000100001",
    )

    # Article 2: Matching by record_id (no DOI)
    art2 = Article(title="No DOI Article", authors=["Silva, A."], year=2020)
    rec2_ret = ReviewRecord(
        record_id=make_record_id(art2), article=art2, stage=Stage.IDENTIFIED
    )
    rec2_gold = ReviewRecord(
        record_id=make_record_id(art2), article=art2, stage=Stage.SCREENED
    )

    # Article 3: Only in retrieved (FP)
    art3_ret = Article(
        title="Unmatched Retrieved",
        authors=["B"],
        year=2021,
        doi="10.1000/only-retrieved",
    )

    # Article 4: Only in gold standard (FN)
    art4_gold = Article(
        title="Unmatched Gold", authors=["C"], year=2021, doi="10.1000/only-gold"
    )

    records = [art1_ret, rec2_ret, art3_ret]
    gold_standard = [art1_gold, rec2_gold, art4_gold]

    metrics = evaluate_strategy(records, gold_standard)

    assert metrics.confusion is not None
    assert metrics.confusion.tp == 2
    assert metrics.confusion.fp == 1
    assert metrics.confusion.fn == 1
    assert metrics.precision == pytest.approx(2 / 3)
    assert metrics.recall == pytest.approx(2 / 3)
    assert metrics.f1 == pytest.approx(2 / 3)


def test_evaluate_strategy_with_corpus() -> None:
    art = Article(
        title="Corpus Article", authors=["Author"], year=2022, doi="10.1590/test-corpus"
    )
    rec = ReviewRecord(
        record_id=make_record_id(art), article=art, stage=Stage.IDENTIFIED
    )

    retrieved_corpus = Corpus(records=[rec])
    gold_corpus = Corpus(records=[rec])

    metrics = evaluate_strategy(retrieved_corpus, gold_corpus, universe_size=10)

    assert metrics.confusion is not None
    assert metrics.confusion.tp == 1
    assert metrics.confusion.fp == 0
    assert metrics.confusion.fn == 0
    assert metrics.confusion.tn == 9
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert metrics.specificity == 1.0
    assert metrics.accuracy == 1.0
    assert metrics.nnr == 1.0
