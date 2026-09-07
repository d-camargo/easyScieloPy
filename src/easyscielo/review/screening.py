"""Deterministic and auditable record screening for systematic reviews."""

import re
import warnings
from dataclasses import dataclass
from typing import Iterable, Optional, Union

from easyscielo._optional import require
from easyscielo.filters import _remove_accents
from easyscielo.models import Article
from easyscielo.review.models import Decision, ReviewRecord, Stage, make_record_id

__all__ = ["ScreeningCriteria", "screen", "rank_by_relevance"]


@dataclass
class ScreeningCriteria:
    """Criteria for deterministic and auditable record screening."""

    include_terms: Optional[list[str]] = None
    exclude_terms: Optional[list[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    languages: Optional[list[str]] = None


def screen(
    records: Iterable[Union[ReviewRecord, Article]],
    criteria: ScreeningCriteria,
) -> list[ReviewRecord]:
    """Screen records against criteria in a deterministic and auditable manner.

    Args:
        records: Collection of ReviewRecord or Article instances.
        criteria: ScreeningCriteria instance defining inclusion/exclusion rules.

    Returns:
        List of screened ReviewRecord instances with updated decision,
        decision_reason, and stage set to Stage.SCREENED.
    """
    result: list[ReviewRecord] = []

    for item in records:
        if isinstance(item, Article):
            rec = ReviewRecord(
                record_id=make_record_id(item),
                article=item,
                stage=Stage.SCREENED,
            )
        elif isinstance(item, ReviewRecord):
            rec = item
            rec.stage = Stage.SCREENED
        else:
            raise TypeError(f"Expected ReviewRecord or Article, got {type(item)}")

        article = rec.article
        has_title = bool(article.title and article.title.strip())
        has_abstract = bool(article.abstract and article.abstract.strip())

        # Check for insufficient metadata first (neither title nor abstract present)
        if not has_title and not has_abstract:
            rec.decision = Decision.MAYBE
            rec.decision_reason = "insufficient metadata"
            result.append(rec)
            continue

        # Evaluate exclusion criteria first (exclusion trumps inclusion)
        excluded = False

        # 1. Year min check
        if (
            criteria.year_min is not None
            and article.year is not None
            and article.year < criteria.year_min
        ):
            rec.decision = Decision.EXCLUDE
            rec.decision_reason = (
                f"excluded: year {article.year} < year_min {criteria.year_min}"
            )
            excluded = True

        # 2. Year max check
        elif (
            criteria.year_max is not None
            and article.year is not None
            and article.year > criteria.year_max
        ):
            rec.decision = Decision.EXCLUDE
            rec.decision_reason = (
                f"excluded: year {article.year} > year_max {criteria.year_max}"
            )
            excluded = True

        # 3. Languages check
        elif criteria.languages is not None and len(criteria.languages) > 0:
            crit_langs = {lang.lower().strip() for lang in criteria.languages if lang}
            article_langs = set()
            if isinstance(article.languages, (list, tuple, set)):
                article_langs = {
                    str(lang).lower().strip() for lang in article.languages if lang
                }
            elif isinstance(article.languages, str) and article.languages:
                article_langs = {article.languages.lower().strip()}

            if not (article_langs & crit_langs):
                lang_str = ", ".join(sorted(article_langs)) if article_langs else "none"
                rec.decision = Decision.EXCLUDE
                rec.decision_reason = (
                    f"excluded: language '{lang_str}' not in languages"
                )
                excluded = True

        # 4. Exclude terms check
        if (
            not excluded
            and criteria.exclude_terms is not None
            and len(criteria.exclude_terms) > 0
        ):
            raw_text = f"{article.title or ''} {article.abstract or ''}"
            norm_text = _remove_accents(raw_text).lower()
            text_words = set(re.findall(r"\w+", norm_text))

            for term in criteria.exclude_terms:
                norm_term = _remove_accents(term).lower()
                term_words = re.findall(r"\w+", norm_term)
                if term_words and all(w in text_words for w in term_words):
                    rec.decision = Decision.EXCLUDE
                    rec.decision_reason = f"excluded: exclude_term '{term}' found"
                    excluded = True
                    break

        if excluded:
            result.append(rec)
            continue

        # Evaluate inclusion criteria if present
        if criteria.include_terms is not None and len(criteria.include_terms) > 0:
            raw_text = f"{article.title or ''} {article.abstract or ''}"
            norm_text = _remove_accents(raw_text).lower()
            text_words = set(re.findall(r"\w+", norm_text))
            matched_term = None

            for term in criteria.include_terms:
                norm_term = _remove_accents(term).lower()
                term_words = re.findall(r"\w+", norm_term)
                if term_words and all(w in text_words for w in term_words):
                    matched_term = term
                    break

            if matched_term is not None:
                rec.decision = Decision.INCLUDE
                rec.decision_reason = f"included: include_term '{matched_term}' found"
            else:
                rec.decision = Decision.EXCLUDE
                rec.decision_reason = "excluded: no include_terms matched"
        else:
            rec.decision = Decision.INCLUDE
            rec.decision_reason = "included: criteria satisfied"

        result.append(rec)

    return result


def rank_by_relevance(
    records: Iterable[Union[ReviewRecord, Article]],
    seed_relevant_ids: Iterable[str],
    *,
    top_n: Optional[int] = None,
) -> list[tuple[ReviewRecord, float]]:
    """Rank unlabeled records by relevance using TF-IDF and Logistic Regression or cosine similarity.

    Args:
        records: Collection of ReviewRecord or Article instances.
        seed_relevant_ids: Collection of record IDs considered relevant seeds.
        top_n: Optional maximum number of records to return.

    Returns:
        List of (ReviewRecord, float score) tuples for unlabeled records,
        sorted in descending order of relevance score.
    """
    require("sklearn", "screening")
    import numpy as np
    from sklearn.feature_extraction.text import (  # type: ignore[import-untyped,import-not-found]
        TfidfVectorizer,
    )
    from sklearn.linear_model import (  # type: ignore[import-untyped,import-not-found]
        LogisticRegression,
    )
    from sklearn.metrics.pairwise import (  # type: ignore[import-untyped,import-not-found]
        cosine_similarity,
    )

    records_list: list[ReviewRecord] = []
    for item in records:
        if isinstance(item, Article):
            rec = ReviewRecord(
                record_id=make_record_id(item),
                article=item,
                stage=Stage.IDENTIFIED,
            )
        elif isinstance(item, ReviewRecord):
            rec = item
        else:
            raise TypeError(f"Expected ReviewRecord or Article, got {type(item)}")
        records_list.append(rec)

    if not records_list:
        return []

    seed_set = set(seed_relevant_ids) if seed_relevant_ids is not None else set()

    labeled_indices: list[int] = []
    unlabeled_indices: list[int] = []
    y_train: list[int] = []

    for idx, rec in enumerate(records_list):
        if rec.record_id in seed_set or rec.decision == Decision.INCLUDE:
            labeled_indices.append(idx)
            y_train.append(1)
        elif rec.decision == Decision.EXCLUDE:
            labeled_indices.append(idx)
            y_train.append(0)
        else:
            unlabeled_indices.append(idx)

    if not unlabeled_indices:
        return []

    corpus_texts = [
        f"{rec.article.title or ''} {rec.article.abstract or ''}".strip()
        for rec in records_list
    ]

    vectorizer = TfidfVectorizer()
    try:
        X_all = vectorizer.fit_transform(corpus_texts)
    except ValueError:
        results = [(records_list[idx], 0.0) for idx in unlabeled_indices]
        if top_n is not None:
            results = results[:top_n]
        return results

    n_seeds = len(labeled_indices)
    unique_classes = set(y_train)

    if n_seeds < 2 or len(unique_classes) < 2:
        warnings.warn(
            "Fewer than 2 seeds or single class available; falling back to cosine similarity with seed centroid.",
            UserWarning,
            stacklevel=2,
        )
        pos_indices = [idx for idx, y in zip(labeled_indices, y_train) if y == 1]
        if pos_indices:
            centroid = np.asarray(X_all[pos_indices].mean(axis=0))
        elif labeled_indices:
            centroid = np.asarray(X_all[labeled_indices].mean(axis=0))
        else:
            centroid = np.zeros((1, X_all.shape[1]))

        sims = cosine_similarity(X_all[unlabeled_indices], centroid)
        scores = sims.ravel()
    else:
        clf = LogisticRegression()
        clf.fit(X_all[labeled_indices], y_train)
        pos_class_idx = list(clf.classes_).index(1)
        scores = clf.predict_proba(X_all[unlabeled_indices])[:, pos_class_idx]

    results = [
        (records_list[unlabeled_idx], float(score))
        for unlabeled_idx, score in zip(unlabeled_indices, scores)
    ]
    results.sort(key=lambda item: item[1], reverse=True)

    if top_n is not None:
        results = results[:top_n]

    return results
