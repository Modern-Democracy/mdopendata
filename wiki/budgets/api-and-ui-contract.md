---
type: implementation
tags:
  - budget
  - api
  - web-ui
updated: 2026-07-12
---

This page defines the public budget routes, read APIs, filters, visualization rules, and unavailable-data behavior.

# Budget API And UI Contract

## Website Routes

| Route | Purpose |
| --- | --- |
| `/budgets` | Municipality budget landing page with period selector, headline totals, spending, revenue, capital, and coverage summary. |
| `/budgets/operating` | Operating revenue and expense explorer with hierarchy and period comparison. |
| `/budgets/capital` | Capital programs, projects, gross cost, funding sources, and net municipal cost. |
| `/budgets/revenue` | Revenue-source, tax, assessment, utility-rate, grant, fee, transfer, and financing explorer. |
| `/budgets/debt-reserves` | Debt balances/service and reserve movements when published. |
| `/budgets/compare` | Cross-period and future cross-municipality comparison with compatibility and coverage notices. |
| `/budgets/sources` | Document inventory, extraction coverage, reconciliation status, and source-table browser. |

Default municipality is selected through portal context, not hard-coded into database queries. URLs preserve municipality and period selections through query parameters.

## Public Read APIs

| Endpoint | Key parameters | Response |
| --- | --- | --- |
| `GET /api/budgets/municipalities` | none | Municipalities with published snapshots and available periods. |
| `GET /api/budgets/periods` | `municipality` | Fiscal periods, source labels, dates, and available amount types. |
| `GET /api/budgets/summary` | `municipality`, `period`, optional `entity` | Reviewed headline operating revenue/expense, capital gross/net, debt service, and coverage. |
| `GET /api/budgets/operating` | municipality, period(s), entity, department, category, amount type | Hierarchical operating facts and totals without summary/detail duplication. |
| `GET /api/budgets/capital` | municipality, period(s), entity, program, project, funding category | Project/program gross, funding, financing, and net facts. |
| `GET /api/budgets/revenue` | municipality, period(s), revenue category, tax class | Revenue facts, rates, assessments, and reported calculations. |
| `GET /api/budgets/debt` | municipality, period(s), entity, instrument | Debt balances, principal, interest, maturity, and source totals. |
| `GET /api/budgets/reserves` | municipality, period(s), entity, reserve | Reserve balances and movements where reported. |
| `GET /api/budgets/compare` | municipality list, period list, metric/category, basis | Compatible values, change measures, coverage, and incompatibility reasons. |
| `GET /api/budgets/facts/:factId` | fact id | One fact with hierarchy, review status, derivation, and exact source citation. |
| `GET /api/budgets/sources` | municipality, period | Documents, pages, tables, extraction counts, and publication state. |
| `GET /api/budgets/sources/:documentId/pages/:pageNumber` | document and page | Page metadata and authorized rendered-page asset location. |
| `GET /api/budgets/download.csv` | same filters as fact endpoints | Reviewed filtered facts with provenance columns. |
| `GET /api/projects` | municipality, period, status, text query | Municipality-scoped capital projects linked to the selected published snapshot, with periods and reported gross, funding, and net facts. |
| `GET /api/projects/:projectKey` | municipality | One published capital project with lifecycle status, multi-year facts, approved source references, and approved profile fields. |

All collection endpoints support `limit`, `cursor`, and stable sort. Unknown filters return `400`; missing resources return `404`; unavailable or incompatible comparisons return `200` with an empty data array and machine-readable reasons because the query itself is valid.

## Response Contract

Every financial response includes:

- `data`: facts or aggregates
- `filters`: normalized applied filters
- `periods`: source label, start/end dates, and amount type
- `scope`: municipality, reporting entity, funds, and statement kinds included
- `units`: currency, scale, denominator, and display precision
- `coverage`: published, unresolved, and excluded source counts
- `provenance`: publication snapshot and source document identifiers
- `warnings`: restatement, incompatibility, missing denominator, failed reconciliation, or partial-coverage notices

Aggregates include `aggregation_method`, `input_fact_count`, and `excludes_reported_totals`. Derived metrics include formula and input fact identifiers.

## UI Requirements

### Landing Page

- State the selected fiscal period and reporting scope above all numbers.
- Show operating revenue, operating expense, gross capital, external capital funding, net capital, and debt service only when reviewed.
- Separate reported totals from derived explanatory text.
- Provide direct actions for spending, revenue, capital, comparison, and sources.

### Spending And Revenue Explorers

- Use an accessible table as the canonical representation.
- Add bar, treemap, or flow views only when the same filtered data remains available in the table.
- Support drill-down from normalized category to source department/service/line item.
- Show absolute and percentage change together; suppress percentage change when the baseline is zero or missing.
- Never combine operating and capital into one unlabeled spending total.

### Capital Explorer

- Show gross project/program cost, each reported funding deduction/source, and net municipal cost separately.
- Distinguish a capital schedule line from a narrative project-profile number.
- Allow filtering by department, program, project, funding source, and period.
- Exclude registry projects that have no fact in the selected published snapshot.
- Display `unknown` when the registry contains no source-supported lifecycle status; do not infer a lifecycle state in the API or UI.

### Comparison

- Default to nominal reported dollars.
- Label fiscal-period date ranges, amount types, entities, units, and taxonomy version.
- Disable comparisons with incompatible units or scopes and display the specific reason.
- Show coverage side by side so missing categories are not rendered as zero.
- Per-capita and inflation-adjusted bases remain unavailable until approved denominator/index datasets exist.

### Source And Trust Controls

- Each chart and row links to a fact detail and highlighted source page/cell when coordinates exist.
- Visible badges distinguish reported, derived, restated, partial, and review-exception values.
- The sources page reports extraction and reconciliation completeness, not a generic confidence score alone.

## Visualization Rules

- Prefer sorted bars over pie charts for category comparison. The source PDF pie chart on page 19 is evidence, not a required UI pattern.
- Use consistent colors for revenue, operating expense, capital gross, external funding, and net capital across pages.
- Do not use area or volume to compare negative funding deductions with positive spending.
- Charts must expose labels, values, units, keyboard access, text alternatives, and downloadable underlying data.
- Truncate no financial labels without a full accessible label or tooltip.

## Performance Targets

- Server response target: p95 under 500 ms for a single-municipality summary or filtered table against a publication snapshot.
- Initial route target: usable content under 2 seconds on a typical broadband connection, excluding first source-page image retrieval.
- Paginate detailed facts; do not send all source rows or page images in summary responses.
- Cache immutable publication snapshots and rendered source pages by document hash.

## Sources

- [Requirements](./requirements.md)
- [Database schema](./database-schema.md)
- [Municipal portal product purpose](../product/municipal-portal-purpose.md)
- [Web UI stack](../implementation/web-ui-stack.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 19, 105, 111, 149, and 151
