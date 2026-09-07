import pytest

from easyscielo.models import Article
from easyscielo.review.dedup import DedupResult
from easyscielo.review.models import (
    Corpus,
    Decision,
    ReviewRecord,
    Stage,
)
from easyscielo.review.prisma import prisma_counts, to_mermaid


def test_prisma_counts_three_sources_and_identity():
    # 4 from pubmed, 5 from scopus, 6 from scielo -> total 15 identified
    records = []

    for i in range(4):
        art = Article(
            title=f"Pubmed Article {i}",
            authors=["Author A"],
            year=2020,
            source="pubmed",
        )
        records.append(
            ReviewRecord(record_id=f"pm_{i}", article=art, stage=Stage.IDENTIFIED)
        )

    for i in range(5):
        art = Article(
            title=f"Scopus Article {i}",
            authors=["Author B"],
            year=2020,
            source="scopus",
        )
        records.append(
            ReviewRecord(record_id=f"sc_{i}", article=art, stage=Stage.IDENTIFIED)
        )

    for i in range(6):
        art = Article(
            title=f"SciELO Article {i}",
            authors=["Author C"],
            year=2020,
            source="scielo",
        )
        records.append(
            ReviewRecord(record_id=f"scl_{i}", article=art, stage=Stage.IDENTIFIED)
        )

    # Mark 3 as duplicates
    records[1].duplicate_of = "pm_0"
    records[1].stage = Stage.DEDUPLICATED

    records[5].duplicate_of = "sc_0"
    records[5].stage = Stage.DEDUPLICATED

    records[10].duplicate_of = "scl_0"
    records[10].stage = Stage.DEDUPLICATED

    # 12 screened remaining: exclude 3 with reasons, include 9
    records[2].stage = Stage.SCREENED
    records[2].decision = Decision.EXCLUDE
    records[2].decision_reason = "excluded: year < 2010"

    records[3].stage = Stage.SCREENED
    records[3].decision = Decision.EXCLUDE
    records[3].decision_reason = "excluded: year < 2010"

    records[6].stage = Stage.SCREENED
    records[6].decision = Decision.EXCLUDE
    records[6].decision_reason = "excluded: language not in languages"

    for r in [
        records[0],
        records[4],
        records[7],
        records[8],
        records[9],
        records[11],
        records[12],
        records[13],
        records[14],
    ]:
        r.stage = Stage.SCREENED
        r.decision = Decision.INCLUDE
        r.decision_reason = "included: criteria satisfied"

    corpus = Corpus(records)
    counts = prisma_counts(corpus)

    assert counts["identified"] == {"pubmed": 4, "scopus": 5, "scielo": 6}
    assert counts["total_identified"] == 15
    assert counts["duplicates_removed"] == 3
    assert counts["screened"] == 12

    # Check key identity requested by PRISMA: identified - duplicates_removed == screened
    total_identified = sum(counts["identified"].values())
    assert total_identified - counts["duplicates_removed"] == counts["screened"]
    assert (
        counts["total_identified"] - counts["duplicates_removed"] == counts["screened"]
    )

    assert counts["excluded_screening"] == {
        "excluded: year < 2010": 2,
        "excluded: language not in languages": 1,
    }
    assert counts["total_excluded_screening"] == 3
    assert counts["included"] == 9


def test_prisma_counts_with_dedup_result():
    unique_recs = []
    dup_recs = []

    for i in range(3):
        art = Article(
            title=f"Unique {i}", authors=["A"], year=2021, collection="scielo"
        )
        unique_recs.append(
            ReviewRecord(record_id=f"u_{i}", article=art, stage=Stage.IDENTIFIED)
        )

    for i in range(2):
        art = Article(title=f"Dup {i}", authors=["B"], year=2021, collection="scielo")
        rec = ReviewRecord(
            record_id=f"d_{i}",
            article=art,
            stage=Stage.DEDUPLICATED,
            duplicate_of="u_0",
        )
        dup_recs.append(rec)

    dedup_res = DedupResult(unique=unique_recs, duplicates=dup_recs, groups=[])
    corpus = Corpus(unique_recs)

    counts = prisma_counts(corpus, dedup_result=dedup_res)

    assert counts["total_identified"] == 5
    assert counts["duplicates_removed"] == 2
    assert counts["screened"] == 3
    assert (
        counts["total_identified"] - counts["duplicates_removed"] == counts["screened"]
    )


def test_prisma_counts_with_raw_articles():
    articles = [
        Article(title="Art 1", authors=["A"], year=2020, source="pubmed"),
        Article(title="Art 2", authors=["B"], year=2021, source="scopus"),
    ]
    counts = prisma_counts(articles, dedup_result=0)

    assert counts["identified"] == {"pubmed": 1, "scopus": 1}
    assert counts["total_identified"] == 2
    assert counts["duplicates_removed"] == 0
    assert counts["screened"] == 2


def test_to_mermaid_flowchart():
    counts = {
        "identified": {"pubmed": 4, "scopus": 5, "scielo": 6},
        "total_identified": 15,
        "duplicates_removed": 3,
        "screened": 12,
        "excluded_screening": {
            "excluded: year < 2010": 2,
            "excluded: language not in languages": 1,
        },
        "total_excluded_screening": 3,
        "included": 9,
    }

    mermaid = to_mermaid(counts)

    assert "flowchart TD" in mermaid
    assert 'subgraph Identification["Identification"]' in mermaid
    assert "pubmed (n = 4)" in mermaid
    assert "scopus (n = 5)" in mermaid
    assert "scielo (n = 6)" in mermaid
    assert "Duplicates Removed (n = 3)" in mermaid
    assert "Records Screened (n = 12)" in mermaid
    assert 'subgraph Excluded["Excluded during Screening"]' in mermaid
    assert "excluded: year < 2010 (n = 2)" in mermaid
    assert "Records Included (n = 9)" in mermaid


def test_invalid_corpus_type():
    with pytest.raises(TypeError):
        prisma_counts(12345)


def test_prisma_counts_prefers_record_source_db():
    """ReviewRecord.source_db wins over article.source in PRISMA identification."""
    records = []
    for i in range(2):
        art = Article(
            title=f"RIS Article {i}",
            authors=["Author A"],
            year=2020,
            source="ris",
        )
        records.append(
            ReviewRecord(
                record_id=f"ris_{i}",
                article=art,
                stage=Stage.IDENTIFIED,
                source_db="ris:pubmed_export.ris",
            )
        )

    counts = prisma_counts(Corpus(records))

    assert counts["identified"] == {"ris:pubmed_export.ris": 2}
