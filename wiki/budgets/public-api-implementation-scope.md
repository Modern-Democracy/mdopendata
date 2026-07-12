---
type: project
tags:
  - budget
  - api
  - publication
  - charlottetown
updated: 2026-07-12
---

This page defines the first implementation slice for read-only public budget APIs backed only by published snapshots.

# Public Budget API Implementation Scope

## Outcome

Implement a read-only API that lets a public user discover available published budget coverage, inspect source documents, retrieve an individual fact with provenance, and download filtered published facts. The initial implementation serves only `budget.v_published_facts`; it must not query raw or draft-snapshot facts for public responses.

Snapshot 1 is currently `draft`. Until a snapshot is separately approved and changed to `published`, every public budget endpoint returns an empty valid result with the machine-readable reason `no_published_snapshot`.

## In Scope: First Slice

| Endpoint | Required behavior |
| --- | --- |
| `GET /api/budgets/municipalities` | Return municipalities with at least one published snapshot and their available source periods. |
| `GET /api/budgets/periods?municipality=` | Return published fiscal periods, source labels, date ranges, and available amount types. Unknown municipality returns `404`. |
| `GET /api/budgets/sources?municipality=&period=` | Return published source-document inventory, snapshot metadata, coverage counts, reconciliation-warning summaries, and source-page links where authorized. |
| `GET /api/budgets/facts/:factId` | Return one published fact with hierarchy, units, review state, snapshot provenance, source-cell citations, and warnings. Unpublished or unknown fact IDs return `404`. |
| `GET /api/budgets/download.csv` | Export filtered published facts and required provenance columns using the same filters, stable sort, cursor, and limit rules as collection endpoints. |

JSON collection endpoints accept only their documented query parameters and reject unknown, repeated, empty, or malformed values with `400`. They accept `limit` from 1 through 1,000 and a non-negative numeric `cursor` offset, use a stable route-specific sort, and return `pagination.limit`, `pagination.cursor`, and `pagination.next_cursor`. CSV downloads use the same pagination controls and return the next cursor in `X-Next-Cursor`.

All JSON endpoints return the standard envelope fields: `data`, `filters`, `periods`, `scope`, `units`, `coverage`, `provenance`, `warnings`, and `pagination`. CSV downloads return applicable warnings in `X-Budget-Warnings`.

## Required Controls

- Read only from `budget.v_published_facts` and related source metadata for the same published snapshot.
- Do not expose snapshot 1 while it remains `draft`.
- Enforce `limit` and cursor pagination, stable sort, and `400` for unknown filters.
- Preserve fiscal-period labels and date ranges; do not relabel them as calendar years.
- Include the accepted 2026/2027 debt-balance discrepancy as a warning wherever its affected source or fact is returned.
- Preserve source coordinates and identifiers in fact and CSV provenance.
- Return `200` with empty data and `no_published_snapshot` for a valid request when no published coverage exists.

## Explicitly Deferred

- `/summary`, `/operating`, `/capital`, `/revenue`, `/debt`, `/reserves`, and `/compare` aggregate/explorer endpoints.
- Public `/budgets` pages, charts, and source-page rendering.
- Cross-period aggregate comparisons until compatibility logic and coverage notices are implemented.
- Cross-municipality comparisons, per-capita calculations, inflation adjustments, writes, authentication, and administrative review actions.

## Acceptance Criteria

1. With no published snapshot, all in-scope collection endpoints return empty data and `no_published_snapshot`; no draft facts are leaked.
2. After a snapshot is published, discovery and source endpoints return only its documents, periods, and facts.
3. Fact-detail and CSV provenance exactly match `budget.fact_source` and source-cell records.
4. Pagination has no duplicates or omissions across a stable snapshot.
5. API tests cover draft exclusion, unknown filters, missing fact IDs, source-scope isolation, CSV schema, and the accepted debt warning.
6. The p95 target remains under 500 ms for a single-municipality filtered request against the three-year snapshot.

## Follow-On Sequence

1. Implement the first slice and automated tests against a published test fixture or approved published snapshot.
2. Implement summary and operating/capital aggregate endpoints with explicit no-double-counting controls.
3. Implement comparison and coverage warnings only after compatibility rules are executable.
4. Add public pages after their API contracts and accessibility tests pass.

## Sources

- [Budget API and UI contract](./api-and-ui-contract.md)
- [Three-year snapshot proposal](./three-year-publication-snapshot-proposal.md)
- [Municipal budget requirements](./requirements.md)
- [Municipal budget database schema](./database-schema.md)
