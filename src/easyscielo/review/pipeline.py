"""Systematic Review pipeline implementation."""

import inspect
import warnings
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from easyscielo import sources
from easyscielo.errors import ReviewError
from easyscielo.models import Article
from easyscielo.review.dedup import deduplicate
from easyscielo.review.metrics import SearchMetrics, evaluate_strategy
from easyscielo.review.models import Corpus, ReviewRecord, Stage, make_record_id
from easyscielo.review.protocol import ReviewProtocol, provenance
from easyscielo.review.report import render_report
from easyscielo.review.screening import screen

_ITER_ARTICLES_PARAMS = frozenset(inspect.signature(sources.iter_articles).parameters)


def _protocol_filters(protocol: ReviewProtocol) -> dict[str, Any]:
    """Return protocol query filters accepted by sources.iter_articles."""
    raw = protocol.query_filters or {}
    known = {k: v for k, v in raw.items() if k in _ITER_ARTICLES_PARAMS}
    unknown = [k for k in raw if k not in _ITER_ARTICLES_PARAMS]
    if unknown:
        warnings.warn(
            f"Ignoring unknown query filter(s) in protocol: {', '.join(sorted(unknown))}.",
            UserWarning,
            stacklevel=3,
        )
    return known


@dataclass
class ReviewResult:
    """The result of running a systematic review pipeline."""

    corpus: Corpus
    metrics: Optional[SearchMetrics] = None
    report: Optional[str] = None


class SystematicReview:
    """A systematic review pipeline with chainable stages."""

    def __init__(
        self, protocol: ReviewProtocol, *, client: Optional[Any] = None
    ) -> None:
        self.protocol = protocol
        self.client = client
        self.corpus = Corpus()
        self._completed_stages: set[str] = set()
        self._last_metrics: Optional[SearchMetrics] = None
        self._last_report: Optional[str] = None

    def identify(self) -> "SystematicReview":
        """Run each query in each source to identify articles."""
        filters = _protocol_filters(self.protocol)

        if not self.protocol.sources:
            self._completed_stages.add("identify")
            return self

        for source in self.protocol.sources:
            for query in self.protocol.queries:
                for article in sources.iter_articles(
                    query, sources=[source], **filters
                ):
                    if not article.source:
                        article.source = source
                    record = ReviewRecord(
                        record_id=make_record_id(article),
                        article=article,
                        stage=Stage.IDENTIFIED,
                        source_db=source,
                    )
                    self.corpus.records.append(record)

        self._completed_stages.add("identify")
        return self

    def add_source(
        self, records: Iterable[Union[Article, ReviewRecord]]
    ) -> "SystematicReview":
        """Add manually imported records to the corpus."""
        # It's an independent or chainable stage, assume it sets identify stage if not already
        if "identify" not in self._completed_stages:
            self._completed_stages.add("identify")

        for item in records:
            if isinstance(item, Article):
                rec = ReviewRecord(
                    record_id=make_record_id(item),
                    article=item,
                    stage=Stage.IDENTIFIED,
                )
            elif isinstance(item, ReviewRecord):
                rec = item
                rec.stage = Stage.IDENTIFIED
            else:
                raise TypeError(f"Expected ReviewRecord or Article, got {type(item)}")
            self.corpus.records.append(rec)

        return self

    def deduplicate(self, **kw: Any) -> "SystematicReview":
        """Deduplicate records in the corpus."""
        if "identify" not in self._completed_stages:
            raise ReviewError("Missing stage: identify()")

        result = deduplicate(self.corpus.records, **kw)
        self.corpus.records = result.unique + result.duplicates

        self._completed_stages.add("deduplicate")
        return self

    def screen(self) -> "SystematicReview":
        """Screen records based on criteria."""
        if "deduplicate" not in self._completed_stages:
            raise ReviewError("Missing stage: deduplicate()")

        unique_records = [r for r in self.corpus.records if r.duplicate_of is None]
        duplicates = [r for r in self.corpus.records if r.duplicate_of is not None]

        screened_unique = screen(unique_records, self.protocol.criteria)
        for rec in screened_unique:
            rec.stage = Stage.SCREENED
            if rec.decision is not None:
                if rec.decision.name == "INCLUDE":
                    rec.stage = Stage.INCLUDED
                elif rec.decision.name == "EXCLUDE":
                    rec.stage = Stage.EXCLUDED

        self.corpus.records = screened_unique + duplicates

        self._completed_stages.add("screen")
        return self

    def evaluate(self, universe_size: Optional[int] = None) -> "SystematicReview":
        """Evaluate the review against a gold standard."""
        if "screen" not in self._completed_stages:
            raise ReviewError("Missing stage: screen()")

        if self.protocol.gold_standard:
            self._last_metrics = evaluate_strategy(
                self.corpus, self.protocol.gold_standard, universe_size=universe_size
            )

        self._completed_stages.add("evaluate")
        return self

    def report(self, fmt: str = "md") -> "SystematicReview":
        """Generate a review report."""
        if "evaluate" not in self._completed_stages:
            raise ReviewError("Missing stage: evaluate()")

        from easyscielo.review.prisma import prisma_counts

        self._last_report = render_report(
            corpus=self.corpus,
            protocol=self.protocol,
            counts=prisma_counts(self.corpus),
            metrics=self._last_metrics,
            provenance=provenance(self.corpus, self.protocol),
            fmt=fmt,
        )
        self._completed_stages.add("report")
        return self

    def run(self) -> ReviewResult:
        """Run the full pipeline and return ReviewResult."""
        self.identify()
        self.deduplicate()
        self.screen()
        self.evaluate()
        self.report()
        return ReviewResult(
            corpus=self.corpus,
            metrics=self._last_metrics,
            report=self._last_report,
        )
