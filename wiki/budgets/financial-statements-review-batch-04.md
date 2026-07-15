---
type: implementation
tags:
  - budget
  - financial-statements
  - extraction
  - review
updated: 2026-07-15
---

This page records the Gate 5 table-context review queue for financial-statement period evidence, statement class, and entity scope.

# Financial Statements Review Batch 04

## Status

Batch 04 exact source review and controlled-derived application are complete. It joins the existing period, statement-class, and entity-scope registers by all 139 table keys across eight documents and 139 PDF pages. Visual review approved 134 proposals as written and revised and approved five period-evidence proposals; all 139 decisions are materialized without source-column roles.

| Measure | Count |
| --- | ---: |
| Review records | 139 |
| Unique table keys | 139 |
| Source PDF pages | 139 |
| Source documents | 8 |
| Tables with current-year candidates | 133 |
| Tables with comparative-year evidence | 110 |
| Tables with contextual-year evidence | 33 |
| Approved as proposed | 134 |
| Revised and approved | 5 |
| Approved decisions | 139 |

## Review Contract

Each record identifies the exact source file and hash, PDF and printed page, table and page keys, section, table family, rotation, continuation evidence, raw title, detected years, proposed reporting date, proposed financial-year candidates, other detected years, proposed statement class, and proposed entity scope.

The six tables without current-year evidence are separate prior-year schedule pages and remain source-faithful. Exact review added one OCR-omitted comparative heading and reclassified future debt-repayment years as financial schedule evidence on four pages.

| Record | Exact source | Revision |
| ---: | --- | --- |
| 11 | City 2024, PDF page 19, `ctown_fs_city_2024_03_31_audited_p019_t01` | Added the visually present March 31, 2023 assumptions-table heading omitted by OCR. |
| 18 | City 2024, PDF page 26, `ctown_fs_city_2024_03_31_audited_p026_t01` | Classified 2025 through 2029 principal-repayment rows as financial year evidence; retained 2015 as contextual. |
| 46 | City 2025, PDF page 26, `ctown_fs_city_2025_03_31_audited_p026_t01` | Classified 2026 through 2030 principal-repayment rows and 2026 through 2027 lease commitments as financial year evidence. |
| 94 | Water and Sewer 2024, PDF page 17, `ctown_fs_ws_2024_03_31_audited_p017_t01` | Classified 2025 through 2029 principal-repayment rows as financial year evidence; retained 2016 and 2054 as contextual narrative. |
| 109 | Water and Sewer 2025, PDF page 17, `ctown_fs_ws_2025_03_31_audited_p017_t01` | Classified 2026 through 2030 principal-repayment rows as financial year evidence; retained 2016 as contextual narrative. |

Detected years do not establish source-column roles or distinguish budget from actual columns. Source-column role assignment remains deferred to a later cell-aware review stage.

## Decision Boundary

- Table-level period evidence: approved for all 139 records.
- Source-column roles: not proposed or approved.
- Statement classes: approved for all 139 records.
- Entity scope: approved for all 139 records.
- Normalization: not approved.
- Database writes: none.
- Publication changes: none.
- Controlled-derived application: complete for all 139 approved table contexts.

## Artifacts

- `data/financial-statements/charlottetown/review-batches/table-context-batch-04.json`
- `data/financial-statements/charlottetown/review-batches/table-context-batch-04.md`
- `scripts/build-charlottetown-financial-statements-review-batch-04.py`
- `scripts/test-financial-statements-review-batch-04.py`
- `data/financial-statements/charlottetown/controlled-derived/table-context-batch-04-applied.json`
- `data/financial-statements/charlottetown/controlled-derived/table-context-batch-04-applied.md`
- `scripts/apply-charlottetown-financial-statements-review-batch-04.py`
- `scripts/test-financial-statements-review-batch-04-application.py`

## Sources

- [Financial statements raw extraction status](./financial-statements-raw-extraction-status.md)
- [Financial statements review batch 03](./financial-statements-review-batch-03.md)
- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
- `data/financial-statements/charlottetown/period-review.json`
- `data/financial-statements/charlottetown/statement-class-review.json`
- `data/financial-statements/charlottetown/entity-scope-review.json`
