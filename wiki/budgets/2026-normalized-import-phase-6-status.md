---
type: status
tags:
  - budget
  - normalized-import
  - charlottetown
  - phase-6
updated: 2026-07-09
---

# 2026/2027 Normalized Import Phase 6 Status

Phase 6 controlled import is complete and ready for Gate 7 import-acceptance review.

## Scope

Phase 6 applied importer version `normalized-full-1` to the local PostgreSQL database after Gate 6 approval. The import remained controlled: no publication snapshot was created.

## Backup

Before import, a custom-format database backup was written to:

`backups/database/mdopendata-before-budget-normalized-full-20260709.dump`

The backup size is 109,157,546 bytes.

## Import Evidence

| Evidence | Result |
| --- | --- |
| Importer version | `normalized-full-1` |
| Source SHA-256 | `d926634427e80aa2b06b6425bdbb117424fe53567ae344980cd10791f8e39bac` |
| First import batch | `17`, completed |
| Idempotence rerun batch | `18`, completed |
| Publication snapshots | `0` |
| Evidence artifact | `data/budget/charlottetown/2026-2027/normalized-import-phase-6-report.json` |

First import batch `17` recorded 6,523 `added` events, 7 `unchanged` dimension events, and 1 `review_needed` capital-profile exception.

Second import batch `18` recorded 6,530 `unchanged` events and 1 `review_needed` capital-profile exception. It recorded no `added` events.

## Keyed Database Counts

| Record set | Count |
| --- | ---: |
| Source documents | 1 |
| Source tables | 85 |
| Statements | 30 |
| Line items | 1,163 |
| Capital projects | 169 |
| Capital project profile rows | 120 |
| Capital project facts | 192 |
| Debt instruments | 10 |
| Debt facts | 30 |
| Reconciliations | 161 |
| Review issues | 1 |
| Publication snapshots | 0 |

The exact fact and fact-source idempotence evidence comes from import-record events: batch `18` reported 2,165 `fact` records and 2,165 `fact_source` records as `unchanged`.

## Accepted Exception

The only failed reconciliation remains the approved source-document discrepancy:

| Check | Calculated | Reported | Difference | Passed |
| --- | ---: | ---: | ---: | --- |
| `debt_total:balance` | 39,008,541.0000 | 39,008,543.0000 | -2.0000 | false |

## Gate 7 Readiness

Gate 7 is ready for review. The controlled import completed, the idempotence rerun produced no duplicate logical inserts, source-keyed counts match the approved Phase 5 import plan, publication snapshots remain absent, and the only failed reconciliation is the accepted $2 source-document discrepancy.

## Sources

- [Implementation and test plan](./implementation-plan.md)
- [Phase 5 status](./2026-normalized-import-phase-5-status.md)
- `data/budget/charlottetown/2026-2027/normalized-import-phase-6-report.json`
