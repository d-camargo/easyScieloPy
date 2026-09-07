import enum
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from easyscielo.models import Article


class Stage(enum.Enum):
    """The stages of a review process."""

    IDENTIFIED = "IDENTIFIED"
    DEDUPLICATED = "DEDUPLICATED"
    SCREENED = "SCREENED"
    INCLUDED = "INCLUDED"
    EXCLUDED = "EXCLUDED"


class Decision(enum.Enum):
    """The decision made during a review stage."""

    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    MAYBE = "MAYBE"


def make_record_id(article: Article) -> str:
    """Generate a stable 16-hex record ID for an Article."""
    if article.doi:
        key = article.doi.lower().strip()
    else:
        title = article.title.lower().strip() if article.title else ""
        year = str(article.year)
        author = article.authors[0].lower().strip() if article.authors else ""
        key = f"{title}|{year}|{author}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass
class ReviewRecord:
    """A record linking an Article to its review state."""

    record_id: str
    article: Article
    stage: Stage
    source_db: Optional[str] = None
    decision: Optional[Decision] = None
    duplicate_of: Optional[str] = None
    decision_reason: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        """Flatten the article and append review columns."""
        d = self.article.as_dict()
        d["record_id"] = self.record_id
        d["stage"] = self.stage.name
        d["source_db"] = self.source_db
        d["decision"] = self.decision.name if self.decision else None
        d["duplicate_of"] = self.duplicate_of
        d["decision_reason"] = self.decision_reason
        return d


@dataclass
class Corpus:
    """A collection of ReviewRecords."""

    records: list[ReviewRecord] = field(default_factory=list)

    def counts_by_stage(self) -> dict[Stage, int]:
        """Count records by their current stage."""
        counts = {stage: 0 for stage in Stage}
        for record in self.records:
            counts[record.stage] += 1
        return counts

    def filter_by(self, stage: Stage) -> list[ReviewRecord]:
        """Return a list of records in the given stage."""
        return [r for r in self.records if r.stage == stage]
