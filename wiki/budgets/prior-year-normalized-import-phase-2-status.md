---
type: status
tags:
  - budget
  - normalization
  - prior-year
  - phase-2
updated: 2026-07-10
---

This page records the initial source-linked row-mapping inputs for prior-year Phase 2 normalization.

# Prior-Year Normalized Import Phase 2 Status

Phase 2 has generated deterministic mapping inputs for every Phase 1 `normalize` candidate. Schema version 2 follows the 2026/2027 reviewed mapping contract: each approved row has a source-value-level `facts` array containing source value ID, document period, amount type, unit, value state, and numeric value. The artifacts create no normalized facts, manifests, imports, compatibility records, or publication snapshots.

| Document | Candidates | Raw rows | Status |
| --- | ---: | ---: | --- |
| 2024/2025 | 58 | 1,705 | 359 operating rows approved; remaining family review required |
| 2025/2026 | 112 | 3,056 | 719 operating rows and 40 debt-schedule rows approved; remaining family review required |

The first operating approvals use only contiguous, header-aligned source value columns. They map 359 2024/2025 rows to 1,015 source-linked facts and 719 2025/2026 rows to 1,556 source-linked facts. Each fact uses the same fields as its 2026/2027 counterpart. Blank-label totals, rows with omitted intermediate columns, and other non-contiguous column patterns remain unapproved.

All 43 capital project profiles are approved as narrative-only fields, covering 288 rows in 2025/2026 and 2024/2025. Their dates, quantities, and narrative numbers remain source text and cannot create financial facts.

The remaining 3,044 rows retain `unreviewed` semantics and `needs_review` status. Phase 2 must still approve each applicable row's hierarchy, aggregation role, amount type, unit, reporting entity, and period role before it can become a normalized fact candidate.

## 2025/2026 Debt Schedules

The City and Water and Sewer schedules on PDF pages 147 and 149 are approved at row level. Twenty document-scoped instruments and two schedule totals map balance, principal, and interest facts. The two `New Debt` rows map balance and interest only as planned-debt buckets; their principal dashes and fourth `Comments`-column cells remain raw evidence. Schedule headings and combined interest-and-principal totals are approved non-additive source context because the current amount-type vocabulary has no combined debt-service measure.

## Current Stage

2025/2026 review has completed debt schedules, tax and rate formulas, named property-tax totals and grants, six inherited property-tax subtotals, capital schedules, and Bell Aliant facility statements. Operating-detail review remains active: 1,541 rows across 49 tables require page-pattern-specific review before normalized facts can be approved.

## Artifacts

- `scripts/build-budget-prior-year-phase2-artifacts.py`
- `data/budget/charlottetown/prior-year-phase-2-row-mapping-package.json`
- `data/budget/charlottetown/2024-2025/phase-2-row-mapping-input.json`
- `data/budget/charlottetown/2025-2026/phase-2-row-mapping-input.json`

## Sources

- [Prior-year Phase 1 status](./prior-year-normalized-import-phase-1-status.md)
- [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md)
