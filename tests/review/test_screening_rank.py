import warnings
from unittest.mock import patch

import pytest

pytest.importorskip("sklearn")

from easyscielo.models import Article
from easyscielo.review.models import Decision, ReviewRecord, Stage, make_record_id
from easyscielo.review.screening import rank_by_relevance


def test_rank_by_relevance_logistic_regression_seed_vocabulary_higher():
    # Seeds (2 seeds, 2 classes)
    art_pos = Article(
        title="Machine Learning for Medical Diagnostics",
        authors=["Author A"],
        year=2021,
        abstract="Deep learning models for clinical healthcare diagnosis.",
    )
    art_neg = Article(
        title="Ancient Roman Empire Politics",
        authors=["Author B"],
        year=2020,
        abstract="Historical governance structures of the Roman Senate.",
    )

    rec_pos = ReviewRecord(make_record_id(art_pos), art_pos, Stage.IDENTIFIED)
    rec_neg = ReviewRecord(
        make_record_id(art_neg), art_neg, Stage.IDENTIFIED, decision=Decision.EXCLUDE
    )

    # Unlabeled records
    art_rel = Article(
        title="Neural Networks for Health Care",
        authors=["Author C"],
        year=2022,
        abstract="Medical machine learning algorithms in clinical practice.",
    )
    art_unrel = Article(
        title="Traditional Italian Pasta Cooking Recipes",
        authors=["Author D"],
        year=2023,
        abstract="Culinary secrets for making fresh spaghetti with tomato sauce.",
    )

    rec_rel = ReviewRecord(make_record_id(art_rel), art_rel, Stage.IDENTIFIED)
    rec_unrel = ReviewRecord(make_record_id(art_unrel), art_unrel, Stage.IDENTIFIED)

    records = [rec_pos, rec_neg, rec_rel, rec_unrel]
    seed_ids = [rec_pos.record_id]

    ranked = rank_by_relevance(records, seed_ids)

    # Labeled seeds should NOT be in the returned list
    returned_ids = [r.record_id for r, _ in ranked]
    assert rec_pos.record_id not in returned_ids
    assert rec_neg.record_id not in returned_ids

    # Unlabeled related document should rank higher than unrelated
    assert len(ranked) == 2
    assert ranked[0][0].record_id == rec_rel.record_id
    assert ranked[1][0].record_id == rec_unrel.record_id
    assert ranked[0][1] > ranked[1][1]


def test_rank_by_relevance_fallback_single_seed_warning():
    art_pos = Article(
        title="Machine Learning in Health",
        authors=["Author A"],
        year=2021,
        abstract="Artificial intelligence for medical diagnosis.",
    )
    rec_pos = ReviewRecord(make_record_id(art_pos), art_pos, Stage.IDENTIFIED)

    art_rel = Article(
        title="Deep Learning Diagnostics",
        authors=["Author B"],
        year=2022,
        abstract="Medical machine learning applications.",
    )
    art_unrel = Article(
        title="Astronomy and Stellar Physics",
        authors=["Author C"],
        year=2023,
        abstract="Observations of distant galaxy clusters.",
    )
    rec_rel = ReviewRecord(make_record_id(art_rel), art_rel, Stage.IDENTIFIED)
    rec_unrel = ReviewRecord(make_record_id(art_unrel), art_unrel, Stage.IDENTIFIED)

    records = [rec_pos, rec_rel, rec_unrel]
    seed_ids = [rec_pos.record_id]

    # Only 1 seed -> should trigger warning and fallback to cosine similarity with centroid
    with pytest.warns(UserWarning, match="Fewer than 2 seeds or single class"):
        ranked = rank_by_relevance(records, seed_ids)

    assert len(ranked) == 2
    assert ranked[0][0].record_id == rec_rel.record_id
    assert ranked[1][0].record_id == rec_unrel.record_id
    assert ranked[0][1] > ranked[1][1]


def test_rank_by_relevance_top_n():
    art_pos = Article(
        title="ML Disease", authors=["A"], year=2021, abstract="Medical ML"
    )
    rec_pos = ReviewRecord(make_record_id(art_pos), art_pos, Stage.IDENTIFIED)

    records = [rec_pos]
    for i in range(5):
        art = Article(
            title=f"Unlabeled Paper {i} ML Medical",
            authors=["B"],
            year=2022,
            abstract=f"Health diagnostic {i}",
        )
        records.append(ReviewRecord(make_record_id(art), art, Stage.IDENTIFIED))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        ranked = rank_by_relevance(records, [rec_pos.record_id], top_n=2)

    assert len(ranked) == 2


def test_rank_by_relevance_missing_sklearn():
    art = Article(
        title="Test Paper", authors=["A"], year=2021, abstract="Test abstract"
    )
    rec = ReviewRecord(make_record_id(art), art, Stage.IDENTIFIED)

    with patch(
        "importlib.import_module", side_effect=ImportError("No module named 'sklearn'")
    ):
        with pytest.raises(ImportError, match="sklearn is required for this feature"):
            rank_by_relevance([rec], [rec.record_id])
