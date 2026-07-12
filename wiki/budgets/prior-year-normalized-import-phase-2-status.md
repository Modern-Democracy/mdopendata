---
type: status
tags:
  - budget
  - normalization
  - prior-year
  - phase-2
updated: 2026-07-11
---

This page records the initial source-linked row-mapping inputs for prior-year Phase 2 normalization.

# Prior-Year Normalized Import Phase 2 Status

Phase 2 has generated deterministic mapping inputs for every Phase 1 `normalize` candidate. Schema version 2 follows the 2026/2027 reviewed mapping contract: each approved row has a source-value-level `facts` array containing source value ID, document period, amount type, unit, value state, and numeric value. The artifacts create no normalized facts, manifests, imports, compatibility records, or publication snapshots.

| Document | Candidates | Raw rows | Status |
| --- | ---: | ---: | --- |
| 2024/2025 | 56 | 1,645 | 1,717 source-linked facts approved; zero rows remain open. |
| 2025/2026 | 112 | 3,056 | 2,374 source-linked facts approved; zero rows remain open. |

The generated mappings use only reviewed source-column patterns and retain per-value source provenance. User-reviewed decisions applied on 2026-07-10 approve department hierarchy/context rows, blank-label category totals, capital schedule totals, facility statements, property-tax totals, and Water and Sewer debt entity context where the visible layout matches the reviewed pattern.

The remaining review queue is empty. Mixed-content rows preserve percentages, dates, staff counts, and narrative amounts as source context while mapping only reviewed monetary cells. Visibly omitted period cells remain omitted, and displayed dashes are retained as source display-zero or unresolved-dash context under the existing value-state rules.

All 43 capital project profiles are approved as narrative-only fields, covering 288 rows in 2025/2026 and 2024/2025. Their dates, quantities, and narrative numbers remain source text and cannot create financial facts. The 2025/2026 Bikeshare Program's $600,000 budget is already mapped from its capital schedule on PDF page 109, not from the narrative profile on page 110.

The generator emits an unresolved-review report for each document. It lists only the 217 unresolved 2024/2025 rows and 44 unresolved 2025/2026 rows, with candidate, table, page, family, section, row, label, and source-value IDs. Each remaining row still requires explicit hierarchy, aggregation role, amount type, unit, reporting entity, or period-role confirmation before it can become a normalized fact candidate.

The 2024/2025 operating-budget summary on PDF page 14 is approved as a standard three-period statement. Its document title, split column headings, City label, Revenue/Expenses labels, and Water and Sewer label are non-additive source context. Its 31 City and six Water and Sewer monetary rows create 91 source-linked facts, with 74 assigned to `city-of-charlottetown` and 17 to `charlottetown-water-and-sewer`. The page has zero unresolved rows.

The 2024/2025 revenue and expenditure bubble charts on PDF pages 15 and 16 are classified as `duplicate_summary` because page 14 contains the authoritative tabular figures. They remain in raw artifacts for audit but are excluded from Phase 2 mapping and from the unresolved register.

The 2025/2026 Water and Sewer operating-detail page 89 is approved using the 2026/2027 three-period detail pattern. Its 11 labelled financial rows create 33 facts across 2024/2025 budget, 2024/2025 forecast, and 2025/2026 budget. The source heading determines the `charlottetown-water-and-sewer` reporting entity, rather than the City default used by other operating-detail pages. The seven title, period-header, and section-heading rows are preserved as non-additive source context.

Page 25 staff-count labels such as `Directors (3)` and `GIS Technician (2)` are approved as non-additive source context. Their embedded count tokens cannot create CAD facts. Adjacent labelled monetary rows remain mapped, including the four solicitor-fee rows.

## 2025/2026 Debt Schedules

The City and Water and Sewer schedules on PDF pages 147 and 149 are approved at row level. Twenty document-scoped instruments and two schedule totals map balance, principal, and interest facts. The two `New Debt` rows map balance and interest only as planned-debt buckets; their principal dashes and fourth `Comments`-column cells remain raw evidence. Schedule headings and combined interest-and-principal totals are approved non-additive source context because the current amount-type vocabulary has no combined debt-service measure.

## Current Stage

Phase 2 is complete. The reviewed mappings cover operating statements and details, facility statements, capital schedules, capital-profile narrative fields, 2025/2026 tax/rate formulas, and 2025/2026 debt schedules. The next gate is deterministic prior-year manifest generation.

## Artifacts

- `scripts/build-budget-prior-year-phase2-artifacts.py`
- `data/budget/charlottetown/prior-year-phase-2-row-mapping-package.json`
- `data/budget/charlottetown/2024-2025/phase-2-row-mapping-input.json`
- `data/budget/charlottetown/2025-2026/phase-2-row-mapping-input.json`
- `data/budget/charlottetown/2024-2025/phase-2-unresolved-review-report.json`
- `data/budget/charlottetown/2025-2026/phase-2-unresolved-review-report.json`

## Sources

- [Prior-year Phase 1 status](./prior-year-normalized-import-phase-1-status.md)
- [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md)
