---
type: status
tags:
  - budget
  - raw-ingestion
  - charlottetown
  - week-5
updated: 2026-07-09
---

# Week 5 Raw Ingestion Status

Week 5 raw ingestion has appended the 2025/2026 and 2024/2025 Charlottetown budget source tables, rows, cells, and source pages to the database without creating a publication snapshot.

## Scope

This pass ingested raw extraction records for the two prior annual PDFs so they can support later normalized mapping, restatement handling, project aliases, and cross-period comparability review.

It did not approve normalized facts or mark compatible facts as comparable across documents.

## Source Documents

| Document | PDF pages | full-2 tables | Raw rows | Detected values | Database cells |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025/2026 Financial Plan Capital and Operational Budgets | 150 | 114 | 3,871 | 5,182 | 9,053 |
| 2024/2025 Financial Plan Capital and Operational Budgets | 88 | 58 | 1,701 | 2,019 | 3,720 |

Database cells equal one label cell for each raw row plus one value cell for each detected value.

## Generated Artifacts

| Document | Artifacts |
| --- | --- |
| 2025/2026 | `data/budget/charlottetown/2025-2026/page_inventory.json`, `table_manifest.json`, `ingestion_summary.json`, `raw-pages/`, `raw-tables/` |
| 2024/2025 | `data/budget/charlottetown/2024-2025/page_inventory.json`, `table_manifest.json`, `ingestion_summary.json`, `raw-pages/`, `raw-tables/` |

## Database Evidence

| Check | Result |
| --- | --- |
| 2025/2026 source pages | 150 of 150 |
| 2024/2025 source pages | 88 of 88 |
| 2025/2026 full-2 raw tables | 114 |
| 2024/2025 full-2 raw tables | 58 |
| Publication snapshots | 0 |

## Remaining Gate

The 2026/2027 normalized builder remains document-specific. Prior-year normalized import still requires approved document-specific mapping for fiscal-period labels, section ranges, continuation groups, project aliases, restatement handling, and compatibility records.

Raw coverage blockers identified during normalized mapping review were resolved on 2026-07-09 by adding supplemental full-2 raw table coverage for 2025/2026 pages 14-17 and 2024/2025 pages 14-16, 62-63, and 78-86.

## Sources

- [Implementation and test plan](./implementation-plan.md)
- [Budget database schema](./database-schema.md)
- `data/budget/charlottetown/2025-2026/raw-tables/raw_row_value_summary.json`
- `data/budget/charlottetown/2024-2025/raw-tables/raw_row_value_summary.json`
