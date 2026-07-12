---
type: status
tags:
  - budget
  - normalization
  - prior-year
  - import
  - qa
updated: 2026-07-12
---

This page records completion of normalized review, import, idempotence, and source-fidelity QA for the 2024/2025 and 2025/2026 Charlottetown budgets.

# Prior-Year Normalized Import Completion Status

## Result

Both prior-year documents are normalized and imported to the reviewed database level. Publication snapshots remain zero.

| Document | Facts | Fact sources | Reconciliations | Failed checks | Project references | Debt facts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024/2025 | 1,717 | 1,717 | 6 | 0 | 20 | 0 |
| 2025/2026 | 2,374 | 2,374 | 8 | 0 | 23 | 60 |

Every fact-source link matches both the reviewed raw artifact and the imported database cell. Both idempotence reruns recorded normalized logical records as unchanged and added no duplicates.

## Raw Corrections

Append-only `full-3` raw imports preserve corrected prior-year table identities. The 2025/2026 extraction also recombines debt-column values split by PDF rule geometry, such as principal `535,200`, without rewriting earlier raw imports.

## Cross-Year Projects

`budget.capital_project` remains municipality-scoped and independent of fiscal years. `budget.capital_project_reference` links source-document project labels to the stable identity, while `budget.capital_project_fact` and `budget.capital_project_profile` retain document-period facts and particulars.

Migration 026 restored the missing reference table. The approved 2026/2027 manifest then backfilled 173 references transactionally. Across all imported budgets, 27 project identities now have references from more than one source document. Compatibility is asserted only for approved exact or strong project references.

## QA Evidence

- two deterministic dry runs per prior-year document
- transactional imports followed by unchanged-only idempotence reruns
- 4,091 artifact-to-database fact-source comparisons with zero mismatches
- 14 source-supported reconciliations with zero failures
- zero publication snapshots
- 173-reference 2026/2027 backfill followed by an unchanged-only rerun

## Gate 8 Review

Gate 8 review commenced on 2026-07-12 for both prior-year datasets. The review evidence confirms exact manifest-to-database fact and source-link counts, zero artifact or database source mismatches, six passing reconciliations for 2024/2025, eight passing reconciliations for 2025/2026, zero unresolved high- or critical-severity issues, and zero publication snapshots.

### Gate 8 Approval Record

On 2026-07-12, the project owner approved Gate 8 for both the 2024/2025 and 2025/2026 datasets. Both are now publication-eligible. This approval does not create a `budget.publication_snapshot`, authorize a public release, or establish a cross-period publication scope; each requires a separate decision.

## Sources

- [Prior-year Phase 2 status](./prior-year-normalized-import-phase-2-status.md)
- [Prior-year gap report](./prior-year-normalized-import-gap-report.md)
- [Capital project lifecycle](./capital-project-lifecycle.md)
- `data/budget/charlottetown/2024-2025/normalized-import-provenance-report.json`
- `data/budget/charlottetown/2025-2026/normalized-import-provenance-report.json`
