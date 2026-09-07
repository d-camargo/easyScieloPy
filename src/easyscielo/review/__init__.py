"""Systematic review subpackage for easyscielopy."""

from easyscielo.review.dedup import deduplicate
from easyscielo.review.exporters import to_bibtex, to_ris
from easyscielo.review.importers import from_bibtex, from_ris
from easyscielo.review.metrics import evaluate_strategy
from easyscielo.review.models import Corpus, ReviewRecord
from easyscielo.review.pipeline import SystematicReview
from easyscielo.review.prisma import prisma_counts
from easyscielo.review.protocol import ReviewProtocol
from easyscielo.review.screening import ScreeningCriteria

__all__ = [
    "SystematicReview",
    "ReviewProtocol",
    "ReviewRecord",
    "Corpus",
    "ScreeningCriteria",
    "deduplicate",
    "evaluate_strategy",
    "prisma_counts",
    "from_ris",
    "from_bibtex",
    "to_ris",
    "to_bibtex",
]
