---
type: status
tags:
  - budget
  - raw-extraction
  - prior-year
updated: 2026-07-09
---

This page records the coordinate-aware regeneration of the two prior-year raw budget artifacts.

# Prior-Year Coordinate Raw Extraction Status

## Result

The prior text-line extractor treated transparent PDF layout glyphs as financial values. The regenerated extractor filters transparent glyphs and derives rows from visible PDF text coordinates.

| Document | Rows | Values | Reused row IDs | New row IDs |
| --- | ---: | ---: | ---: | ---: |
| 2024/2025 | 1,705 | 1,970 | 992 | 713 |
| 2025/2026 | 3,123 | 2,576 | 514 | 2,609 |

Exact visible-line matches retain their old row IDs. Changed or newly separable visible lines receive deterministic `*_coord_rNNN` IDs. Eleven 2024/2025 pages with no embedded visible text retain their existing OCR-derived raw rows and values under the explicit `preextracted_text_fallback` method. Source table IDs remain unchanged.

## Verification

- All regenerated values use `pdf_visible_coordinate_text`.
- Row and value keys are unique, and every value references a regenerated row.
- The 2025/2026 PDF page 25 control retains the visible `2,594,004` total and no longer emits a standalone transparent `0` row.
- Regenerated Phase 1 review again identifies 20 document-scoped debt instruments and two planned-debt buckets.

## Boundary

This pass regenerated repository artifacts and refreshed the Phase 1 and Phase 2 review packages. It did not mutate the existing raw database records, normalized facts, imports, compatibility records, or publication snapshots. A later controlled raw-database re-import is required before a prior-year normalized import can use the regenerated source-cell identities.

## Sources

- [Prior-year normalized import Phase 2 status](./prior-year-normalized-import-phase-2-status.md)
- [Week 5 raw ingestion status](./week-5-raw-ingestion-status.md)
- `scripts/extract-charlottetown-budget-raw-rows.py`
- `data/budget/charlottetown/2024-2025/raw-tables/coordinate-extraction-reconciliation.json`
- `data/budget/charlottetown/2025-2026/raw-tables/coordinate-extraction-reconciliation.json`
