---
type: implementation
tags:
  - budget
  - import
  - reconciliation
  - data-quality
updated: 2026-07-08
---

This page records Phase 4 reconciliation-design status for the 2026/2027 normalized budget import.

# 2026/2027 Normalized Import Phase 4 Status

## Result

Phase 4 generated a deterministic reconciliation catalogue for the reviewed full-document manifest. Gate 5 is ready for review, not automatically approved.

The catalogue contains 161 applicable checks with exact manifest fact-key inputs and reported fact keys. It records 160 passing checks and one review outcome. No reconciliation input is unresolved.

## Coverage

| Family | Checks |
| --- | ---: |
| Adjacent detail subtotal or total | 129 |
| Capital gross plus partner-funding deduction equals net | 7 |
| Capital page 110 title-scoped net totals | 6 |
| Continued page 21/22 budget-item total | 3 |
| Explicit source component sum | 7 |
| Revenue less expense equals net income or earnings | 6 |
| Debt component totals | 3 |

The design covers operating, capital, and debt statement families where reviewed manifest facts supply all operands. Property-tax and utility-rate rows from page 23 remain excluded from calculation checks because the normalized manifest contains approved rates but not the assessment or revenue operands required to calculate them from manifest facts.

## Review Outcomes

The only non-passing numeric difference is the Water and Sewer debt balance total, where instrument balances sum to 39,008,541 and the reported balance total is 39,008,543, a difference of -2 CAD. This is recorded as a source-document discrepancy because manual recalculation reaches the same result. Dashes are treated as zero for reconciliation arithmetic while preserving their source value state.

The report records zero rejected adjacent-block candidates. Page 22 `Budget Item Totals` now reconcile as a continued page 21/22 table because both pages share the same title and column headers and page 21 has no totals. Page 110 is no longer treated as an adjacent-block exclusion because the page title supports explicit city, water/sewer, and combined net checks. Civic Centre nested revenue totals and Public Works page-87 Municipal Buildings totals now use explicit source component checks.

## Gate 5 Status

**Status:** ready for review 2026-07-08.

Gate 5 can be approved after review accepts the tolerance policy, the debt balance source-document discrepancy, and the dash-as-zero arithmetic rule.

## Sources

- [Normalized import implementation plan](./2026-normalized-import-gap-report.md)
- [Phase 3 status](./2026-normalized-import-phase-3-status.md)
- `scripts/build-budget-2026-reconciliation-catalogue.py`
- `data/budget/charlottetown/2026-2027/normalized-import-reconciliation-catalogue.json`
- `data/budget/charlottetown/2026-2027/normalized-import-reconciliation-report.json`
