---
type: implementation
tags:
  - budget
  - financial-statements
  - extraction
  - review
updated: 2026-07-14
---

This page records the exact Gate 5 review queue for low-confidence note-disclosure and schedule rows.

# Financial Statements Review Batch 02

## Status

Batch 02 source review and controlled-derived application are complete. All 111 raw rows with parser confidence below 80 whose table manifest section is `Notes` or `Schedules` were visually reviewed in 67 exact source-page groups; no sampling was used.

| Measure | Count |
| --- | ---: |
| Exact review rows | 111 |
| Source PDF pages | 67 |
| Source documents | 8 |
| Note rows | 82 |
| Schedule rows | 29 |
| Value-bearing rows | 26 |
| Rows without parsed values | 85 |
| Financial transcriptions | 57 |
| Context transcriptions | 7 |
| Layout-artifact exclusions | 47 |
| Revised and approved decisions | 111 |

| Table family | Rows |
| --- | ---: |
| General note-disclosure tables | 77 |
| Budget-reconciliation notes | 5 |
| Tangible-capital-asset schedules | 25 |
| Segmented-disclosure schedules | 4 |

## Review Contract

Every row identifies the source document, PDF page, captured printed-page label, table family, table key, row key, parser confidence, raw label, raw values, exact source finding, approved resolution, source-verified transcription where applicable, and decision state. The machine-readable artifact retains raw text and bounding boxes.

The review approved 57 source-verified financial transcriptions, 7 context transcriptions, and 47 non-financial layout-artifact exclusions. The human-readable artifact groups all decisions by exact source document and PDF page.

The controlled-derived application materializes the 57 financial rows and 7 context records and records all 47 exclusions. Every application retains the immutable raw label, text, values, source locator, approved resolution, and source decision artifact hash.

## Family Controls

Every selected source page was rendered at 180 DPI and each row bounding box was inspected against page context. Source transcription preserves parentheses, dashes, value order, source wording, and comparative differences, including the `(499,620)` value on City 2025 PDF page 35.

## Decision Boundary

- Visual source decisions: complete for all 111 rows.
- Raw corrections: not applied.
- Controlled-derived application: complete for all 111 rows.
- Normalization: not approved.
- Database writes: none.
- Publication changes: none.

## Artifacts

- `data/financial-statements/charlottetown/review-batches/low-confidence-note-schedules-batch-02.json`
- `data/financial-statements/charlottetown/review-batches/low-confidence-note-schedules-batch-02.md`
- `scripts/build-charlottetown-financial-statements-review-batch-02.py`
- `scripts/test-financial-statements-review-batch-02.py`
- `data/financial-statements/charlottetown/controlled-derived/low-confidence-note-schedules-batch-02-applied.json`
- `data/financial-statements/charlottetown/controlled-derived/low-confidence-note-schedules-batch-02-applied.md`
- `scripts/apply-charlottetown-financial-statements-review-batch-02.py`
- `scripts/test-financial-statements-review-batch-02-application.py`

## Sources

- [Financial statements raw extraction status](./financial-statements-raw-extraction-status.md)
- [Financial statements review batch 01](./financial-statements-review-batch-01.md)
- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
