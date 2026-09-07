"""Deduplication functions for systematic reviews."""

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional, Union

from easyscielo._optional import require
from easyscielo.models import Article
from easyscielo.review.models import ReviewRecord, Stage, make_record_id
from easyscielo.review.normalize import blocking_key, normalize_doi, normalize_title

__all__ = ["DedupResult", "deduplicate"]


@dataclass
class DedupResult:
    """Container for deduplication results for PRISMA reporting."""

    unique: list[ReviewRecord] = field(default_factory=list)
    duplicates: list[ReviewRecord] = field(default_factory=list)
    groups: list[list[ReviewRecord]] = field(default_factory=list)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> None:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


def _count_filled_fields(article: Article) -> int:
    """Count the number of non-empty / non-None fields in an Article."""
    count = 0
    for _key, value in asdict(article).items():
        if value is None:
            continue
        if isinstance(value, (str, list, dict, set, tuple)):
            if len(value) > 0:
                count += 1
        else:
            count += 1
    return count


def deduplicate(
    records: Iterable[Union[ReviewRecord, Article]],
    *,
    threshold: float = 0.92,
    fuzzy: bool = True,
) -> DedupResult:
    """Deduplicate records in three passes (DOI -> Title+Year -> Fuzzy Title).

    Args:
        records: Collection of ReviewRecord or Article instances.
        threshold: Fuzzy similarity threshold (0.0 to 1.0 or 0 to 100). Default 0.92.
        fuzzy: If True, execute the third fuzzy comparison pass using rapidfuzz.

    Returns:
        DedupResult containing unique records, duplicate records, and PRISMA groups.
    """
    rec_list: list[ReviewRecord] = []
    for item in records:
        if isinstance(item, Article):
            rec_list.append(
                ReviewRecord(
                    record_id=make_record_id(item),
                    article=item,
                    stage=Stage.DEDUPLICATED,
                )
            )
        elif isinstance(item, ReviewRecord):
            item.stage = Stage.DEDUPLICATED
            rec_list.append(item)
        else:
            raise TypeError(f"Expected ReviewRecord or Article, got {type(item)}")

    if not rec_list:
        return DedupResult(unique=[], duplicates=[], groups=[])

    n = len(rec_list)
    uf = _UnionFind(n)

    # --- Pass 1: Identical Normalized DOI ---
    doi_map: dict[str, int] = {}
    for i, rec in enumerate(rec_list):
        doi_norm = normalize_doi(rec.article.doi)
        if doi_norm:
            if doi_norm in doi_map:
                uf.union(i, doi_map[doi_norm])
            else:
                doi_map[doi_norm] = i

    # --- Pass 2: Identical Normalized Title + Year ---
    title_year_map: dict[tuple[str, Optional[int]], int] = {}
    for i, rec in enumerate(rec_list):
        t_norm = normalize_title(rec.article.title)
        year = rec.article.year
        if t_norm and year is not None:
            key = (t_norm, year)
            if key in title_year_map:
                uf.union(i, title_year_map[key])
            else:
                title_year_map[key] = i

    # --- Pass 3: Fuzzy comparison on title within blocking_key ---
    if fuzzy:
        rapidfuzz = require("rapidfuzz", "review")
        token_sort_ratio = rapidfuzz.fuzz.token_sort_ratio

        target_threshold = threshold * 100.0 if threshold <= 1.0 else float(threshold)

        blocking_buckets: dict[str, list[int]] = defaultdict(list)
        for i, rec in enumerate(rec_list):
            b_key = blocking_key(rec.article)
            if b_key:
                blocking_buckets[b_key].append(i)

        for bucket in blocking_buckets.values():
            m = len(bucket)
            if m < 2:
                continue
            for idx_a in range(m):
                i = bucket[idx_a]
                t1 = normalize_title(rec_list[i].article.title)
                if not t1:
                    continue
                for idx_b in range(idx_a + 1, m):
                    j = bucket[idx_b]
                    if uf.find(i) == uf.find(j):
                        continue
                    t2 = normalize_title(rec_list[j].article.title)
                    if not t2:
                        continue
                    score = token_sort_ratio(t1, t2)
                    if score >= target_threshold:
                        uf.union(i, j)

    # --- Group records by Union-Find root parent ---
    clusters: dict[int, list[ReviewRecord]] = defaultdict(list)
    for i, rec in enumerate(rec_list):
        root = uf.find(i)
        clusters[root].append(rec)

    unique: list[ReviewRecord] = []
    duplicates: list[ReviewRecord] = []
    groups: list[list[ReviewRecord]] = []

    seen_roots: set[int] = set()
    for i, rec in enumerate(rec_list):
        root = uf.find(i)
        if root in seen_roots:
            continue
        seen_roots.add(root)
        cluster = clusters[root]

        canonical = max(cluster, key=lambda r: _count_filled_fields(r.article))

        group_records = [canonical]
        for item in cluster:
            if item is not canonical:
                item.duplicate_of = canonical.record_id
                group_records.append(item)
                duplicates.append(item)

        canonical.duplicate_of = None
        unique.append(canonical)
        groups.append(group_records)

    return DedupResult(unique=unique, duplicates=duplicates, groups=groups)
