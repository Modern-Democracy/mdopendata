---
type: implementation
tags:
  - budget
  - financial-statements
  - extraction
  - review
updated: 2026-07-15
---

This page records Gate 5 full raw extraction and controlled-review artifacts for the eight Charlottetown financial-statement PDFs.

# Financial Statements Raw Extraction Status

## Status

Formal Gate 5 is complete. All 139 financial-table pages identified in Gate 2 were re-extracted at 220 DPI with Tesseract word coordinates, including the eight reviewed 270-degree schedule rotations. The controlled raw import committed all eight documents and exact artifact counts on 2026-07-15. No normalized record, snapshot membership, or publication state changed.

## Raw Artifacts

Each document directory contains `raw-tables/source_table_pages.json`, `source_table_columns.json`, `source_table_rows.json`, and `source_table_cells.json`. Raw row and cell keys are derived from the document, page, table, source coordinate, and exact OCR text. Every row and cell retains normalized bounding boxes, OCR confidence, raw text, and review state.

| Measure | Count |
| --- | ---: |
| Documents | 8 |
| Registered PDF pages | 188 |
| Extracted table pages | 139 |
| Raw detected column slots | 551 |
| Raw rows | 4,852 |
| Raw cells | 10,085 |
| Raw value-candidate cells | 4,017 |
| Low-confidence rows | 140 |
| Low-confidence cells | 405 |
| Rotated table pages | 8 |

Detected column slots are raw row-relative OCR groupings. Their roles remain `unknown` until review; they are not approved semantic columns.

## Controlled Review Artifacts

Every value-bearing baseline mapping row identifies the document key, PDF page, printed page where available, page key, table key, table family, row key, raw label, and raw values. These baseline mapping registers remain unapproved; Batch 01 extraction decisions are recorded separately.

| Register | Records |
| --- | ---: |
| Per-document mapping reviews | 1,331 |
| Period review | 139 |
| Statement-class review | 139 |
| Hierarchy review | 1,331 |
| Entity-scope review | 139 |
| Dash/sign review | 1,160 |
| Reporting-entity relationship candidates | 3 |
| Comparative relationship candidates | 299 |
| Budget-equivalence candidates | 121 |
| Taxonomy review | 121 |

Comparative candidates require an exact compacted raw-label match within the same table family across the two documents in a series. This is candidate discovery only; it does not establish equal meaning, period role, or relationship approval.

### Review Batch 01

The first exact review batch contains all 29 rows below parser confidence 80 in primary-statement families across all eight documents and 17 PDF pages. Visual review approved six source-verified raw-row retentions, ten source-verified transcriptions, and 13 non-financial layout-artifact exclusions. Record 10 was revised from retention to transcription because its visually legible total-revenue row had no parsed value cells. All 29 decisions are applied to a controlled derived artifact containing 16 materialized rows and 13 exclusions. Raw artifacts, hierarchy, normalization, the database, and publication remain unchanged. See [Financial statements review batch 01](./financial-statements-review-batch-01.md).

### Review Batch 02

The second exact review batch contains all 111 remaining sub-80-confidence rows in note and schedule sections across all eight documents and 67 PDF pages. Exact source-page review approved and controlled-derived application materialized 57 source-verified financial transcriptions and 7 context transcriptions while recording 47 non-financial layout-artifact exclusions. Raw artifacts, hierarchy, normalization, the database, and publication remain unchanged. See [Financial statements review batch 02](./financial-statements-review-batch-02.md).

### Review Batch 03

The third exact review batch contains all 228 sub-80-confidence cells whose 191 parent rows are not already resolved by approved Batch 01 or Batch 02 treatment. Exact source-page review approved and controlled-derived application materialized 117 financial transcriptions, 7 context transcriptions, and 86 source dash placeholders while recording 18 layout-artifact exclusions. The other 177 of 405 low-confidence cells remain excluded because their complete parent rows already have approved treatment. See [Financial statements review batch 03](./financial-statements-review-batch-03.md).

### Review Batch 04

The fourth exact review batch joins period evidence, statement-class proposals, and entity-scope proposals for all 139 tables across 139 source pages. Visual review approved 134 proposals as written and revised five: one OCR-omitted comparative heading and four debt-maturity schedules. Controlled-derived application materialized table-level period evidence, statement class, entity scope, and the cross-entity non-addition rule for all 139 records; source-column roles remain explicitly deferred. See [Financial statements review batch 04](./financial-statements-review-batch-04.md).

## Verification

Nine extraction regressions pass. A complete rerun compared 51 generated files with zero SHA-256 differences. Visual source review confirmed City financial position, budget/actual operations, the dense budget-reconciliation note, a rotated tangible-capital-asset schedule, and pension financial position. Exact tested values and parentheses survive in the raw rows.

Six database regressions compare every imported document, page, table-page link, column, row, and cell to its controlled artifact. Scoped database counts equal 8 documents, 188 pages, 139 tables and table-page links, 551 columns, 4,852 rows, 10,085 cells, and 8 import batches. A committed rerun inserted zero records. The pre-import backup is `backups/database/mdopendata-before-financial-statements-gate5-raw-20260715.dump`, SHA-256 `a9220271cf030b78ae0602309e35ba4f7134ccded0ce1c906d0b688e349c45f1`.

Narrative years are classified as references rather than financial value candidates. Batch 01, Batch 02, and Batch 03 extraction treatments are applied in controlled derived layers. Batch 04 table-level period evidence, statement class, and entity scope are approved and applied; source-column roles, hierarchy, comparatives, budget equivalence, and taxonomy remain individually blocked for controlled review.

The Gate 6 readiness audit confirmed that raw `column_index` values identify row-relative OCR groups rather than stable physical statement columns: 345 of 551 mix value evidence with text or years, and 258 span more than 25 percent of page width. Migration 031 therefore adds a separate reviewed semantic-column and cell-fragment layer while preserving these Gate 5 records unchanged.

## Operational Boundary

- Raw database import: complete and count-verified.
- Normalized records: none created.
- Active publication snapshots: unchanged.
- Financial-statement publication: not authorized.

## Sources

- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
- [Financial statements representative schema spike](./financial-statements-schema-spike.md)
- [Financial statements migration status](./financial-statements-migration-status.md)
- [Financial statements review batch 01](./financial-statements-review-batch-01.md)
- [Financial statements review batch 02](./financial-statements-review-batch-02.md)
- [Financial statements review batch 03](./financial-statements-review-batch-03.md)
- [Financial statements review batch 04](./financial-statements-review-batch-04.md)
- `data/financial-statements/charlottetown/gate-5-raw-extraction-summary.json`
- `data/financial-statements/charlottetown/gate-5-review-summary.json`
- `data/financial-statements/charlottetown/gate-5-qa-report.json`
- `data/financial-statements/charlottetown/gate-5-raw-database-import-result.json`
- `data/financial-statements/charlottetown/gate-5-raw-database-idempotence-result.json`
- `scripts/import-charlottetown-financial-statements-raw.py`
- `scripts/test-financial-statements-raw-import.py`
- `scripts/extract-charlottetown-financial-statements-raw.py`
- `scripts/build-charlottetown-financial-statements-review.py`
- `scripts/test-financial-statements-extraction.py`
- `scripts/test-financial-statements-review-application.py`
- `scripts/test-financial-statements-review-batch-02.py`
- `scripts/test-financial-statements-review-batch-02-application.py`
- `scripts/test-financial-statements-review-batch-03.py`
- `scripts/test-financial-statements-review-batch-03-application.py`
- `scripts/test-financial-statements-review-batch-04.py`
- `scripts/test-financial-statements-review-batch-04-application.py`
