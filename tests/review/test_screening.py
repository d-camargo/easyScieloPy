from easyscielo.models import Article
from easyscielo.review.models import Decision, ReviewRecord, Stage, make_record_id
from easyscielo.review.screening import ScreeningCriteria, screen


def test_screen_year_min_isolated():
    a1 = Article(
        title="Paper 1", authors=["Author"], year=1998, abstract="Some abstract"
    )
    a2 = Article(
        title="Paper 2", authors=["Author"], year=2015, abstract="Some abstract"
    )
    r1 = ReviewRecord(make_record_id(a1), a1, Stage.IDENTIFIED)
    r2 = ReviewRecord(make_record_id(a2), a2, Stage.IDENTIFIED)

    criteria = ScreeningCriteria(year_min=2010)
    results = screen([r1, r2], criteria)

    assert len(results) == 2
    assert results[0].decision == Decision.EXCLUDE
    assert results[0].decision_reason == "excluded: year 1998 < year_min 2010"
    assert results[0].stage == Stage.SCREENED

    assert results[1].decision == Decision.INCLUDE
    assert results[1].decision_reason == "included: criteria satisfied"
    assert results[1].stage == Stage.SCREENED


def test_screen_year_max_isolated():
    a1 = Article(
        title="Paper 1", authors=["Author"], year=2025, abstract="Some abstract"
    )
    a2 = Article(
        title="Paper 2", authors=["Author"], year=2018, abstract="Some abstract"
    )

    criteria = ScreeningCriteria(year_max=2020)
    results = screen([a1, a2], criteria)

    assert results[0].decision == Decision.EXCLUDE
    assert results[0].decision_reason == "excluded: year 2025 > year_max 2020"
    assert results[1].decision == Decision.INCLUDE


def test_screen_languages_isolated():
    a1 = Article(
        title="Paper 1",
        authors=["Author"],
        year=2020,
        languages=["es"],
        abstract="Abstract",
    )
    a2 = Article(
        title="Paper 2",
        authors=["Author"],
        year=2020,
        languages=["en"],
        abstract="Abstract",
    )

    criteria = ScreeningCriteria(languages=["en", "pt"])
    results = screen([a1, a2], criteria)

    assert results[0].decision == Decision.EXCLUDE
    assert "excluded: language 'es' not in languages" in results[0].decision_reason
    assert results[1].decision == Decision.INCLUDE


def test_screen_exclude_terms_isolated():
    a1 = Article(
        title="Revisão Sistemática de Literatura",
        authors=["Author"],
        year=2020,
        abstract="Um estudo sobre saude",
    )
    a2 = Article(
        title="Estudo Preditivo em Saúde",
        authors=["Author"],
        year=2020,
        abstract="Análise de dados",
    )

    criteria = ScreeningCriteria(exclude_terms=["revisao sistematica"])
    results = screen([a1, a2], criteria)

    assert results[0].decision == Decision.EXCLUDE
    assert (
        results[0].decision_reason
        == "excluded: exclude_term 'revisao sistematica' found"
    )
    assert results[1].decision == Decision.INCLUDE


def test_screen_include_terms_isolated():
    a1 = Article(
        title="Inteligência Artificial na Saúde",
        authors=["Author"],
        year=2020,
        abstract="Redes neurais em medicina",
    )
    a2 = Article(
        title="Estudo de Química Geral",
        authors=["Author"],
        year=2020,
        abstract="Reações orgânicas",
    )

    criteria = ScreeningCriteria(
        include_terms=["inteligencia artificial", "redes neurais"]
    )
    results = screen([a1, a2], criteria)

    assert results[0].decision == Decision.INCLUDE
    assert (
        "included: include_term 'inteligencia artificial' found"
        in results[0].decision_reason
    )
    assert results[1].decision == Decision.EXCLUDE
    assert results[1].decision_reason == "excluded: no include_terms matched"


def test_screen_normalization_accents_case_and_all_words():
    # Term: "aprendizado de maquina" (lowercase, no accents)
    # Title has accents and mixed case: "Aprendizadô de Máquinâ na Saúde"
    a = Article(
        title="Aprendizadô de Máquinâ na Saúde",
        authors=["Author"],
        year=2021,
        abstract="Aplicação prática em hospitais.",
    )
    criteria = ScreeningCriteria(include_terms=["aprendizado de maquina"])
    results = screen([a], criteria)

    assert results[0].decision == Decision.INCLUDE
    assert (
        "included: include_term 'aprendizado de maquina' found"
        in results[0].decision_reason
    )


def test_screen_precedence_exclusion_wins_over_inclusion():
    # Article matches include_terms BUT ALSO fails year_min and matches exclude_terms
    a1 = Article(
        title="Machine Learning for Healthcare: A Systematic Review",
        authors=["Author"],
        year=1998,
        abstract="Overview of models",
    )
    a2 = Article(
        title="Machine Learning for Healthcare: A Systematic Review",
        authors=["Author"],
        year=2020,
        abstract="Overview of models",
    )

    criteria = ScreeningCriteria(
        include_terms=["machine learning"],
        exclude_terms=["systematic review"],
        year_min=2010,
    )
    results = screen([a1, a2], criteria)

    # a1 fails year_min first
    assert results[0].decision == Decision.EXCLUDE
    assert results[0].decision_reason == "excluded: year 1998 < year_min 2010"

    # a2 fails exclude_terms
    assert results[1].decision == Decision.EXCLUDE
    assert (
        results[1].decision_reason == "excluded: exclude_term 'systematic review' found"
    )


def test_screen_insufficient_metadata():
    # Record with neither title nor abstract -> MAYBE with "insufficient metadata"
    a_empty = Article(title="", authors=["Author"], year=2020, abstract="")
    a_none = Article(title=None, authors=["Author"], year=2020, abstract=None)

    criteria = ScreeningCriteria(include_terms=["health"])
    results = screen([a_empty, a_none], criteria)

    assert results[0].decision == Decision.MAYBE
    assert results[0].decision_reason == "insufficient metadata"
    assert results[0].stage == Stage.SCREENED

    assert results[1].decision == Decision.MAYBE
    assert results[1].decision_reason == "insufficient metadata"
    assert results[1].stage == Stage.SCREENED


def test_screen_crossref_title_without_abstract():
    # Common Crossref case: title is present, abstract is missing
    a = Article(
        title="Machine Learning Methods in Cardiology",
        authors=["Author"],
        year=2021,
        abstract=None,
    )
    criteria = ScreeningCriteria(include_terms=["machine learning"])
    results = screen([a], criteria)

    # Title is sufficient to evaluate include_terms
    assert results[0].decision == Decision.INCLUDE
    assert (
        "included: include_term 'machine learning' found" in results[0].decision_reason
    )
    assert results[0].stage == Stage.SCREENED
