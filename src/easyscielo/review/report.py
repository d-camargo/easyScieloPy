"""Report generation for systematic reviews using Jinja2 templates."""

from pathlib import Path
from typing import Any, Optional

from easyscielo._optional import require
from easyscielo.review.metrics import coverage_by_source, coverage_by_year
from easyscielo.review.prisma import to_mermaid

__all__ = ["render_report"]


def render_report(
    corpus: Any = None,
    counts: Optional[dict[str, Any]] = None,
    metrics: Any = None,
    protocol: Any = None,
    provenance: Optional[dict[str, Any]] = None,
    fmt: str = "md",
) -> str:
    """Render systematic review report using Jinja2 templates.

    Args:
        corpus: Corpus instance or iterable of records. If None, coverage section is omitted.
        counts: PRISMA counts dictionary. If None, PRISMA flow section is omitted.
        metrics: SearchMetrics, dict, or list of StrategyComparison. If None, metrics section is omitted.
        protocol: ReviewProtocol instance or dict. If None, protocol section is omitted.
        provenance: Provenance dictionary. If None, provenance section is omitted.
        fmt: Target format ("md" or "html"). Defaults to "md".

    Returns:
        Rendered report string in Markdown or HTML format.

    Raises:
        ImportError: If jinja2 is not installed.
        ValueError: If fmt is unsupported.
    """
    require("jinja2", "review")
    import jinja2

    fmt_clean = fmt.lower().strip()
    if fmt_clean in ("md", "markdown"):
        template_name = "report.md.j2"
    elif fmt_clean == "html":
        template_name = "report.html.j2"
    else:
        raise ValueError(f"Unsupported format: '{fmt}'. Expected 'md' or 'html'.")

    template_dir = Path(__file__).parent / "templates"
    loader: Any
    try:
        loader = jinja2.PackageLoader("easyscielo.review", "templates")
    except Exception:
        loader = jinja2.FileSystemLoader(template_dir)

    env = jinja2.Environment(
        loader=loader,
        autoescape=jinja2.select_autoescape(["html", "xml"])
        if fmt_clean == "html"
        else False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_name)

    # Process protocol
    protocol_data = None
    if protocol is not None:
        if hasattr(protocol, "to_dict") and callable(protocol.to_dict):
            protocol_data = protocol.to_dict()
        elif isinstance(protocol, dict):
            protocol_data = protocol
        else:
            protocol_data = protocol

    # Process counts and mermaid diagram
    counts_data = None
    mermaid_diagram = None
    if counts is not None:
        counts_data = counts
        mermaid_diagram = to_mermaid(counts)

    # Process metrics
    metrics_data = None
    metrics_is_list = False
    if metrics is not None:
        metrics_data = metrics
        if isinstance(metrics, (list, tuple)):
            metrics_is_list = True

    # Process corpus coverage
    cov_year = None
    cov_source = None
    if corpus is not None:
        try:
            cov_year = coverage_by_year(corpus)
        except Exception:
            cov_year = None
        try:
            cov_source = coverage_by_source(corpus)
        except Exception:
            cov_source = None

    # Process provenance
    provenance_data = None
    if provenance is not None:
        if hasattr(provenance, "to_dict") and callable(provenance.to_dict):
            provenance_data = provenance.to_dict()
        elif isinstance(provenance, dict):
            provenance_data = provenance
        else:
            provenance_data = provenance

    context = {
        "corpus": corpus,
        "counts": counts_data,
        "mermaid_diagram": mermaid_diagram,
        "metrics": metrics_data,
        "metrics_is_list": metrics_is_list,
        "protocol": protocol_data,
        "provenance": provenance_data,
        "coverage_by_year": cov_year,
        "coverage_by_source": cov_source,
    }

    return template.render(**context)
