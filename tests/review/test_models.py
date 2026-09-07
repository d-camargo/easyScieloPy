import hashlib

from easyscielo.models import Article
from easyscielo.review.models import (
    Corpus,
    Decision,
    ReviewRecord,
    Stage,
    make_record_id,
)


def test_make_record_id_doi_case_insensitive():
    a1 = Article(title="Test Title", authors=["Author A"], year=2020, doi="10.123/XYZ")
    a2 = Article(title="Test Title", authors=["Author A"], year=2020, doi="10.123/xyz")
    assert make_record_id(a1) == make_record_id(a2)


def test_make_record_id_fallback_title_year_author():
    a = Article(title="Title A", authors=["Author A"], year=2020)
    expected_key = "title a|2020|author a"
    expected = hashlib.sha256(expected_key.encode("utf-8")).hexdigest()[:16]
    assert make_record_id(a) == expected


def test_make_record_id_fallback_no_author():
    a = Article(title="Title B", authors=[], year=2021)
    expected_key = "title b|2021|"
    expected = hashlib.sha256(expected_key.encode("utf-8")).hexdigest()[:16]
    assert make_record_id(a) == expected


def test_review_record_as_dict():
    a = Article(title="Test Title", authors=["Author A"], year=2020)
    record = ReviewRecord(
        record_id=make_record_id(a),
        article=a,
        stage=Stage.IDENTIFIED,
        decision=Decision.MAYBE,
    )
    d = record.as_dict()

    # Check that title is the first column
    assert list(d.keys())[0] == "title"

    # Check review columns were appended
    assert d["record_id"] == record.record_id
    assert d["stage"] == "IDENTIFIED"
    assert d["decision"] == "MAYBE"


def test_corpus_methods():
    a = Article(title="Test Title", authors=["Author A"], year=2020)
    r1 = ReviewRecord("id1", a, Stage.IDENTIFIED)
    r2 = ReviewRecord("id2", a, Stage.SCREENED, Decision.INCLUDE)

    corpus = Corpus([r1, r2])

    counts = corpus.counts_by_stage()
    assert counts[Stage.IDENTIFIED] == 1
    assert counts[Stage.SCREENED] == 1
    assert counts[Stage.EXCLUDED] == 0

    screened = corpus.filter_by(Stage.SCREENED)
    assert len(screened) == 1
    assert screened[0].record_id == "id2"
