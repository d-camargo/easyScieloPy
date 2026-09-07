from pathlib import Path

import pytest

from easyscielo.review.prisma import to_png


def test_prisma_to_png(tmp_path: Path):
    pytest.importorskip("matplotlib")

    counts = {
        "identified": {"pubmed": 4, "scopus": 5, "scielo": 6},
        "total_identified": 15,
        "duplicates_removed": 3,
        "screened": 12,
        "excluded_screening": {"reason": 3},
        "total_excluded_screening": 3,
        "included": 9,
    }

    png_path = tmp_path / "prisma_diagram.png"
    to_png(counts, png_path)

    assert png_path.exists()
    assert png_path.stat().st_size > 0

    with open(png_path, "rb") as f:
        header = f.read(8)

    assert header == b"\x89PNG\r\n\x1a\n"
