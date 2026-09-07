"""PRISMA 2020 reporting and diagram generation for systematic reviews."""

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional, Union

from easyscielo._optional import require
from easyscielo.models import Article
from easyscielo.review.dedup import DedupResult
from easyscielo.review.models import (
    Corpus,
    Decision,
    ReviewRecord,
    Stage,
    make_record_id,
)

__all__ = ["prisma_counts", "to_mermaid", "to_png"]


def _get_source_db(item: Union[ReviewRecord, Article]) -> str:
    """Extract database source name from a ReviewRecord or Article."""
    if isinstance(item, ReviewRecord):
        if item.source_db:
            return str(item.source_db)
        art = item.article
    else:
        art = item

    if getattr(art, "source", None):
        return str(art.source)
    if getattr(art, "collection", None):
        return str(art.collection)
    return "unknown"


def prisma_counts(
    corpus: Union[Corpus, Iterable[Union[ReviewRecord, Article]]],
    dedup_result: Optional[Union[DedupResult, int, Any]] = None,
) -> dict[str, Any]:
    """Calculate PRISMA 2020 flow metrics from review stages and decisions.

    Args:
        corpus: Corpus instance or iterable of ReviewRecord / Article objects.
        dedup_result: Optional DedupResult instance or integer count of removed duplicates.

    Returns:
        Dict containing PRISMA counts:
        - 'identified': dict mapping source_db -> count of records identified
        - 'total_identified': int sum of identified records
        - 'duplicates_removed': int count of duplicate records removed
        - 'screened': int count of screened records (total_identified - duplicates_removed)
        - 'excluded_screening': dict mapping decision_reason -> count of excluded records
        - 'total_excluded_screening': int sum of excluded records during screening
        - 'included': int count of included records
    """
    if isinstance(corpus, Corpus):
        records = list(corpus.records)
    elif isinstance(corpus, Iterable):
        raw_list = list(corpus)
        records = []
        for item in raw_list:
            if isinstance(item, Article):
                records.append(
                    ReviewRecord(
                        record_id=make_record_id(item),
                        article=item,
                        stage=Stage.IDENTIFIED,
                    )
                )
            elif isinstance(item, ReviewRecord):
                records.append(item)
            else:
                raise TypeError(f"Expected ReviewRecord or Article, got {type(item)}")
    else:
        raise TypeError(f"Expected Corpus or Iterable, got {type(corpus)}")

    extra_duplicates: list[Union[ReviewRecord, Article]] = []
    duplicates_removed = 0

    if dedup_result is not None:
        if isinstance(dedup_result, int):
            duplicates_removed = dedup_result
        elif hasattr(dedup_result, "duplicates"):
            extra_duplicates = getattr(dedup_result, "duplicates") or []
            duplicates_removed = len(extra_duplicates)
        elif isinstance(dedup_result, dict) and "duplicates" in dedup_result:
            extra_duplicates = dedup_result["duplicates"]
            duplicates_removed = len(extra_duplicates)

    all_identified_records: list[Union[ReviewRecord, Article]] = list(records)
    seen_ids = {
        r.record_id if isinstance(r, ReviewRecord) else make_record_id(r)
        for r in records
    }

    for dup in extra_duplicates:
        dup_id = dup.record_id if isinstance(dup, ReviewRecord) else make_record_id(dup)
        if dup_id not in seen_ids:
            all_identified_records.append(dup)
            seen_ids.add(dup_id)

    if dedup_result is None:
        duplicates_removed = sum(
            1
            for r in all_identified_records
            if isinstance(r, ReviewRecord) and r.duplicate_of is not None
        )

    identified: dict[str, int] = defaultdict(int)
    for r in all_identified_records:
        source_db = _get_source_db(r)
        identified[source_db] += 1

    identified_dict = dict(identified)
    total_identified = sum(identified_dict.values())
    screened = total_identified - duplicates_removed

    excluded_screening: dict[str, int] = defaultdict(int)
    included = 0

    for r in all_identified_records:
        if isinstance(r, ReviewRecord):
            if r.duplicate_of is not None:
                continue
            if r.decision == Decision.EXCLUDE or r.stage == Stage.EXCLUDED:
                reason = r.decision_reason or "unspecified"
                excluded_screening[reason] += 1
            elif r.decision == Decision.INCLUDE or r.stage == Stage.INCLUDED:
                included += 1

    excluded_dict = dict(excluded_screening)
    total_excluded = sum(excluded_dict.values())

    return {
        "identified": identified_dict,
        "total_identified": total_identified,
        "duplicates_removed": duplicates_removed,
        "screened": screened,
        "excluded_screening": excluded_dict,
        "total_excluded_screening": total_excluded,
        "included": included,
    }


def to_mermaid(counts: dict[str, Any]) -> str:
    """Generate a pure-text Mermaid flowchart TD diagram for PRISMA 2020 flow.

    Args:
        counts: Dictionary containing PRISMA counts from prisma_counts().

    Returns:
        String containing Mermaid diagram definition (flowchart TD).
    """
    lines = ["flowchart TD"]

    identified = counts.get("identified", {})
    total_identified = counts.get(
        "total_identified",
        sum(identified.values()) if isinstance(identified, dict) else 0,
    )
    duplicates_removed = counts.get("duplicates_removed", 0)
    screened = counts.get("screened", 0)
    excluded_screening = counts.get("excluded_screening", {})
    included = counts.get("included", 0)

    source_node_ids = []
    if isinstance(identified, dict) and identified:
        lines.append('    subgraph Identification["Identification"]')
        for i, (source, count) in enumerate(identified.items()):
            node_id = f"source_{i}"
            source_node_ids.append(node_id)
            safe_source = str(source).replace('"', "'")
            lines.append(f'        {node_id}["{safe_source} (n = {count})"]')
        lines.append("    end")
        lines.append(f'    total_id["Total Identified (n = {total_identified})"]')
        for node_id in source_node_ids:
            lines.append(f"    {node_id} --> total_id")
    else:
        lines.append(f'    total_id["Total Identified (n = {total_identified})"]')

    lines.append(f'    dedup["Duplicates Removed (n = {duplicates_removed})"]')
    lines.append("    total_id --> dedup")
    lines.append(f'    screened["Records Screened (n = {screened})"]')
    lines.append("    total_id --> screened")

    ex_node_ids = []
    if isinstance(excluded_screening, dict) and excluded_screening:
        lines.append('    subgraph Excluded["Excluded during Screening"]')
        for i, (reason, count) in enumerate(excluded_screening.items()):
            node_id = f"ex_{i}"
            ex_node_ids.append(node_id)
            safe_reason = str(reason).replace('"', "'")
            lines.append(f'        {node_id}["{safe_reason} (n = {count})"]')
        lines.append("    end")
        for node_id in ex_node_ids:
            lines.append(f"    screened --> {node_id}")

    lines.append(f'    included["Records Included (n = {included})"]')
    lines.append("    screened --> included")

    return "\n".join(lines)


def to_png(counts: dict[str, Any], path: Union[str, Path]) -> None:
    """Generate a PNG diagram representing the 4 PRISMA flow phases using matplotlib.

    Args:
        counts: Dictionary containing PRISMA counts from prisma_counts().
        path: File path or Path object where the PNG image will be saved.
    """
    mpl = require("matplotlib", "plots")
    mpl.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[import-untyped]

    total_identified = counts.get("total_identified", 0)
    screened = counts.get("screened", 0)
    excluded = counts.get("total_excluded_screening", 0)
    included = counts.get("included", 0)

    phases = [
        ("1. Identification", f"Identified (n = {total_identified})"),
        ("2. Screening", f"Screened (n = {screened})"),
        ("3. Exclusion", f"Excluded (n = {excluded})"),
        ("4. Inclusion", f"Included (n = {included})"),
    ]

    fig, ax = plt.subplots(figsize=(6, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    y_positions = [8.0, 6.0, 4.0, 2.0]

    for i, (title, text) in enumerate(phases):
        y = y_positions[i]
        label = f"{title}\n{text}"
        ax.text(
            5.0,
            y,
            label,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.6",
                facecolor="#e0f2fe",
                edgecolor="#0284c7",
                lw=1.5,
            ),
            fontsize=11,
            fontweight="bold",
        )
        if i < len(y_positions) - 1:
            ax.annotate(
                "",
                xy=(5.0, y_positions[i + 1] + 0.6),
                xytext=(5.0, y - 0.6),
                arrowprops=dict(arrowstyle="->", lw=1.5, color="#334155"),
            )

    plt.tight_layout()
    try:
        fig.savefig(path, format="png", dpi=150)
    finally:
        plt.close(fig)
