---
type: implementation
tags:
  - budget
  - financial-statements
  - schema
  - spike
updated: 2026-07-14
---

This page records the Gate 3 representative schema spike for the eight Charlottetown financial-statement source documents.

# Financial Statements Representative Schema Spike

## Status

Gate 3 is complete. Seven approved source controls were materialized across seven unique PDF pages as 247 raw OCR rows and 612 raw OCR cells with normalized coordinates. All controls fit the existing budget schema plus the four extensions already planned for migration 029; no unsupported pattern, unplanned schema object, database write, normalized observation, or publication change was found.

## Representative Controls

| Control | Source | Result |
| --- | --- | --- |
| Consolidated financial position | 2025 City PDF page 6, visible page 4 | Asset, liability, net-debt, non-financial-asset, and accumulated-surplus hierarchy fits. |
| Budget-to-actual operations | 2025 City PDF page 7, visible page 5 | Budget 2025, actual 2025, and actual 2024 remain separate source columns and document periods. |
| Cash flow | 2025 City PDF page 9, visible page 7 | Operating, capital, investing, and financing sections remain hierarchical and non-additive. |
| Component operations | 2025 Water and Sewer PDF page 7, visible page 5 | Separate corporation scope is retained and blocked from additive use with City consolidated scope. |
| Pension position | 2024 City pension PDF page 6, visible page 4 | Plan assets, obligations, surplus, and December 31 periods remain in non-additive pension scope. |
| Draft/audited comparative difference | 2024 and 2025 City PDFs, page 6 | Both document-owned 2024 cash values survive: 15,694,379 and 15,694,380. |
| Filename/reporting-date conflict | 2024 Water and Sewer pension PDF page 6, visible page 4 | December 31 controls; no December 21 period is created. |

## Materialized Evidence

| Artifact | Count | Purpose |
| --- | ---: | --- |
| Representative source pages | 7 | Document hash, page identity, printed label, extraction method, renderer, and dimensions. |
| Representative source rows | 247 | Stable row identity, exact OCR text, normalized bounding box, confidence, and control membership. |
| Representative source cells | 612 | Stable cell identity, row identity, exact OCR text, normalized bounding box, confidence, and review state. |
| Schema projections | 7 | Source-table, statement, column-role, period-role, amount-type, reporting-entity, and required migration-object fit. |

Sixteen rows and 42 cells are below OCR confidence 80. They remain explicitly marked for Gate 5 extraction review. Visual inspection of all seven source pages and exact value controls is sufficient for architecture fit but does not authorize normalized import from low-confidence records.

## Schema Decision

The current schema already fits raw evidence, source columns, document periods, amount types, reporting entities, statement and line-item hierarchy, aggregation roles, financial observations, and observation-to-cell provenance.

Migration 029 must add the four already planned objects:

- `budget.document_accounting_context`
- `budget.statement_class`
- `budget.reporting_entity_relationship`
- `budget.financial_observation_relationship`

These objects cover accounting framework and assurance, controlled statement classification, consolidated-component and related-pension scope, and reviewed relationships between document-owned comparative observations. Gate 3 found no additional schema requirement.

## Gate Decision

Migration 029 and migration 030 are approved for Gate 4 implementation with isolated regression tests. This approval does not authorize database application, normalized import, snapshot membership, or publication.

## Sources

- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
- [Document extraction engineering](../implementation/document-extraction-engineering.md)
- `data/financial-statements/charlottetown/schema-spike/spike-summary.json`
- `data/financial-statements/charlottetown/schema-spike/schema-fit-report.json`
- `data/financial-statements/charlottetown/schema-spike/schema-spike-qa-report.json`
- `scripts/build-charlottetown-financial-statements-schema-spike.py`
- `scripts/test-financial-statements-schema-spike.py`
