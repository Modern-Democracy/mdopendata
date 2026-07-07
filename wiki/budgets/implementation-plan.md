---
type: project
tags:
  - budget
  - implementation-plan
  - testing
updated: 2026-07-07
---

This page defines the estimated implementation sequence and test gates for the Charlottetown budget prototype.

# Budget Implementation And Test Plan

## Planning Basis

Estimate: eight working weeks for one engineer with periodic financial-data review. The estimate begins after approval of the requirements and proposed schema. It excludes obtaining external population/inflation datasets and production hosting changes.

The three annual PDFs are one source family, not assumed to be one layout template. Each document must pass discovery before reuse of parsing rules.

## Timeline

| Week | Work | Exit gate |
| --- | --- | --- |
| 1 | Profile all three PDFs; inventory pages, tables, column patterns, entities, periods, continuation pages, and source variations. Select representative tables. | Reviewed source matrix with no unclassified table family. |
| 2 | Build a representative-table spike for operating detail, Bell Aliant multi-period statement, capital partner-funding deductions, property-tax calculation, and debt schedule. Validate proposed keys and value states. | Architecture/schema approval; migrations may begin. |
| 3 | Add `budget` schema migrations, constraints, publication views, and seed dimensions. Adapt raw extraction to stable document/table/row/cell keys and coordinates. | Migration tests and idempotent rerun tests pass. |
| 4 | Normalize and review the complete 2026/2027 document. Implement continuation joining, row semantics, hierarchy, period mapping, and reconciliation reports. | Every table has a disposition; reviewed operating/capital totals reconcile or have documented exceptions. |
| 5 | Ingest 2025/2026 and 2024/2025. Add versioned label mappings, project aliases, restatement handling, and cross-period comparability records. | Three-document coverage report approved; compatible facts compare without overwriting restatements. |
| 6 | Implement read APIs, pagination, CSV export, fact provenance, coverage, and comparison compatibility responses. | API contract, query, error-state, and performance tests pass. |
| 7 | Implement `/budgets` landing, operating, capital, revenue, comparison, and sources views with accessible tables and source links. | Browser tests pass for primary public tasks, empty states, and source tracing. |
| 8 | Full reconciliation, accessibility, regression, performance, backup/rebuild, and reviewer acceptance. Correct defects and freeze the first publication snapshot. | Prototype release checklist passes with no unresolved critical issue. |

Week 1 completed on 2026-07-07. The [three-year source profile](../charlottetown/sources/budget-three-year-source-profile.md) inventories 392 pages, 288 table/profile candidates, 160 continuation candidates, material source variations, and the representative-table set for Week 2.

## Representative-Table Spike

The schema gate must use these 2026/2027 layouts:

- PDF page 30: hierarchical operating detail with labels and right-aligned amounts
- PDF page 105: reporting-entity statement with current/prior periods, revenue, grants, expenses, deductions, and earnings/loss
- PDF page 111: capital gross, external partner funding in parentheses, and net totals
- PDF page 149: assessment base multiplied by rate with class and residency hierarchies
- PDF page 151: debt instrument, balance, principal, interest, maturity embedded in labels, and reported totals

## Test Strategy

### Extraction Tests

- golden tests for page/table boundaries, headers, row order, cells, coordinates, signs, dashes, and continuation joins
- source-hash and stable-key tests across reruns
- regression fixtures for each materially different table family in each annual PDF
- explicit tests that narrative dates and project-profile numbers are not imported as financial facts

### Database Tests

- migration up/rebuild in a clean database
- foreign-key, uniqueness, value-state, provenance, and hierarchy constraints
- idempotent import and changed-source detection
- document-specific restatement preservation
- publication snapshot immutability

### Financial QA

- operating revenue and expense reconciliation by statement and period
- capital gross minus reported funding deductions equals reported net where the source asserts that relation
- rate times assessment checks with source rounding tolerance
- debt principal plus interest checks against reported debt-service totals
- summary/detail duplicate detection
- manual sample back to rendered pages for every table family

### API And Browser Tests

- endpoint schema, filtering, sorting, pagination, CSV, unavailable-data, and incompatibility responses
- no double counting when switching hierarchy levels
- period and entity scope retained in navigation URLs
- keyboard navigation, table semantics, chart text alternatives, contrast, and responsive layouts
- source links open the correct document page and highlight the cited cell where available
- p95 response measurement on the complete three-document prototype dataset

## Quality Thresholds

- 100% of detected source tables have a disposition: published, review-blocked, non-financial, duplicate summary, or excluded with reason.
- 100% of public facts have source provenance or an explicit derivation chain.
- 100% of published statement totals either pass reconciliation or display an approved exception.
- No unresolved high-severity extraction or accounting-scope issue enters a publication snapshot.
- Automated tests cover every observed table family, not only every document.

## Stop Conditions

Stop and return to requirements or architecture when:

- a source uses a fiscal period, accounting basis, entity scope, or unit that the schema cannot represent
- a reused parser rule materially misclassifies a new annual layout
- reported totals cannot be reconciled and the cause is unknown
- cross-period identity requires an unapproved normalization decision
- implementation would expose unreviewed values as equivalent public facts

## Deliverables

- approved wiki contracts in this section
- source-pattern matrix for all three Charlottetown PDFs
- SQL migrations and publication views
- repeatable extraction/normalization scripts and review outputs
- three-document normalized dataset and reconciliation report
- budget APIs and CSV export
- public budget pages and source viewer integration
- automated test suite and release checklist

## Sources

- [Requirements](./requirements.md)
- [Database schema](./database-schema.md)
- [API and UI contract](./api-and-ui-contract.md)
- [Charlottetown 2026/2027 first pass](../charlottetown/sources/budget-2026-2027-first-pass.md)
- [Charlottetown three-year source profile](../charlottetown/sources/budget-three-year-source-profile.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 30, 105, 111, 149, and 151
