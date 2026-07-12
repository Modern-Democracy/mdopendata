---
type: index
tags:
  - budget
  - municipal-portal
updated: 2026-07-09
---

This section defines the municipal budget ingestion, data, API, user-interface, and delivery contracts.

# Municipal Budgets

## Product Outcome

Build a public budget section that ingests municipal operating and capital budget documents, publishes every review-approved table value with source provenance, explains spending and revenue, and supports valid comparisons across fiscal periods and municipalities.

Charlottetown is the prototype municipality. The initial source set is the three PDFs under `docs/charlottetown/budget/`, beginning with the 154-page 2026/2027 financial plan.

## Contract Pages

| Page | Purpose |
| --- | --- |
| [Requirements](./requirements.md) | Product scope, users, functional requirements, rules, edge cases, and acceptance criteria. |
| [Database schema](./database-schema.md) | Proposed PostgreSQL `budget` schema, keys, fact model, provenance, and publication views. |
| [API and UI contract](./api-and-ui-contract.md) | Website routes, read APIs, filters, visualizations, and response behavior. |
| [Implementation and test plan](./implementation-plan.md) | Ordered eight-week prototype plan, gates, test strategy, and completion criteria. |
| [Representative-table schema spike](./representative-table-schema-spike.md) | Source-pattern mapping, confirmed schema fits, blocking gaps, and migration gate status. |
| [Representative-spike normalized mapping](./representative-spike-normalized-mapping.md) | Reviewed raw and normalized import identities, manifest contract, sequencing, and stop conditions. |
| [2026/2027 normalization status](./2026-normalization-status.md) | Full raw import, canonical dispositions, continuation decisions, coverage, and blocked normalization review queue. |
| [2026/2027 normalized import gap report](./2026-normalized-import-gap-report.md) | Database-import blockers, vocabulary translations, provenance requirements, reconciliation coverage, and acceptance criteria. |
| [2026/2027 normalized import Phase 1 decisions](./2026-normalized-import-phase-1-decisions.md) | Proposed manifest protocol, identity rules, inventories, vocabulary mappings, coexistence rule, and Gate 1/2 decisions. |
| [2026/2027 normalized import Phase 2 status](./2026-normalized-import-phase-2-status.md) | Deterministic manifest counts, Gate 3 evidence, and blocking capital-profile alias review. |
| [2026/2027 normalized import Phase 3 status](./2026-normalized-import-phase-3-status.md) | Source-cell provenance results and stale raw-database cell blocker for Gate 4. |
| [2026/2027 normalized import Phase 4 status](./2026-normalized-import-phase-4-status.md) | Reconciliation catalogue coverage, input resolution, exclusions, and Gate 5 readiness. |
| [2026/2027 normalized import Phase 5 status](./2026-normalized-import-phase-5-status.md) | Dry-run importer mode, deterministic plan evidence, rollback proof, and Gate 6 readiness. |
| [2026/2027 normalized import Phase 6 status](./2026-normalized-import-phase-6-status.md) | Controlled import evidence, idempotence rerun, accepted exception, and Gate 7 readiness. |
| [2026/2027 normalized import Phase 7 status](./2026-normalized-import-phase-7-status.md) | Source-fidelity QA, review-decision resolution, representative exclusion, and Gate 8 readiness. |
| [Vehicle Equipment clarification draft](./2026-vehicle-equipment-clarification-draft.md) | Draft request about the Police project profile missing from the approved capital schedule. |
| [Week 5 raw ingestion status](./week-5-raw-ingestion-status.md) | Raw database ingestion status for the 2025/2026 and 2024/2025 budget PDFs before normalized comparability approval. |
| [Prior-year coordinate raw extraction status](./prior-year-coordinate-raw-extraction-status.md) | Visible-PDF raw artifact regeneration, identifier reconciliation, QA evidence, and raw-database boundary. |
| [Week 5 normalized mapping review](./week-5-normalized-mapping-review.md) | Prior-year normalized mapping review classifications, raw coverage blockers, and remaining approval gates. |
| [Prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md) | Step-through normalization, review, import, QA, and compatibility gates for 2025/2026 and 2024/2025. |
| [Prior-year normalized import Phase 1 status](./prior-year-normalized-import-phase-1-status.md) | Period-label and section-continuation review artifacts and remaining Phase 1 blockers for prior-year normalization. |
| [Prior-year normalized import Phase 2 status](./prior-year-normalized-import-phase-2-status.md) | Source-linked row-mapping inputs and remaining row-semantic review for both prior-year documents. |
| [Prior-year normalized import completion status](./prior-year-normalized-import-completion-status.md) | Completed manifests, reconciliations, controlled imports, idempotence, project references, and source-fidelity QA for both prior years. |
| [Capital project lifecycle and references](./capital-project-lifecycle.md) | Source-limited lifecycle rules and municipality-scoped project identity with document-owned references. |
| [Budget ingestion refactor tracker](./budget-ingestion-refactor-tracker.md) | Deferred refactor tracker for separating reusable budget ingestion code from document-specific mappings after prior-year completion. |
| [Three-year publication-snapshot proposal](./three-year-publication-snapshot-proposal.md) | Draft scope, required taxonomy decision, source documents, fact counts, and acceptance checks for the first Charlottetown three-year snapshot. |

## Current Evidence

The first pass of the 2026/2027 PDF found 154 pages, 114 table or project-profile candidates, 3,233 raw rows, and 2,420 detected value tokens. The document includes overview charts with source tables, operating summaries and detailed breakdowns, third-party facility budgets, capital schedules and project profiles, property and utility rates, assessment calculations, and debt schedules.

The existing artifacts are discovery inputs, not publishable normalized facts. Their page-granular manifests do not yet join continuation pages or reliably distinguish detail rows, headings, subtotals, deductions, and totals.

Week 1 profiling is complete for all 392 pages. See the [three-year Charlottetown source profile](../charlottetown/sources/budget-three-year-source-profile.md) for the source-pattern matrix and representative schema-spike tables.

Week 5 raw ingestion has appended the 2025/2026 and 2024/2025 source pages, tables, rows, and cells to the database, including supplemental raw coverage for prior raw-blocked pages. See the [Week 5 raw ingestion status](./week-5-raw-ingestion-status.md). Normalized cross-period comparability remains gated by document-specific mapping and review.

Week 5 normalized mapping review has classified 114 profile candidates for 2025/2026 and 58 profile candidates for 2024/2025. See the [Week 5 normalized mapping review](./week-5-normalized-mapping-review.md). Normalized import remains blocked by document-specific mapping approvals.

The [prior-year normalized import gap report](./prior-year-normalized-import-gap-report.md) defines the step-through gates for completing 2025/2026 and 2024/2025. The [budget ingestion refactor tracker](./budget-ingestion-refactor-tracker.md) records lessons to preserve while deferring generalization until the two prior-year imports are complete and tested against other budget documents.

## Decisions

- Fiscal periods are modeled with dates and source labels. The product must not relabel municipal fiscal periods as calendar years.
- Raw table, row, and value IDs use the contract `<municipality_key>_budget_<fiscal_period_slug>_pNNN`, with rows and values extending the same stem as `_rNNN` and `_vNN`. For Charlottetown the current municipality key is `ctown`, and fiscal-period slugs use underscores, for example `ctown_budget_2024_2025_p014`.
- Budget extraction scripts that generate reusable raw artifacts must accept or derive the municipality key and fiscal period instead of hard-coding `ctown` or `2026_2027`. Document-specific 2026/2027 normalization, reconciliation, import, validation, and test scripts may retain `ctown_budget_2026_2027` controls until they are refactored behind approved mapping packages.
- Reported values and derived values remain distinguishable.
- Cross-municipality comparisons require approved normalized categories and visible coverage differences.
- Raw source labels, cells, table structure, and page coordinates remain available for audit.
- The initial public release is read-only. Extraction review remains an internal validation workflow.

## Sources

- [Requirements](./requirements.md)
- [Charlottetown 2026/2027 first pass](../charlottetown/sources/budget-2026-2027-first-pass.md)
- [Charlottetown three-year source profile](../charlottetown/sources/budget-three-year-source-profile.md)
- [Initial municipal budget data model](../implementation/municipal-budget-data-model.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 10, 19, 30, 105, 111, 149, and 151
