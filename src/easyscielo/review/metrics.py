"""Metrics functions and classes for evaluating search strategies in systematic reviews."""

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from easyscielo.models import Article
from easyscielo.review.models import ReviewRecord, make_record_id
from easyscielo.review.normalize import normalize_doi

__all__ = [
    "Confusion",
    "SearchMetrics",
    "StrategyComparison",
    "compare_strategies",
    "confusion",
    "coverage_by_source",
    "coverage_by_year",
    "evaluate_strategy",
]


@dataclass
class Confusion:
    """Confusion matrix counts (TP, FP, FN, TN)."""

    tp: int
    fp: int
    fn: int
    tn: Optional[int] = None

    @property
    def metrics(self) -> "SearchMetrics":
        """Compute SearchMetrics from this confusion matrix."""
        return SearchMetrics.from_confusion(self)


@dataclass
class SearchMetrics:
    """Search evaluation metrics (Precision, Recall, F1, Specificity, Accuracy, NNR)."""

    precision: Optional[float] = None
    recall: Optional[float] = None
    specificity: Optional[float] = None
    f1: Optional[float] = None
    accuracy: Optional[float] = None
    nnr: Optional[float] = None
    confusion: Optional[Confusion] = None

    @property
    def sensitivity(self) -> Optional[float]:
        """Alias for recall."""
        return self.recall

    @classmethod
    def from_confusion(cls, conf: Confusion) -> "SearchMetrics":
        """Build SearchMetrics from a Confusion object."""
        tp, fp, fn, tn = conf.tp, conf.fp, conf.fn, conf.tn

        denom_prec = tp + fp
        precision = (tp / denom_prec) if denom_prec > 0 else None

        denom_rec = tp + fn
        recall = (tp / denom_rec) if denom_rec > 0 else None

        if tn is not None and (tn + fp) > 0:
            specificity = tn / (tn + fp)
        else:
            specificity = None

        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = (2 * precision * recall) / (precision + recall)
        else:
            f1 = None

        if tn is not None and (tp + fp + fn + tn) > 0:
            accuracy = (tp + tn) / (tp + fp + fn + tn)
        else:
            accuracy = None

        if precision is not None and precision > 0:
            nnr = 1.0 / precision
        else:
            nnr = None

        return cls(
            precision=precision,
            recall=recall,
            specificity=specificity,
            f1=f1,
            accuracy=accuracy,
            nnr=nnr,
            confusion=conf,
        )


def confusion(
    retrieved_ids: Iterable[Any],
    relevant_ids: Iterable[Any],
    universe_size: Optional[int] = None,
) -> Confusion:
    """Calculate confusion matrix (TP, FP, FN, TN) between retrieved and relevant IDs.

    Args:
        retrieved_ids: Collection of retrieved item identifiers.
        relevant_ids: Collection of relevant (gold standard) item identifiers.
        universe_size: Total search universe size (N). If None, TN is None.

    Returns:
        Confusion matrix object.
    """
    retrieved = set(retrieved_ids)
    relevant = set(relevant_ids)

    tp = len(retrieved & relevant)
    fp = len(retrieved - relevant)
    fn = len(relevant - retrieved)

    if universe_size is None:
        tn = None
    else:
        tn = max(0, universe_size - (tp + fp + fn))

    return Confusion(tp=tp, fp=fp, fn=fn, tn=tn)


def _to_iterable(obj: Any) -> Iterable[Any]:
    """Convert Corpus or list/iterable into an iterable of items."""
    if hasattr(obj, "records") and isinstance(getattr(obj, "records"), list):
        return getattr(obj, "records")
    return obj


def _extract_key(item: Any) -> str:
    """Extract matching key for an item: normalized DOI if present, falling back to record_id."""
    if isinstance(item, Article):
        doi_norm = normalize_doi(item.doi)
        if doi_norm:
            return f"doi:{doi_norm}"
        return f"id:{make_record_id(item)}"

    if isinstance(item, ReviewRecord):
        if item.article and item.article.doi:
            doi_norm = normalize_doi(item.article.doi)
            if doi_norm:
                return f"doi:{doi_norm}"
        return f"id:{item.record_id}"

    if isinstance(item, str):
        doi_norm = normalize_doi(item)
        if doi_norm and (
            "10." in doi_norm or "/" in doi_norm or item.lower().startswith("doi:")
        ):
            return f"doi:{doi_norm}"
        return f"id:{item}"

    raise TypeError(
        f"Cannot extract matching key from unsupported item type: {type(item)}"
    )


def evaluate_strategy(
    records: Any,
    gold_standard: Any,
    universe_size: Optional[int] = None,
) -> SearchMetrics:
    """Evaluate a search strategy against a gold standard dataset.

    Matches items by normalized DOI, falling back to record_id.

    Args:
        records: Collection of retrieved items (ReviewRecord, Article, str, or Corpus).
        gold_standard: Collection of relevant items (ReviewRecord, Article, str, or Corpus).
        universe_size: Optional total search universe size.

    Returns:
        SearchMetrics object containing evaluation metrics.
    """
    retrieved_items = _to_iterable(records)
    relevant_items = _to_iterable(gold_standard)

    retrieved_keys = [_extract_key(item) for item in retrieved_items]
    relevant_keys = [_extract_key(item) for item in relevant_items]

    conf = confusion(retrieved_keys, relevant_keys, universe_size=universe_size)
    return conf.metrics


@dataclass
class StrategyComparison:
    """Comparison result for a search strategy variant."""

    name: str
    metrics: SearchMetrics
    is_best: bool = False

    @property
    def best(self) -> bool:
        """Alias for is_best."""
        return self.is_best

    @property
    def f1(self) -> Optional[float]:
        """Shortcut to metrics.f1."""
        return self.metrics.f1


def compare_strategies(
    results: dict[str, Any],
    gold_standard: Any,
    universe_size: Optional[int] = None,
) -> list[StrategyComparison]:
    """Compare multiple search strategy variants against a gold standard dataset.

    Args:
        results: Dictionary mapping strategy name to collection of retrieved records.
        gold_standard: Gold standard collection of relevant items.
        universe_size: Optional total search universe size.

    Returns:
        List of StrategyComparison objects sorted by F1 score in descending order,
        with the highest performing variant(s) marked with is_best=True.
    """
    comparisons = []
    for name, records in results.items():
        metrics = evaluate_strategy(records, gold_standard, universe_size=universe_size)
        comparisons.append(StrategyComparison(name=name, metrics=metrics))

    comparisons.sort(
        key=lambda c: c.metrics.f1 if c.metrics.f1 is not None else -1.0,
        reverse=True,
    )

    if comparisons:
        best_f1 = comparisons[0].metrics.f1
        if best_f1 is not None:
            for c in comparisons:
                if c.metrics.f1 == best_f1:
                    c.is_best = True
        else:
            comparisons[0].is_best = True

    return comparisons


def _extract_year(item: Any) -> Optional[Any]:
    """Extract publication year from a ReviewRecord, Article, dict, or object."""
    if isinstance(item, ReviewRecord) and item.article is not None:
        return item.article.year
    if isinstance(item, Article):
        return item.year
    if isinstance(item, dict):
        return item.get("year")
    if hasattr(item, "article") and getattr(item, "article") is not None:
        return getattr(getattr(item, "article"), "year", None)
    return getattr(item, "year", None)


def _extract_source(item: Any) -> str:
    """Extract source name from a ReviewRecord, Article, dict, or object."""
    if isinstance(item, ReviewRecord) and item.article is not None:
        art = item.article
    elif isinstance(item, Article):
        art = item
    elif isinstance(item, dict):
        s = item.get("source")
        if s is not None and str(s).strip():
            return str(s).strip()
        return "unknown"
    elif hasattr(item, "article") and getattr(item, "article") is not None:
        art = getattr(item, "article")
    else:
        art = item

    src = getattr(art, "source", None)
    if not src or not str(src).strip():
        return "unknown"
    return str(src).strip()


def coverage_by_year(records: Any) -> dict[Union[int, str], int]:
    """Compute an ordered histogram of records by publication year.

    Years with None or 0 are grouped under the key 'unknown'.

    Args:
        records: Collection of records (ReviewRecord, Article, Corpus, or iterable).

    Returns:
        Ordered dictionary mapping publication year (int) or 'unknown' (str)
        to count of records.
    """
    items = _to_iterable(records)
    counts: dict[Union[int, str], int] = {}

    for item in items:
        yr = _extract_year(item)
        if yr is None or yr == 0 or yr == "0" or yr == "":
            key: Union[int, str] = "unknown"
        else:
            try:
                key = int(yr)
                if key == 0:
                    key = "unknown"
            except (ValueError, TypeError):
                key = "unknown"

        counts[key] = counts.get(key, 0) + 1

    numeric_years = sorted([k for k in counts if isinstance(k, int)])
    result: dict[Union[int, str], int] = {y: counts[y] for y in numeric_years}
    if "unknown" in counts:
        result["unknown"] = counts["unknown"]

    return result


def coverage_by_source(records: Any) -> dict[str, int]:
    """Compute count of records grouped by search source.

    Args:
        records: Collection of records (ReviewRecord, Article, Corpus, or iterable).

    Returns:
        Ordered dictionary mapping source name to record count.
    """
    items = _to_iterable(records)
    counts: dict[str, int] = {}

    for item in items:
        src = _extract_source(item)
        counts[src] = counts.get(src, 0) + 1

    known_sources = sorted([s for s in counts if s != "unknown"])
    result: dict[str, int] = {s: counts[s] for s in known_sources}
    if "unknown" in counts:
        result["unknown"] = counts["unknown"]

    return result
