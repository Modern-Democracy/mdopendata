---
type: source
tags:
  - charlottetown
  - budget
  - ingestion
updated: 2026-05-19
---

This page records the first-pass ingestion artifacts for the City of Charlottetown 2026/2027 Financial Plan Capital and Operating Budgets PDF.

# Charlottetown 2026/2027 Budget First Pass

## Source

The source document is `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`.

Observed PDF metadata from `pdfinfo`: 154 letter-size pages, Canva producer, tagged PDF, not encrypted.

## Generated Artifacts

The first-pass artifacts are under `data/budget/charlottetown/2026-2027/`:

| Artifact | Purpose |
| --- | --- |
| `raw-pages/page-001.txt` through `raw-pages/page-154.txt` | Per-page `pdftotext -layout` output for audit and classifier review. |
| `page_inventory.json` | One page-level classification record per source page. |
| `table_manifest.json` | Candidate structured tables and capital project profiles with page provenance. |
| `ingestion_summary.json` | Counts by section, content type, and table type. |
| `raw-tables/source_table_rows.json` | Raw line-level rows extracted from each table/profile manifest record. |
| `raw-tables/source_values.json` | Raw numeric, currency, percent, and rate tokens detected in extracted rows. |
| `raw-tables/raw_row_value_summary.json` | Counts by manifest table type and detected value kind. |

## First-Pass Counts

The latest run produced 154 page inventory records and 114 table/profile manifest records.

Page sections:

| Section | Pages |
| --- | ---: |
| Front matter | 3 |
| Introduction | 3 |
| Strategic Plan | 2 |
| Budget Overview | 9 |
| Operating Budget | 91 |
| Capital Budget | 39 |
| Appendix | 6 |
| Back matter | 1 |

Content classifications:

| Type | Pages |
| --- | ---: |
| table | 84 |
| project_profile | 24 |
| section_divider_or_text | 26 |
| text | 14 |
| chart_with_data_table | 2 |
| rate_schedule | 2 |
| debt_schedule | 2 |

Table/profile manifest classifications:

| Type | Records |
| --- | ---: |
| operating_budget_detail | 42 |
| capital_project_profile | 24 |
| operating_budget_summary | 21 |
| capital_budget_table | 13 |
| third_party_facility_operating_budget | 8 |
| chart_source_table | 2 |
| tax_or_utility_rate_schedule | 2 |
| debt_schedule | 2 |

## Limits

This is not a normalized budget import. It does not create database tables, stable budget identifiers, cross-year facts, or parsed row-level financial records.

The table manifest is page-granular. Multi-page detailed breakdowns remain separate candidate records until a later schema and extraction pass defines how sections, sub-sections, subtotal rows, and continuation pages should be joined.

A later generic three-year profiler reports 116 discovery candidates for this document rather than 114. The counts are not equivalent: the generic profile includes a broader overview/rate candidate set and uses different family rules. Neither count represents approved normalized tables.

## Raw Row And Value Extraction

The raw row/value pass reads the 114 manifest records and emits row/value JSON without normalized budget semantics.

| Metric | Count |
| --- | ---: |
| Manifest table/profile records | 114 |
| Raw row records | 3,233 |
| Raw value records | 2,420 |

Detected values by kind:

| Kind | Count |
| --- | ---: |
| currency | 124 |
| number | 2,194 |
| percent | 98 |
| rate | 4 |

## Sources

- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`
- `data/budget/charlottetown/2026-2027/ingestion_summary.json`
- `data/budget/charlottetown/2026-2027/raw-tables/raw_row_value_summary.json`
- [Three-year budget source profile](./budget-three-year-source-profile.md)
