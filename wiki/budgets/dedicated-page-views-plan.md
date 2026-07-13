---
type: project
tags:
  - budget
  - web-ui
  - analysis
  - implementation-plan
updated: 2026-07-13
---

This page defines the review-gated plan for replacing the current combined budget page with useful year, department, project, and municipal-analysis views.

# Dedicated Budget Page Views Plan

## Status

Phase 1 implemented for browser review. The budget-edition page, fact explorer, schema migration, assignment writes, snapshot `1` taxonomy revision, and filter enforcement were authorized and completed on 2026-07-13. Dedicated cross-year department, project-detail, and municipal-analysis routes remain planned.

## Requested Outcome

Provide four public tasks:

1. Select one budget year and inspect authoritative overall figures, department figures, and that year's capital projects.
2. Select one department and compare its reviewed figures across every supported fiscal year.
3. Select one capital project, optionally filter its facts by budget year, and inspect its multi-year financial and descriptive evidence.
4. Analyze one municipality's budget across all supported years through meaningful, source-auditable measures and visualizations.

The current `/budgets` page must stop combining all four tasks into one exploratory dashboard.

## Verified Current-State Findings

- `/budgets` is one 16.9 KB React/Babel HTML file. It loads summary, project, comparison, and source data into one route with no task-specific information architecture.
- Its headline cards sum non-duplicated detail facts. Those sums are explicitly exploratory and are not authoritative statement totals.
- Period discovery collapses rows by fiscal-period label in the browser. A label can occur in multiple source documents, so a selection can combine the selected annual budget PDF's own budget figures with a later PDF's prior-period presentation. For example, `2024-2025-budget` currently selects 845 facts from document `7` and 715 facts from document `8`; `2025-2026-budget` selects 1,220 facts from document `8` and 529 facts from document `9`.
- Published facts include 6,256 rows and 182 registered capital projects. Existing project list and detail endpoints provide a strong base for a dedicated project view.
- Only 389 published facts have a line-level `organization_unit_id`. All such facts originate in source document `9`; the prior-year normalized imports did not assign organization units.
- Of the 6,256 published facts, 207 facts are linked to 172 published capital projects. None of the 182 registered project records has an `organization_unit_id`, and none of the 207 project-linked facts has a line-level organization unit. Twenty-four published projects have an approved `department` profile field that can seed reviewed assignment; the other 148 require schedule-hierarchy or other source-evidence review.
- The remaining 6,049 non-project facts include 5,341 operating or facility-operating facts, 511 unlinked capital facts, 103 debt facts, and 94 tax, assessment, or rate facts. Only 389 of those non-project facts currently carry a department assignment.
- Thirteen organization units are currently classified as departments. Their visible period coverage comes from the 2026/2027 document's current, prior-budget, and forecast columns, not independently from every annual source document.
- The operating endpoint accepts a `department` parameter but does not apply it. Other documented filters such as capital `program` and `project` are also accepted without complete query enforcement.
- The published view exposes `organization_unit_id` but not its key, name, type, parent, or effective dates.
- Snapshot `1` has no populated normalized categories. Category-based composition or cross-municipality analysis is therefore not ready.
- Cross-period comparison is limited to exact published identities. It reports 440 matches for 2025/2026 to 2026/2027 and correctly excludes unmatched facts instead of treating them as zero.

## Proposed Route Model

| Route | Primary task | Default behavior |
| --- | --- | --- |
| `/budgets` | Budget-year view | Open the latest canonical budget observation and retain the selected municipality and period in the URL. |
| `/budgets/departments` | Department comparison | Require or prompt for a reporting entity and reviewed department identity. |
| `/budgets/projects` | Capital-project detail | Show the project selector across the snapshot; an optional period narrows displayed facts but not project identity. |
| `/budgets/analysis` | Municipal analysis | Show all-year nominal analysis only for measures that pass the metric-catalogue gate. |
| `/budgets/sources` | Existing trust workflow | Retain source inventory, coverage, warnings, and rendered source pages as a supporting route. |

A persistent budget subnavigation will expose Year, Departments, Projects, Analysis, and Sources. The existing `/budgets/operating`, `/budgets/capital`, `/budgets/revenue`, `/budgets/debt-reserves`, and `/budgets/compare` contract should be reevaluated after these four tasks work; it should not be implemented as a parallel second navigation model by default.

## Shared Semantic Gates

### Budget Edition And In-Document Observation

Treat the budget-year selector as an annual budget-edition selector. Selecting 2025/2026 must select the 2025/2026 budget PDF and show the city totals, department breakdowns, capital projects, and other values reported as that document's own budget figures. It must not add the 2026/2027 PDF's presentation of 2025/2026 values.

Prior-budget, forecast, actual, and later-restated values within other PDFs remain valid published observations, but they must be explicitly labeled and separately selectable for comparison or audit. The design spike must select and document one durable representation, preferably explicit budget-edition, primary-fiscal-period, and observation-role metadata rather than title parsing in API queries. The API must return source document, observation role, fiscal label, date range, amount type, and default-edition status.

### Headline Measure Catalogue

Create a reviewed catalogue for each displayed measure with:

- stable key and public label
- included reporting entities and statement scopes
- allowed statement kinds, amount types, units, and aggregation roles
- whether the value is reported or derived
- formula and input fact IDs for derived values
- source total, reconciliation result, and warning behavior
- valid periods and explicit unavailable states

At minimum, assess operating revenue, operating expense, operating surplus or deficit, capital gross, external capital funding, net municipal capital, debt balance, principal, interest, and debt service. Do not display a measure when its accounting scope or source-total identity is unresolved.

### Department Identity And Coverage

Backfill reviewed organization-unit assignments for prior annual documents before claiming an all-year department view. Repeated or renamed department labels require source-document, statement, entity, and hierarchy evidence; text equality alone is insufficient.

The review output must enumerate every unresolved assignment by source page, table or section, raw label, values, exact ambiguity, and proposed normalization. The UI must show missing department coverage as unavailable, not zero.

Project department assignment is a separate reviewed backfill. Use the 24 approved project-profile `department` fields as direct candidates, then use capital-schedule section hierarchy and project-reference evidence for the remaining 148 published projects. Do not derive a department from project-name keywords. The accepted target is one reviewed project-to-organization-unit assignment where the source supports it, with an explicit unresolved state otherwise.

### Analysis Metric Gate

Every analytical chart must answer a named public question and be backed by the headline measure catalogue or exact compatible identities. Category-dependent analysis remains deferred until the normalized-category taxonomy, versioned assignment relation, mappings, and category-aware snapshot are approved.

The normalized-category direction and versioned-assignment design were accepted for browser evaluation. The project owner separately authorized migration, assignment writes, and changing snapshot `1`. The implementation preserves its 6,256 fact memberships and source documents, applies an explicit taxonomy revision overlay, retains raw labels, and marks controlled-label category assignments as proposed.

## Page Contracts

### Budget-Year View

Purpose: answer what the municipality budgeted for the selected fiscal year and where the user can inspect the evidence.

Required sections:

- fiscal-period and canonical-observation selector with source document and date range
- reporting scope and warning banner above every figure
- reviewed headline cards, with reported and derived states distinguished
- department table containing comparable revenue, expense, and net measures only where defined
- capital-project table for the selected observation with gross, funding deductions, net, entity, and source-supported status
- direct links to fact evidence, filtered CSV, and selected source document
- coverage panel showing published, excluded, unmatched, and unresolved inputs

Acceptance requires that no card or table combines original and restated observations, no summary/detail double counting occurs, and every displayed number has a traceable fact or derivation chain.

### Department View

Purpose: answer how one reviewed department's budget changed across all available annual observations.

Required sections:

- reporting-entity and department selectors grouped by stable organization-unit identity
- one row per canonical annual observation, with revenue, expense, net, fact coverage, and warnings
- accessible nominal trend chart backed by the same table
- largest exact-identity line-item changes between adjacent supported years
- associated capital projects only when a reviewed project-to-organization-unit link exists
- explicit gaps for years without an approved assignment or compatible measure

Department comparison must not infer continuity through label similarity. Renames, splits, merges, or reporting-entity moves require reviewed compatibility records or visibly separate series.

### Project View

Purpose: answer what a project is, which annual budgets reference it, and what each source reports.

Required sections:

- searchable project selector plus optional fiscal-period filter
- stable project identity, reporting entity, source-supported lifecycle status, location, and description
- year-by-year gross, funding deduction, and net table without combining unlike amount types
- all other published project facts grouped by annual observation and unit
- approved profile fields grouped by source document, retaining raw and normalized values
- approved references with exact document and rendered-page links
- unavailable states for absent lifecycle, profile, location, funding, or period data

The period filter narrows evidence displayed; it must not create a year-owned project identity or hide the project's overall multi-year coverage.

### Municipal Analysis View

Purpose: explain how the municipality's budget changed over time without implying unsupported causation, actual spending, inflation adjustment, or per-capita results.

The initial design spike should validate these user questions in order:

1. How did reviewed operating revenue and expense change across canonical annual observations?
2. How did gross capital, external funding, and net municipal capital change?
3. How did debt balance, principal, interest, and debt service change where comparable?
4. Which exact compatible line items produced the largest nominal increases and decreases?
5. How complete and comparable is each year before interpreting the trends?

Proposed initial visualizations are a table-backed operating trend, a grouped capital funding chart, a debt trend, sorted increase/decrease bars, and a comparison-coverage matrix. Every chart requires keyboard-readable labels, units, source scope, downloadable inputs, and a plain-language limitation.

Do not initially add category shares, service-mix analysis, cross-municipality ranking, inflation adjustment, per-capita measures, forecasts, causal claims, or inferred efficiency metrics. Add them only after their separate data and compatibility gates pass.

## Proposed API Work

| API capability | Required change |
| --- | --- |
| Budget observations | Replace label-only discovery with explicit document-owned observations and canonical/default metadata. |
| Headline measures | Replace exploratory detail sums with catalogue-backed reported or approved-derived measures and derivation/provenance metadata. |
| Department discovery | Return stable unit ID, key, name, type, parent, reporting entity, effective dates, available observations, and coverage. |
| Department series | Return one scoped measure set per canonical observation plus exact-identity changes and incompatibility reasons. |
| Project list/detail | Add explicit observation metadata, enforce optional period filtering consistently, and return rendered-page links for profiles and references. |
| Municipal analysis | Return only approved metric-catalogue series, exact-change rankings, and a period-by-measure compatibility matrix. |
| Downloads | Apply the same observation, department, project, and metric filters as the page and retain provenance identifiers. |

All endpoints must continue reading through the published-snapshot boundary, reject unsupported or repeated filters, paginate detail collections, and return standard scope, units, coverage, provenance, warnings, and pagination fields.

## Technical Shape

- Retain the existing server-side Node API boundary and React/Babel UI posture. Do not introduce a framework, state library, chart library, or build tool without separate approval.
- Replace the single monolithic budget page with a small budget shell and route-specific view files. Share only behavior used by at least two routes, starting with context, selectors, status/provenance, canonical tables, and accessible bar or trend rendering.
- Derive municipality from portal context or URL state instead of the current hard-coded browser constant.
- Preserve all selections in query parameters so links are reproducible and browser navigation works.
- Keep tables canonical. Charts render only the same filtered data and never become the sole representation.
- A schema migration is permitted only if the canonical-observation spike proves existing metadata cannot represent the reviewed policy. Any migration requires separate approval and DevOps execution.

## Ordered Delivery Plan

### 1. Approve Product And Accounting Decisions

Approve the routes, default root behavior, canonical observation policy, department scope, headline measures, and initial analysis questions. Exit gate: no unresolved choice changes grouping, totals, compatibility, or URL behavior.

### 2. Complete Data-Contract Spikes

Inventory every annual observation, authoritative source total, department assignment, project-to-unit link, and analysis metric. Produce exact review registers for department gaps and observation conflicts. Exit gate: each page field is classified as ready, partial with explicit behavior, or blocked.

### 3. Correct And Extend APIs

Implement observation discovery, catalogue-backed headline measures, department discovery/series, project evidence links, and analysis series. Enforce every documented filter. Exit gate: API contract, source-scope, no-merge, no-double-counting, pagination, warning, and performance tests pass.

### 4. Build Shared Budget Navigation And States

Add route entrypoints, municipality context, query-state handling, selection controls, loading, empty, partial, unavailable, error, and provenance components. Exit gate: every dedicated route is directly addressable and preserves context through navigation.

### 5. Build Project And Budget-Year Views

Build the project view first because its identity and detail API are substantially present, then the budget-year view after headline measures and observation identity pass. Exit gate: primary public tasks and source tracing pass browser and accessibility tests.

### 6. Build Department View

Proceed only after prior-year unit coverage and compatibility decisions are reviewed. Exit gate: all-year series contains no label-based inference, missing years remain missing, and displayed totals reconcile to approved inputs.

### 7. Prototype And Review Municipal Analysis

Create a low-fidelity layout using real approved series, review whether each chart answers its named question, then implement only accepted charts. Exit gate: user review accepts the metric definitions, chart set, explanatory text, and limitations before visual polish.

### 8. Final QA And Documentation

Run route/API smoke tests, database regression tests, keyboard and screen-reader checks, responsive checks, source-link verification, p95 measurements, and a published-snapshot leakage test. Update the API/UI contract and budget wiki only after behavior is accepted.

## Test And Acceptance Matrix

- A budget-year selection resolves to one annual budget edition and that PDF's own budget observations unless the user explicitly selects another source observation.
- Authoritative cards match reviewed reported totals or approved derivations exactly; exploratory sums are not presented as totals.
- Original and later-restated values remain distinct and visibly labeled.
- Department filters change query results and never act as accepted no-ops.
- Department series use reviewed stable identities and show unavailable coverage rather than zero.
- Project facts retain gross, funding deduction, net, narrative, and non-currency distinctions.
- Every chart has a matching table, unit, scope, source/provenance access, and text alternative.
- Query parameters reproduce municipality, observation, department, project, and view state.
- Empty, partial, incompatible, warning, and no-published-snapshot states are covered.
- Existing fact detail, source rendering, CSV, project identity, comparison, and snapshot-isolation behavior does not regress.
- Single-municipality summary and analysis endpoints meet the p95 under 500 ms target; initial usable route content meets the two-second target.

## Remaining Decisions For Later Phases

1. Review the implemented `/budgets` and `/budgets/facts` browser surfaces and classify proposed category false positives and omissions.
2. Approve department scope for the dedicated cross-year page, including treatment of separately reported facilities.
3. Approve the initial municipal-analysis questions, measures, and charts before implementation.
4. Decide whether later-document `forecast` is the final public label for the requested reported amount or whether a broader restatement model is required.

## Sources

- [Municipal budget requirements](./requirements.md)
- [Budget API and UI contract](./api-and-ui-contract.md)
- [Public budget API implementation scope](./public-api-implementation-scope.md)
- [Municipal budget database schema](./database-schema.md)
- [Capital project lifecycle and references](./capital-project-lifecycle.md)
- [Normalized category taxonomy proposal](./normalized-category-taxonomy-proposal.md)
- [Budget web and taxonomy implementation status](./budget-web-taxonomy-implementation-status.md)
- [Municipal portal UI architecture](../product/municipal-portal-ui-architecture.md)
- [Municipal portal UI component architecture](../product/municipal-portal-ui-component-architecture.md)
- `web/public/ui_kits/budgets/index.html`, inspected 2026-07-13
- `web/server.js`, inspected 2026-07-13
- `budget.v_published_facts`, `budget.organization_unit`, and `budget.capital_project`, queried 2026-07-13
