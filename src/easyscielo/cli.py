"""Command-line interface for easyscielo."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from easyscielo.api import search_scielo
from easyscielo.errors import BlockedError, ReviewError, ScieloError
from easyscielo.frame import to_csv, to_csv_string
from easyscielo.sources import search_articles


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
        default=None,
        help="Search backend to use (default: 'search')",
    )
    search_parser.add_argument(
        "--source",
        action="append",
        default=None,
        help=(
            "Search source to use (repeatable, default: 'crossref' since "
            "2026-09-07 because SciELO blocks automated requests)"
        ),
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

    subparsers.add_parser("sources", help="List available article sources.")

    # Systematic Review subcommands
    review_parser = subparsers.add_parser(
        "review", help="Systematic review commands and workflows."
    )
    review_subparsers = review_parser.add_subparsers(
        dest="review_subcommand", help="Review sub-command to execute"
    )

    run_parser = review_subparsers.add_parser(
        "run", help="Run a systematic review pipeline from a protocol file."
    )
    run_parser.add_argument(
        "--protocol",
        required=True,
        help="Path to review protocol JSON file",
    )
    run_parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory path for review artifacts",
    )

    dedup_parser = review_subparsers.add_parser(
        "dedup", help="Deduplicate a standalone RIS, BibTeX, or CSV file."
    )
    dedup_parser.add_argument("entrada", help="Input file path (RIS, BibTeX, or CSV)")
    dedup_parser.add_argument(
        "--out",
        required=True,
        help="Output file path",
    )

    metrics_parser = review_subparsers.add_parser(
        "metrics", help="Evaluate corpus metrics against a gold standard."
    )
    metrics_parser.add_argument(
        "corpus", help="Corpus file path (CSV, RIS, BibTeX, or JSON)"
    )
    metrics_parser.add_argument(
        "--gold",
        required=True,
        help="Gold standard file path (TXT, CSV, RIS, or BibTeX)",
    )

    return parser


def print_sources() -> None:
    """Print available sources and their details."""
    sources_info = [
        ("search", "SciELO Search (HTML)", "Não precisa de extra/credencial"),
        ("articlemeta", "SciELO ArticleMeta API", "Não precisa de extra/credencial"),
        ("oai", "SciELO OAI-PMH", "Não precisa de extra/credencial"),
        (
            "openalex",
            "OpenAlex API",
            "Requer extra 'openalex' (pyalex); credenciais opcionais",
        ),
        ("crossref", "Crossref API", "Não precisa de extra; mailto opcional"),
    ]
    for name, base, extra in sources_info:
        sys.stdout.write(f"{name}: {base} - {extra}\n")


def _run_review(protocol_path: str, out_dir_path: str) -> None:
    """Execute 'easyscielo review run' subcommand."""
    from easyscielo.review.exporters import to_review_csv, to_ris
    from easyscielo.review.pipeline import SystematicReview
    from easyscielo.review.prisma import prisma_counts
    from easyscielo.review.protocol import ReviewProtocol, provenance

    protocol = ReviewProtocol.from_json(protocol_path)
    review = SystematicReview(protocol)
    result = review.run()

    out_dir = Path(out_dir_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. corpus.csv
    to_review_csv(result.corpus.records, out_dir / "corpus.csv")

    # 2. included.ris
    included = [
        r
        for r in result.corpus.records
        if getattr(r.stage, "name", str(r.stage)) == "INCLUDED"
        or (
            getattr(r, "decision", None)
            and getattr(r.decision, "name", str(r.decision)) == "INCLUDE"
        )
    ]
    to_ris(included, out_dir / "included.ris")

    # 3. prisma.json
    p_counts = prisma_counts(result.corpus)
    (out_dir / "prisma.json").write_text(
        json.dumps(p_counts, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 4. report.md
    report_text = result.report or ""
    (out_dir / "report.md").write_text(report_text, encoding="utf-8")

    # 5. provenance.json
    prov = provenance(result.corpus, protocol)
    (out_dir / "provenance.json").write_text(
        json.dumps(prov, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _dedup_review(entrada_path_str: str, out_path_str: str) -> None:
    """Execute 'easyscielo review dedup' subcommand."""
    from easyscielo.review.dedup import deduplicate
    from easyscielo.review.exporters import to_bibtex, to_review_csv, to_ris
    from easyscielo.review.importers import from_bibtex, from_csv, from_ris

    entrada_path = Path(entrada_path_str)
    saida_path = Path(out_path_str)

    ext_in = entrada_path.suffix.lower()
    if ext_in == ".ris":
        records = from_ris(entrada_path)
    elif ext_in in (".bib", ".bibtex"):
        records = from_bibtex(entrada_path)
    elif ext_in == ".csv":
        records = from_csv(entrada_path)
    else:
        content = entrada_path.read_text(encoding="utf-8")
        if "TY  -" in content or content.strip().startswith("TY "):
            records = from_ris(entrada_path)
        elif "@" in content:
            records = from_bibtex(entrada_path)
        else:
            records = from_csv(entrada_path)

    res = deduplicate(records)
    unique_records = res.unique

    saida_path.parent.mkdir(parents=True, exist_ok=True)
    ext_out = saida_path.suffix.lower()
    if ext_out == ".ris":
        to_ris(unique_records, saida_path)
    elif ext_out in (".bib", ".bibtex"):
        to_bibtex(unique_records, saida_path)
    else:
        to_review_csv(unique_records, saida_path)


def _format_metrics_table(metrics) -> str:
    """Format SearchMetrics into a plain text markdown table."""

    def fmt_val(val, prec=4):
        if val is None:
            return "N/A"
        return f"{val:.{prec}f}"

    lines = [
        "| Métrica | Valor |",
        "| --- | --- |",
        f"| Precisão | {fmt_val(metrics.precision)} |",
        f"| Recall | {fmt_val(metrics.recall)} |",
        f"| Especificidade | {fmt_val(metrics.specificity)} |",
        f"| F1 | {fmt_val(metrics.f1)} |",
        f"| Acurácia | {fmt_val(metrics.accuracy)} |",
        f"| NNR | {fmt_val(metrics.nnr, 2)} |",
    ]
    if metrics.confusion:
        lines.append(f"| TP | {metrics.confusion.tp} |")
        lines.append(f"| FP | {metrics.confusion.fp} |")
        lines.append(f"| FN | {metrics.confusion.fn} |")
        tn_val = metrics.confusion.tn
        tn_str = str(tn_val) if tn_val is not None else "N/A"
        lines.append(f"| TN | {tn_str} |")

    return "\n".join(lines) + "\n"


def _metrics_review(corpus_path_str: str, gold_path_str: str) -> None:
    """Execute 'easyscielo review metrics' subcommand."""
    from easyscielo.review.importers import from_bibtex, from_csv, from_ris
    from easyscielo.review.metrics import evaluate_strategy

    corpus_path = Path(corpus_path_str)
    gold_path = Path(gold_path_str)

    # 1. Corpus records
    corpus_records: list[Any] = []
    ext_c = corpus_path.suffix.lower()
    if ext_c == ".csv":
        corpus_records = from_csv(corpus_path)
    elif ext_c == ".ris":
        corpus_records = from_ris(corpus_path)
    elif ext_c in (".bib", ".bibtex"):
        corpus_records = from_bibtex(corpus_path)
    elif ext_c == ".json":
        content = corpus_path.read_text(encoding="utf-8")
        raw = json.loads(content)
        if isinstance(raw, list):
            from easyscielo.models import Article
            from easyscielo.review.models import ReviewRecord, Stage, make_record_id

            for item in raw:
                if isinstance(item, dict):
                    art = Article(
                        title=item.get("title", ""),
                        authors=item.get("authors", []),
                        year=item.get("year", 0),
                        doi=item.get("doi"),
                        abstract=item.get("abstract"),
                    )
                    rec_id = item.get("record_id") or make_record_id(art)
                    corpus_records.append(
                        ReviewRecord(
                            record_id=rec_id,
                            article=art,
                            stage=Stage.IDENTIFIED,
                        )
                    )
                else:
                    corpus_records.append(str(item))
        else:
            corpus_records = [content]
    else:
        content = corpus_path.read_text(encoding="utf-8")
        if "TY  -" in content:
            corpus_records = from_ris(corpus_path)
        elif "@" in content:
            corpus_records = from_bibtex(corpus_path)
        else:
            corpus_records = from_csv(corpus_path)

    # 2. Gold standard records
    gold_records: list[Any] = []
    ext_g = gold_path.suffix.lower()

    if ext_g == ".txt":
        gold_records = [
            line.strip()
            for line in gold_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    elif ext_g == ".csv":
        gold_records = from_csv(gold_path)
    elif ext_g == ".ris":
        gold_records = from_ris(gold_path)
    elif ext_g in (".bib", ".bibtex"):
        gold_records = from_bibtex(gold_path)
    else:
        content = gold_path.read_text(encoding="utf-8")
        if "TY  -" in content:
            gold_records = from_ris(gold_path)
        elif "@" in content:
            gold_records = from_bibtex(gold_path)
        elif "," in content and "\n" in content:
            gold_records = from_csv(gold_path)
        else:
            gold_records = [
                line.strip() for line in content.splitlines() if line.strip()
            ]

    metrics = evaluate_strategy(corpus_records, gold_records)
    sys.stdout.write(_format_metrics_table(metrics))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for easyscielo CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    try:
        if args.subcommand == "search":
            if args.backend is not None and args.source is not None:
                sys.stderr.write("Error: Cannot specify both --backend and --source.\n")
                return 1

            if args.backend is not None:
                articles = search_scielo(
                    query=args.query,
                    backend=args.backend,
                    collections=args.collection,
                    languages=args.language,
                    year_start=args.year_start,
                    year_end=args.year_end,
                    n_max=args.n_max,
                )
            else:
                sources = args.source if args.source is not None else ["crossref"]
                articles = search_articles(
                    query=args.query,
                    sources=sources,
                    collections=args.collection,
                    languages=args.language,
                    year_start=args.year_start,
                    year_end=args.year_end,
                    n_max=args.n_max,
                )

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

        elif args.subcommand == "sources":
            print_sources()

        elif args.subcommand == "review":
            if not args.review_subcommand:
                parser.print_help()
                return 0

            if args.review_subcommand == "run":
                _run_review(args.protocol, args.out_dir)
            elif args.review_subcommand == "dedup":
                _dedup_review(args.entrada, args.out)
            elif args.review_subcommand == "metrics":
                _metrics_review(args.corpus, args.gold)

    except BlockedError as e:
        sys.stderr.write(f"Blocked: {e}\n")
        return 2
    except ReviewError as e:
        sys.stderr.write(f"ReviewError: {e}\n")
        return 2
    except ImportError as e:
        sys.stderr.write(f"ImportError: {e}\n")
        return 2
    except ScieloError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
