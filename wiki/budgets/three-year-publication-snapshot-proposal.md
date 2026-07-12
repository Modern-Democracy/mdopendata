---
type: project
tags:
  - budget
  - publication
  - snapshot
  - charlottetown
updated: 2026-07-12
---

This page records the creation and publication state of the first three-year Charlottetown budget publication snapshot.

# Three-Year Charlottetown Publication-Snapshot Proposal

## Outcome

Snapshot `1` contains all reviewed facts from the 2024/2025, 2025/2026, and 2026/2027 Charlottetown financial-plan documents. It is published for read-only API access. Publication does not imply that every cross-period comparison is compatible.

## Proposed Snapshot Record

| Field | Value | Status |
| --- | --- | --- |
| Municipality | `charlottetown` | Confirmed |
| Release label | `charlottetown-budget-2024-2027-initial` | Confirmed |
| Taxonomy version | `charlottetown-budget-v1` | Approved |
| Status | `published` | Confirmed |
| Source documents | Three documents listed below | Confirmed |
| Fact membership | All 6,256 approved facts from the three documents | Confirmed |
| Public-release state | Published read-only snapshot | Confirmed |

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
4. `budget.v_published_facts` returns exactly 6,256 rows for the published snapshot.
5. No fact, source link, raw record, reconciliation, review decision, or prior snapshot is changed.
6. Re-run attempts with the same release label fail visibly through the unique municipality/release-label constraint.

## Snapshot Publication Record

The approved draft snapshot was created and subsequently published on 2026-07-12.

| Field | Result |
| --- | --- |
| Snapshot ID | `1` |
| Release label | `charlottetown-budget-2024-2027-initial` |
| Taxonomy version | `charlottetown-budget-v1` |
| Status | `published` |
| Source document IDs | `7`, `8`, `9` |
| Publication facts | `6,256` |
| Published-view rows | `6,256` |
| Unapproved member facts | `0` |
| Out-of-scope member facts | `0` |

Database verification on 2026-07-12 confirmed status `published` and 6,256 rows for snapshot `1` in `budget.v_published_facts`.

## Publication And Comparison Limits

- Snapshot publication authorizes read-only exposure through APIs that enforce the published-snapshot boundary.
- Snapshot publication does not by itself establish comparison compatibility or create web pages.
- Cross-period comparison remains limited to facts with approved compatible identity, period, entity, amount-type, unit, and aggregation semantics. Missing or incompatible coverage must remain visible and must not render as zero.
- Cross-municipality comparison is out of scope because no cross-municipality taxonomy has been approved.

## Sources

- [Municipal budget database schema](./database-schema.md)
- [Budget API and UI contract](./api-and-ui-contract.md)
- [2026/2027 Phase 7 status](./2026-normalized-import-phase-7-status.md)
- [Prior-year completion status](./prior-year-normalized-import-completion-status.md)
- `budget.source_document` database records 7, 8, and 9 queried on 2026-07-12
- `data/budget/charlottetown/publication-snapshot-three-year-dry-run-plan.json`
- `data/budget/charlottetown/publication-snapshot-three-year-draft-report.json`
- `budget.publication_snapshot` snapshot `1` and `budget.v_published_facts`, queried on 2026-07-12
