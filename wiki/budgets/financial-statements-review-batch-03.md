---
type: implementation
tags:
  - budget
  - financial-statements
  - extraction
  - review
updated: 2026-07-14
---

This page records the exact Gate 5 review queue for remaining low-confidence financial-statement cells.

# Financial Statements Review Batch 03

## Status

Batch 03 source review and controlled-derived application are complete. Every raw cell with parser confidence below 80 whose parent row is not already resolved by approved Batch 01 or Batch 02 treatment was reviewed in 77 exact source-page groups; no sampling was used. All 228 approved treatments were applied by exact cell key without mutating raw evidence.

| Measure | Count |
| --- | ---: |
| All low-confidence cells | 405 |
| Excluded under approved parent-row decisions | 177 |
| Exact remaining review cells | 228 |
| Parent rows | 191 |
| Source PDF pages | 77 |
| Source documents | 8 |
| Primary-statement cells | 51 |
| Note cells | 84 |
| Schedule cells | 93 |
| Financial transcriptions | 117 |
| Context transcriptions | 7 |
| Source dash placeholders | 86 |
| Layout-artifact exclusions | 18 |
| Revised and approved decisions | 228 |

| Token class | Cells |
| --- | ---: |
| Text | 102 |
| Amount candidate | 51 |
| Dash candidate | 69 |
| Signed-amount candidate | 6 |

## Selection Contract

The 177 excluded cells belong to one of the 140 parent rows already reviewed and approved in Batch 01 or Batch 02. Whole-row retention, transcription, context preservation, or exclusion supersedes separate cell review for those rows.

Every included record identifies the source document, PDF page, captured printed-page label, table section and family, table key, parent row key and context, cell key, column index, cell bounding box, immutable raw cell text, token class, parser confidence, exact source finding, approved resolution, source-verified text and values or value state, and decision status.

## Review Contract

- 117 financial cells have source-verified text, digits, signs, percentages, and value order.
- 7 context cells preserve source wording and column separation outside financial mapping.
- 86 cells are source-verified dash placeholders and are not interpreted as zero, null, or negative signs.
- 18 isolated logos, bullets, signature marks, or table-edge artifacts are excluded from financial mapping.

The machine-readable and human-readable review artifacts group all 228 approved decisions into 77 exact source-page groups. The controlled-derived artifacts preserve the same page grouping and materialize 117 financial cells, 7 context cells, and 86 source dash states while recording 18 exclusions. Normalization remains a separate gate.

## Source Controls

Every selected page was rendered at 180 DPI, including all recorded 270-degree schedule rotations, and every cell bbox was inspected within its parent-row context. Source review corrected material OCR errors including `(792,142)`, `(742,585)`, `35,377,973`, `73,115`, and the percentage placeholder `- %`.

## Decision Boundary

- Cell-level visual decisions: complete for all 228 cells.
- Approved Batch 01 and Batch 02 row decisions: unchanged.
- Raw corrections: not applied.
- Controlled-derived application: complete for all 228 approved cell decisions.
- Normalization: not approved.
- Database writes: none.
- Publication changes: none.

## Artifacts

- `data/financial-statements/charlottetown/review-batches/low-confidence-cells-batch-03.json`
- `data/financial-statements/charlottetown/review-batches/low-confidence-cells-batch-03.md`
- `scripts/build-charlottetown-financial-statements-review-batch-03.py`
- `scripts/test-financial-statements-review-batch-03.py`
- `data/financial-statements/charlottetown/controlled-derived/low-confidence-cells-batch-03-applied.json`
- `data/financial-statements/charlottetown/controlled-derived/low-confidence-cells-batch-03-applied.md`
- `scripts/apply-charlottetown-financial-statements-review-batch-03.py`
- `scripts/test-financial-statements-review-batch-03-application.py`

## Sources

- [Financial statements raw extraction status](./financial-statements-raw-extraction-status.md)
- [Financial statements review batch 01](./financial-statements-review-batch-01.md)
- [Financial statements review batch 02](./financial-statements-review-batch-02.md)
- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
