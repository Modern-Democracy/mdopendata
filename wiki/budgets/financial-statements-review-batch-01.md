---
type: implementation
tags:
  - budget
  - financial-statements
  - extraction
  - review
updated: 2026-07-14
---

This page records the completed source review and extraction decisions for Gate 5 low-confidence primary-statement batch 01.

# Financial Statements Review Batch 01

## Status

Gate 5 review batch 01 is complete. It contains every raw row with parser confidence below 80 in the six primary-statement table families; no sampling was used and all 29 extraction dispositions are approved.

| Measure | Count |
| --- | ---: |
| Exact review rows | 29 |
| Source PDF pages | 17 |
| Source documents | 8 |
| Financial rows | 16 |
| Non-financial layout artifacts | 13 |
| Approved retention of source-verified raw row | 6 |
| Approved source-verified transcription | 10 |
| Approved as proposed | 28 |
| Revised and approved | 1 |
| Approved decisions | 29 |

## Review Contract

The machine-readable register and human-readable table identify each row by source document, PDF page, printed page, table key, row key, raw label, raw text, raw values, and parser confidence. Each row states one exact ambiguity, approved extraction resolution, approved source values, and decision outcome.

The 13 approved exclusions are signature fragments, auditor logos, printed-page artifacts, or fragmented headings. The 16 approved financial treatments preserve or transcribe visually verified statement values. Hierarchy and normalization remain separate pending reviews.

## Revision

Record 10, City 2025 consolidated statement of operations, PDF page 7, printed page 5, table `ctown_fs_city_2025_03_31_audited_p007_t01`, row `ctown_fs_city_2025_03_31_audited_p007_t01_r_9951291bf61f85bd8d2d`, raw label `null`, raw text `97,421,447 100,740,160 101,452,953`, and raw values `[]`, was revised from retain to `replace_with_source_verified_transcription`. The exact ambiguity is that the total-revenue values are visually legible but the parser exposed no value cells; the approved transcription is `97,421,447`, `100,740,160`, and `101,452,953`.

## Decision Boundary

- Approved extraction treatments are applied only to the controlled derived artifact.
- Immutable raw rows and cells are unchanged.
- No normalization is approved.
- No database write is performed.
- No publication state changes.

## Verification

The batch allowlist is derived from all eight raw-row artifacts and the primary-statement table manifests. Regression checks require exactly 29 unique rows, exact raw-field and source-locator round trips, all eight source PDFs, the 6/10/13 approved disposition split, 28 approvals as proposed, one exact revision, and one occurrence of every row key in the human review table.

## Artifacts

- `data/financial-statements/charlottetown/review-batches/low-confidence-primary-statements-batch-01.json`
- `data/financial-statements/charlottetown/review-batches/low-confidence-primary-statements-batch-01.md`
- `data/financial-statements/charlottetown/controlled-derived/low-confidence-primary-statements-batch-01-applied.json`
- `data/financial-statements/charlottetown/controlled-derived/low-confidence-primary-statements-batch-01-applied.md`
- `scripts/apply-charlottetown-financial-statements-review-batch-01.py`
- `scripts/build-charlottetown-financial-statements-review-batch-01.py`
- `scripts/test-financial-statements-review-batch.py`
- `scripts/test-financial-statements-review-application.py`

## Sources

- [Financial statements raw extraction status](./financial-statements-raw-extraction-status.md)
- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
