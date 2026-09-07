"""Review protocol specification, serialization, and provenance generation."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import easyscielo
from easyscielo.models import Query
from easyscielo.review.models import Corpus
from easyscielo.review.screening import ScreeningCriteria

__all__ = ["ReviewProtocol", "provenance", "compute_corpus_sha256"]


@dataclass
class ReviewProtocol:
    """Dataclass defining a systematic review protocol.

    Attributes:
        title: Title of the review.
        question: Research question.
        queries: List of search query strings.
        sources: List of source names (e.g., 'search', 'articlemeta', 'oai', 'openalex', 'crossref').
        query_filters: Dictionary or Query object of filter parameters.
        criteria: ScreeningCriteria instance defining inclusion/exclusion rules.
        gold_standard: List of expected record IDs or DOIs.
    """

    title: str = ""
    question: str = ""
    queries: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    query_filters: dict[str, Any] = field(default_factory=dict)
    criteria: ScreeningCriteria = field(default_factory=ScreeningCriteria)
    gold_standard: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.query_filters, Query):
            self.query_filters = asdict(self.query_filters)
        elif self.query_filters is None:
            self.query_filters = {}

        if isinstance(self.criteria, dict):
            self.criteria = ScreeningCriteria(**self.criteria)
        elif self.criteria is None:
            self.criteria = ScreeningCriteria()

        if self.queries is None:
            self.queries = []
        if self.sources is None:
            self.sources = []
        if self.gold_standard is None:
            self.gold_standard = []

    def to_dict(self) -> dict[str, Any]:
        """Convert ReviewProtocol to a dictionary representation."""
        if isinstance(self.criteria, ScreeningCriteria):
            crit_dict = asdict(self.criteria)
        elif isinstance(self.criteria, dict):
            crit_dict = self.criteria
        else:
            crit_dict = {}

        if isinstance(self.query_filters, Query):
            qf_dict = asdict(self.query_filters)
        elif isinstance(self.query_filters, dict):
            qf_dict = self.query_filters
        else:
            qf_dict = {}

        return {
            "title": self.title,
            "question": self.question,
            "queries": list(self.queries),
            "sources": list(self.sources),
            "query_filters": qf_dict,
            "criteria": crit_dict,
            "gold_standard": list(self.gold_standard),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewProtocol":
        """Construct a ReviewProtocol from a dictionary representation."""
        crit_raw = data.get("criteria", {})
        if isinstance(crit_raw, dict):
            criteria = ScreeningCriteria(**crit_raw)
        elif isinstance(crit_raw, ScreeningCriteria):
            criteria = crit_raw
        else:
            criteria = ScreeningCriteria()

        return cls(
            title=data.get("title", ""),
            question=data.get("question", ""),
            queries=list(data.get("queries", [])),
            sources=list(data.get("sources", [])),
            query_filters=dict(data.get("query_filters", {})),
            criteria=criteria,
            gold_standard=list(data.get("gold_standard", [])),
        )

    def to_json(self, path: Optional[Union[str, Path]] = None) -> Optional[str]:
        """Serialize ReviewProtocol to JSON.

        Args:
            path: Optional file path to save the JSON output.

        Returns:
            JSON string if path is None, otherwise None after saving to file.
        """
        data = self.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if path is not None:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json_str, encoding="utf-8")
            return None
        return json_str

    @classmethod
    def from_json(cls, path_or_str: Union[str, Path]) -> "ReviewProtocol":
        """Deserialize a ReviewProtocol from a JSON file path or JSON string.

        Args:
            path_or_str: File path (str or Path) or raw JSON string.

        Returns:
            Reconstituted ReviewProtocol object.
        """
        if isinstance(path_or_str, Path):
            content = path_or_str.read_text(encoding="utf-8")
        else:
            s = str(path_or_str).strip()
            if s.startswith("{") or s.startswith("["):
                content = s
            else:
                try:
                    p = Path(path_or_str)
                    if p.exists() and p.is_file():
                        content = p.read_text(encoding="utf-8")
                    else:
                        content = s
                except (OSError, ValueError):
                    content = s
        data = json.loads(content)
        return cls.from_dict(data)


def compute_corpus_sha256(corpus: Corpus) -> str:
    """Compute deterministic SHA-256 hash of sorted record IDs in a corpus.

    Two corpora with the same records in different order will yield the same hash.
    """
    sorted_ids = sorted([r.record_id for r in corpus.records if r.record_id])
    content = "\n".join(sorted_ids).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def provenance(corpus: Corpus, protocol: ReviewProtocol) -> dict[str, Any]:
    """Generate provenance metadata for a corpus and review protocol.

    Records package version, UTC ISO-8601 timestamp, stage counts,
    source counts, and corpus_sha256. Guarantees no credentials/secrets are present.

    Args:
        corpus: Corpus instance.
        protocol: ReviewProtocol instance.

    Returns:
        Provenance metadata dictionary.
    """
    stage_counts = {
        s.name if hasattr(s, "name") else str(s): count
        for s, count in corpus.counts_by_stage().items()
    }

    source_counts: dict[str, int] = {}
    for record in corpus.records:
        src = (
            record.article.source
            if (record.article and record.article.source)
            else "unknown"
        )
        source_counts[src] = source_counts.get(src, 0) + 1

    timestamp_utc = datetime.now(timezone.utc).isoformat()

    return {
        "easyscielo_version": easyscielo.__version__,
        "easyscielo.__version__": easyscielo.__version__,
        "timestamp_utc": timestamp_utc,
        "corpus_sha256": compute_corpus_sha256(corpus),
        "stage_counts": stage_counts,
        "source_counts": source_counts,
        "protocol_title": protocol.title,
    }
