"""Command-line interface for easyscielo."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from easyscielo.api import search_scielo
from easyscielo.errors import BlockedError, ScieloError
from easyscielo.frame import to_csv, to_csv_string


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for easyscielo CLI."""
    parser = argparse.ArgumentParser(
        prog="easyscielo",
        description="CLI for searching and retrieving scientific articles from SciELO.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-command to execute")

    search_parser = subparsers.add_parser(
        "search", help="Search SciELO for articles matching a query."
    )
    search_parser.add_argument("query", help="Search query string")
    search_parser.add_argument(
        "--backend",
        default="search",
        help="Search backend to use (default: 'search')",
    )
    search_parser.add_argument(
        "--collection",
        default=None,
        help="Filter by collection code or country name (e.g. 'cri', 'mex')",
    )
    search_parser.add_argument(
        "--language",
        default=None,
        help="Filter by language code (e.g. 'es', 'pt', 'en')",
    )
    search_parser.add_argument(
        "--year-start",
        type=int,
        default=None,
        help="Filter start year (e.g. 2015)",
    )
    search_parser.add_argument(
        "--year-end",
        type=int,
        default=None,
        help="Filter end year (e.g. 2020)",
    )
    search_parser.add_argument(
        "--n-max",
        type=int,
        default=None,
        help="Maximum number of results to return",
    )
    search_parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="json",
        help="Output format (default: 'json')",
    )
    search_parser.add_argument(
        "--out",
        default=None,
        help="Path to output file. If omitted, outputs to stdout.",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for easyscielo CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "search":
        try:
            articles = search_scielo(
                query=args.query,
                backend=args.backend,
                collections=args.collection,
                languages=args.language,
                year_start=args.year_start,
                year_end=args.year_end,
                n_max=args.n_max,
            )
        except BlockedError as e:
            sys.stderr.write(f"Blocked: {e}\n")
            return 2
        except ScieloError as e:
            sys.stderr.write(f"Error: {e}\n")
            return 1

        if args.format == "csv":
            if args.out:
                to_csv(articles, args.out)
            else:
                sys.stdout.write(to_csv_string(articles))
        else:
            data = [a.as_dict() for a in articles]
            content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            if args.out:
                Path(args.out).write_text(content, encoding="utf-8")
            else:
                sys.stdout.write(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
