---
title: 'easyScieloPy: A Python package for programmatic and reproducible literature search in the SciELO database'
tags:
  - Python
  - literature review
  - reproducibility
  - bibliographic databases
  - SciELO
authors:
  - name: Keneth Masis-Leandro
    orcid: 0000-0003-0946-973X
    equal-contrib: true
    affiliation: 1
  - name: José Pablo Sorto-Ixcamparij
    equal-contrib: true
    affiliation: 2
affiliations:
  - name: Infants' Environmental Health (ISA) Program, Central American Institute for Studies on Toxic Substances (IRET), Universidad Nacional, Heredia, Costa Rica
    index: 1
  - name: Business Informatics Program, Guanacaste Campus, University of Costa Rica, Liberia, Costa Rica
    index: 2
date: 02 September 2025
bibliography: paper.bib
---

# Summary

The initial phase of a literature review, searching for and documenting a corpus of academic works, is often overlooked and poorly documented, despite being critical to the review's integrity [@Brocke:2009; @Cram:2020]. Programmatic approaches can enhance reproducibility by embedding search logic directly into code, enabling automated, traceable, and transparent workflows as recommended by the Preferred Reporting Items for Systematic reviews and Meta-Analyses (PRISMA-S) [@Rethlefsen:2021]. However, such tools are rare for regionally focused databases.

To address this gap for the SciELO (Scientific Electronic Library Online) database, we developed `easyScieloPy`, a Python package that provides a scriptable interface to SciELO. The package abstracts query construction, HTTP resilience, and data parsing across three distinct backends: SciELO's web search engine (`search`), the official ArticleMeta REST API (`articlemeta`), and the OAI-PMH provider (`oai`). Results are normalized into structured data models and can be converted to Pandas DataFrames, CSV files, or standard dictionaries for downstream bibliometric analysis.

# Statement of need

SciELO is a crucial open-access platform indexing peer-reviewed journals from Latin America, the Caribbean, South Africa, Portugal, and Spain. Its importance is underscored by the significant underrepresentation of these regions' output in major commercial databases like Scopus and Web of Science, which index only a small fraction of Latin American journals and systematically underrepresent non-English publications [@Cespedes:2021].

Researchers relying on SciELO have traditionally used manual searches on the web portal. This process is inherently difficult to document precisely, impossible to reproduce exactly, and inefficient for testing complex search strategies or updating reviews. While programmatic tools like `easyPubMed` [@Fantini:2025] exist for other databases, no equivalent open-source Python library has been available for SciELO. `easyScieloPy` meets this need by providing a programmable and transparent workflow for researchers, librarians, and data scientists conducting systematic reviews or bibliometric analyses who require a reproducible method to retrieve literature from this essential database.

# Installation and Usage

`easyScieloPy` is available on PyPI and can be installed using `pip`:

```bash
pip install easyscielopy
```

To enable support for Pandas DataFrame exports, install with optional dependencies:

```bash
pip install "easyscielopy[pandas]"
```

## Backends and Data Sources

The package provides three backends for fetching article metadata:

- **Web Search Engine (`search`, default):** Performs full-text queries against SciELO's search service (`search.scielo.org`), supporting filters for year range, country collections, article languages, subject categories, and journal titles.
- **ArticleMeta REST API (`articlemeta`):** Consumes the official SciELO ArticleMeta REST API, providing detailed structured JSON records for advanced metadata analysis.
- **OAI-PMH Provider (`oai`):** Connects to SciELO's OAI-PMH endpoint to retrieve standard Dublin Core XML metadata records suitable for mass harvesting and digital preservation.

## Basic Workflow

A basic workflow using `easyScieloPy` in Python is straightforward:

```python
from easyscielo import search_scielo, to_dataframe

# Search for articles using the default web engine backend
articles = search_scielo(
    query="dengue",
    backend="search",
    collections=["bra", "col"],
    languages=["es", "pt"],
    year_start=2020,
    year_end=2023,
    n_max=20,
)

# Display extracted articles
for art in articles:
    print(f"[{art.year}] {art.title} ({art.journal})")

# Convert results into a Pandas DataFrame
df = to_dataframe(articles)
```

# Acknowledgements

We would like to thank Berendina van Wendel de Joode, coordinator of the Infants' Environmental Health (ISA) Program, for enabling us to test the package in real-world research contexts and for her support throughout its development.

# References
