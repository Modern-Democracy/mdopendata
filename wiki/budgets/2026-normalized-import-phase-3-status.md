---
type: implementation
tags:
  - budget
  - import
  - provenance
  - data-quality
updated: 2026-07-08
---

This page records Phase 3 source-cell and capital-profile provenance validation for the 2026/2027 normalized import.

# 2026/2027 Normalized Import Phase 3 Status

## Result

File-level and PostgreSQL provenance validation are complete. Gate 4 is approved after an append-only `full-2` raw import replaced stale provenance targets without modifying immutable `full-1` records.

The approved database mutation appended 114 versioned source tables, 3,233 rows, 3,092 value cells, and one completed `full-2` import batch. No existing raw record was updated or deleted.

## File-Level Validation

| Check | Result |
| --- | ---: |
| Fact source links | 2,165 |
| Unique source cells | 2,165 |
| Missing source values, rows, or cells | 0 |
| Raw token/span mismatches | 0 |
| Parsed numeric mismatches | 0 |
| Capital profiles | 24 |
| Profile field-to-row links | 253 |
| Profile provenance mismatches | 0 |

Every fact source now contains a deterministic cell key composed from source table, row ID, and column index. Every capital profile field retains its contributing raw row IDs.

## Page 87 Text-Extraction Row Reconstruction

The rendered PDF presents one visual Snow Removal row with horizontally aligned values of $36,000, $36,000, and $36,720. The Snow Removal label sits slightly lower than the values. PDF text extraction assigns the first and third values to extracted row 51 and the middle value to extracted row 52; this is an extraction-order artifact, not a split source row. The manifest reconstructs the three extracted value tokens under one logical Snow Removal line while retaining their extracted row and cell provenance.

## Database Resolution

The original `full-1` raw import remains immutable and contains 23 cells that predate later aligned-column recovery. The approved resolution appended the complete current raw layer under `:full-2` source-table identities and repointed the normalized manifest to those identities.

Post-import validation resolved all 2,165 normalized source-cell links against `full-2` with zero missing cells, raw-token mismatches, or parsed-numeric mismatches. Publication snapshots remain zero.

### Operational Evidence

- Pre-import database dump: `backups/database/mdopendata-before-budget-full2-20260708.dump`
- Dry run: 114 tables, 3,233 rows, and 3,092 values appended then rolled back
- Applied import: one transaction and one completed `full-2` batch
- Database result: 114 `full-2` tables, 3,233 rows, and 3,092 value cells
- Provenance result: 2,165 links resolved with zero mismatches
- Publication snapshots: zero

## Gate 4 Status

**Status:** approved 2026-07-08.

## Sources

- [Normalized import implementation plan](./2026-normalized-import-gap-report.md)
- [Phase 2 status](./2026-normalized-import-phase-2-status.md)
- `data/budget/charlottetown/2026-2027/normalized-import-provenance-report.json`
- `data/budget/charlottetown/2026-2027/raw-tables/source_table_rows.json`
- `data/budget/charlottetown/2026-2027/raw-tables/source_values.json`
- `scripts/import-budget-schema-spike.py`
