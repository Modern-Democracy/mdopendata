---
type: project
tags:
  - budget
  - publication
  - snapshot
  - charlottetown
updated: 2026-07-12
---

This draft defines the approval required to create the first three-year Charlottetown budget publication snapshot without authorizing public release.

# Three-Year Charlottetown Publication-Snapshot Proposal

## Proposed Outcome

Create one draft `budget.publication_snapshot` for Charlottetown containing all reviewed facts from the 2024/2025, 2025/2026, and 2026/2027 financial-plan documents. The snapshot freezes approved fact membership for a later read-only release. It does not implement APIs or UI, make the snapshot public, or imply that every cross-period comparison is compatible.

## Proposed Snapshot Record

| Field | Draft value | Status |
| --- | --- | --- |
| Municipality | `charlottetown` | Confirmed |
| Release label | `charlottetown-budget-2024-2027-initial` | Proposed |
| Taxonomy version | `charlottetown-budget-v1` | Approved |
| Status at creation | `draft` | Proposed |
| Source documents | Three documents listed below | Confirmed |
| Fact membership | All 6,256 approved facts from the three documents | Proposed |
| Public-release state | No public release | Confirmed exclusion |

## Source Scope And Counts

| Fiscal period | Source document ID | SHA-256 | Approved facts | Gate 8 |
| --- | ---: | --- | ---: | --- |
| 2024/2025 | 7 | `873b011970ea4042d107f7b0c4b8d58c5b5ef49ce5531f8f25f46de9270f37f6` | 1,717 | Approved |
| 2025/2026 | 8 | `d6d3fa419756eaa482a67ab42b3acdab4bf0d0329c0649fea108e4c1aaad1631` | 2,374 | Approved |
| 2026/2027 | 9 | `d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac` | 2,165 | Approved |
| **Total** |  |  | **6,256** |  |

## Taxonomy Decision

The project owner approved `charlottetown-budget-v1` as the snapshot taxonomy-version label on 2026-07-12. The database currently has no `budget.normalized_category` rows; this label is immutable snapshot metadata and must be carried by future public API responses and comparison warnings. It does not claim that a cross-municipality taxonomy exists.

## Preconditions

- The three source-document hashes and IDs match the table above.
- Each Gate 8 approval remains valid at execution time.
- All 6,256 candidate facts retain `review_status = approved`.
- There are zero publication snapshots before creation.
- The 2026/2027 accepted `debt_total:balance` source-document discrepancy remains included as a visible warning, not silently recalculated.
- The operation is one transaction: create the draft snapshot, add memberships, verify counts and source scope, then commit.

## Dry-Run Evidence

`scripts/plan-budget-charlottetown-three-year-publication-snapshot.py` generated the deterministic dry-run plan at `data/budget/charlottetown/publication-snapshot-three-year-dry-run-plan.json`.

| Check | Result |
| --- | ---: |
| Candidate publication facts | 6,256 |
| Source documents | 7, 8, 9 |
| Existing snapshots | 0 |
| Open high/critical issues | 0 |
| Plan SHA-256 | `33a5aefbdb0778f26d9cec74add218e6dee3424f044bd7ed4e8382120dd88a91` |

The plan records counts by source document, fiscal period, statement kind, amount type, measure unit, and value state. It creates no database records.

## Acceptance Checks

1. Snapshot municipality is Charlottetown and source-document membership is exactly IDs 7, 8, and 9.
2. Snapshot has exactly 6,256 `publication_fact` memberships, with no duplicate fact IDs.
3. Every member fact is approved and belongs to one listed source document.
4. `budget.v_published_facts` returns 6,256 rows for the snapshot only after a separate status change to `published`; the draft snapshot remains absent from that view.
5. No fact, source link, raw record, reconciliation, review decision, or prior snapshot is changed.
6. Re-run attempts with the same release label fail visibly through the unique municipality/release-label constraint.

## Draft Snapshot Creation Record

The approved draft snapshot was created on 2026-07-12.

| Field | Result |
| --- | --- |
| Snapshot ID | `1` |
| Release label | `charlottetown-budget-2024-2027-initial` |
| Taxonomy version | `charlottetown-budget-v1` |
| Status | `draft` |
| Source document IDs | `7`, `8`, `9` |
| Publication facts | `6,256` |
| Published-view rows | `0` |
| Unapproved member facts | `0` |
| Out-of-scope member facts | `0` |

The draft snapshot is not visible through `budget.v_published_facts`. A separate publication decision remains required.

## Publication And Comparison Limits

- Changing the snapshot from `draft` to `published` is a separate approval and must occur only after the acceptance checks pass.
- Snapshot publication does not create the planned budget APIs or web pages.
- Cross-period comparison remains limited to facts with approved compatible identity, period, entity, amount-type, unit, and aggregation semantics. Missing or incompatible coverage must remain visible and must not render as zero.
- Cross-municipality comparison is out of scope because no cross-municipality taxonomy has been approved.

## Execution Plan After Approval

1. Generate a dry-run membership plan with fact counts by source document, fiscal period, statement family, unit, amount type, and value state.
3. Review the plan against this proposal and the Gate 8 evidence.
4. Create the draft snapshot transactionally and rerun the membership checks.
5. Request the separate decision to publish the snapshot or retain it as an internal release candidate.

## Sources

- [Municipal budget database schema](./database-schema.md)
- [Budget API and UI contract](./api-and-ui-contract.md)
- [2026/2027 Phase 7 status](./2026-normalized-import-phase-7-status.md)
- [Prior-year completion status](./prior-year-normalized-import-completion-status.md)
- `budget.source_document` database records 7, 8, and 9 queried on 2026-07-12
- `data/budget/charlottetown/publication-snapshot-three-year-dry-run-plan.json`
- `data/budget/charlottetown/publication-snapshot-three-year-draft-report.json`
