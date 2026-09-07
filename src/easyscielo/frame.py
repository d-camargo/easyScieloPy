"""CSV and DataFrame export functionality for easyscielo."""

import csv
import io
from pathlib import Path
from typing import Any, Iterable, TextIO

from easyscielo.models import Article

DEFAULT_COLUMNS = ["title", "authors", "year", "doi", "abstract"]


def write_csv(articles: Iterable[Article], fileobj: TextIO) -> None:
    """Write articles as CSV to a text file object.

    Column order is determined by Article.as_dict().
    """
    rows = [a.as_dict() for a in articles]
    fieldnames = list(rows[0].keys()) if rows else DEFAULT_COLUMNS
    writer = csv.DictWriter(fileobj, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


def to_dataframe(articles: Iterable[Article]) -> Any:
    """Convert an iterable of Article objects into a pandas DataFrame.

    Requires pandas to be installed. If pandas is not available, raises an ImportError
    with installation instructions.
    """
    try:
        import pandas as pd  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "pandas is required for to_dataframe(). "
            "Please install it using 'pip install easyscielopy[pandas]'."
        ) from e

    return pd.DataFrame([a.as_dict() for a in articles])


def to_csv(articles: Iterable[Article], path: str | Path) -> None:
    """Export an iterable of Article objects to a CSV file using stdlib only."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        write_csv(articles, f)


def to_csv_string(articles: Iterable[Article]) -> str:
    """Render articles as a CSV string (same layout as to_csv)."""
    buf = io.StringIO()
    write_csv(articles, buf)
    return buf.getvalue()
