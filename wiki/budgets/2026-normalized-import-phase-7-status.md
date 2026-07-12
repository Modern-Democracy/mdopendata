---
type: status
tags:
  - budget
  - normalized-import
  - charlottetown
  - phase-7
updated: 2026-07-12
---

# 2026/2027 Normalized Import Phase 7 Status

Phase 7 source-fidelity and completion QA passed for the full normalized 2026/2027 Charlottetown budget dataset.

## Scope

Phase 7 prepared the dataset for a later publication-snapshot decision. It did not create a database publication snapshot.

## QA Evidence

| Evidence | Result |
| --- | --- |
| QA script | `scripts/verify-budget-2026-phase-7-qa.py` |
| Review-decision script | `scripts/resolve-budget-2026-phase-7-review-decisions.py` |
| Representative cleanup script | `scripts/cleanup-budget-2026-representative-normalized-spike.py` |
| QA report | `data/budget/charlottetown/2026-2027/normalized-import-phase-7-qa-report.json` |
| Cleanup report | `data/budget/charlottetown/2026-2027/normalized-import-representative-cleanup-report.json` |
| QA status | pass |
| Publication snapshots | 0 |
| Publication authorized | false |

## Count Reconciliation

| Record set | Count |
| --- | ---: |
| Manifest facts | 2,165 |
| Database facts matched by manifest key | 2,165 |
| Manifest fact-source links | 2,165 |
| Database fact-source links for manifest facts | 2,165 |
| Reconciliation records | 161 |
| Manifest review issues | 1 |
| Non-manifest same-document facts | 0 |
| Non-manifest same-document review issues | 0 |
| Publication snapshots | 0 |

## Family Results

| Family | Facts | Source links | Reconciliation checks | Mismatches |
| --- | ---: | ---: | ---: | ---: |
| Operating | 1,886 | 1,886 | 122 | 0 |
| Capital | 246 | 246 | 36 | 0 |
| Debt | 33 | 33 | 3 | 0 |

## Source Fidelity

All 2,165 manifest facts matched imported database values by deterministic fact key. All 2,165 manifest fact-source links matched source cell identity, raw text, parsed numeric value, role, and order.

Dash values remain preserved as unresolved source dashes rather than being converted to database numeric zero. The QA report records 41 `dash_unresolved` facts, 40 raw `-` tokens, and one raw `- -` token.

## Reconciliations And Review Issues

The reconciliation catalogue remains 161 checks: 160 pass and one accepted source-document discrepancy.

The accepted discrepancy is `debt_total:balance`, with calculated value 39,008,541.0000, reported value 39,008,543.0000, and difference -2.0000. Phase 7 recorded a review decision using `accept_reported_with_warning` and resolved the manifest-scoped high-severity issue.

There are zero open high- or critical-severity issues in the manifest-scoped publication candidate.

## Representative Cleanup

The database previously contained 19 non-manifest same-document representative-spike facts and three non-manifest representative review issues. These records were test-only normalized spike records from Gate 1 and outside the full-document production identity space.

Phase 7 cleanup removed 19 facts, 21 fact-source links, 16 line items, four statements, six document periods, seven reconciliation records, three review issues, and three review-issue evidence rows. The cleanup report confirms zero publication-fact links were present.

The database now has 2,165 same-document normalized facts, and all 2,165 are manifest-scoped full normalized facts.

## Gate 8 Readiness

Gate 8 is ready for review. The dataset is eligible for a separate publication decision after Gate 8 approval, but this status page does not authorize publication and no snapshot was created.

Gate 8 review commenced on 2026-07-12. Current validation confirms all 2,165 manifest facts and source links match, the 161 reconciliation records retain one approved source-document discrepancy, no high- or critical-severity issues are open, and publication snapshots remain zero.

### Gate 8 Approval Record

On 2026-07-12, the project owner approved Gate 8 based on the evidence above. The 2026/2027 dataset is now publication-eligible. This approval does not create a `budget.publication_snapshot`, does not authorize a public release, and does not alter the requirement for a separate publication decision.

## Post-Import Identity Migration

On 2026-07-12, `normalized-import-manifest.json` was found to contain 301 operating line items under twelve `*-detail-statement` identities added after the original normalized import. The database still held the same facts and source links under the prior summary-statement identities, causing Phase 7 to report 301 missing and 301 non-manifest facts.

The transactional script `scripts/migrate-budget-2026-summary-detail-identities.py` created the twelve manifest-defined detail statements, moved exactly 301 line items and their 301 facts without changing source links or values, and added the summary-detail relationships. Import batch `53` records the operation. A post-migration Phase 7 QA rerun passed with all 2,165 facts and source links matched, 161 reconciliations, and zero publication snapshots.

## Sources

- [Normalized import implementation plan](./2026-normalized-import-gap-report.md)
- [Phase 6 status](./2026-normalized-import-phase-6-status.md)
- [Phase 1 decisions](./2026-normalized-import-phase-1-decisions.md)
- `data/budget/charlottetown/2026-2027/normalized-import-phase-7-qa-report.json`
- `data/budget/charlottetown/2026-2027/normalized-import-representative-cleanup-report.json`
- `data/budget/charlottetown/2026-2027/normalized-import-statement-identity-migration-report.json`
