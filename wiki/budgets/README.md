---
type: index
tags:
  - budget
  - municipal-portal
updated: 2026-07-07
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

## Current Evidence

The first pass of the 2026/2027 PDF found 154 pages, 114 table or project-profile candidates, 3,233 raw rows, and 2,420 detected value tokens. The document includes overview charts with source tables, operating summaries and detailed breakdowns, third-party facility budgets, capital schedules and project profiles, property and utility rates, assessment calculations, and debt schedules.

The existing artifacts are discovery inputs, not publishable normalized facts. Their page-granular manifests do not yet join continuation pages or reliably distinguish detail rows, headings, subtotals, deductions, and totals.

Week 1 profiling is complete for all 392 pages. See the [three-year Charlottetown source profile](../charlottetown/sources/budget-three-year-source-profile.md) for the source-pattern matrix and representative schema-spike tables.

## Decisions

- Fiscal periods are modeled with dates and source labels. The product must not relabel municipal fiscal periods as calendar years.
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
