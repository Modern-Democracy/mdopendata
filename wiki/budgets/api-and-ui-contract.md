---
type: implementation
tags:
  - budget
  - api
  - web-ui
updated: 2026-07-13
---

This page defines the public budget routes, read APIs, filters, visualization rules, and unavailable-data behavior.

# Budget API And UI Contract

## Website Routes

| Route | Purpose |
| --- | --- |
| `/budgets` | Structured contents page using the 2026/2027 table-of-contents pattern across all editions. It does not render an unsorted line-item dump. |
| `/budgets/overview` | Source-authored preamble facts, standardized strategic-plan facts, and universal editorial budget guides. |
| `/budgets/operating` | Operating hierarchy and department entry points. |
| `/budgets/departments/:departmentKey` | Department summary, programs/services, highlights, operating observations, and associated capital projects. |
| `/budgets/capital` | Capital programs and projects, separate from operating sections. |
| `/budgets/projects/:projectKey` | Project facts, including source project name, department, description, and strategic alignment where reported, plus capital observations. |
| `/budgets/appendices` | Property-tax and long-term-debt schedules, explicitly separate from operating and capital. Missing source appendices are labeled as absent. |
| `/budgets/facts` | Contextual narrative, attribute, and list facts only. |
| `/budgets/observations` | Financial observation explorer with edition, section, department, program, project, category, statement, amount, role, and text filters. |
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
| `GET /api/budgets/editions` | `municipality` | Approved annual budget documents, their primary fiscal period, subsequent document, and financial-observation counts. |
| `GET /api/budgets/structure` | `municipality`, required `document` | Reviewed hierarchical sections, page ranges, contextual-fact counts, and editorial guides. |
| `GET /api/budgets/dimensions` | `municipality`, optional `document` | Filter dimensions available in the selected published budget edition. |
| `GET /api/budgets/facts` | `municipality`, optional document, section, department, project, and text filters | Paginated source-authored contextual facts. `fact` never means a financial value. |
| `GET /api/budgets/facts/:factId` | fact id | One contextual fact with page-level citations. |
| `GET /api/budgets/observations` | `municipality`, optional document, period, entity, section, department, program, project, category, status, statement, amount, role, and text filters | Paginated published financial observations with effective assignments and approved subsequent observations. Section filters include all descendants. |
| `GET /api/budgets/observations/:observationId` | observation id | One financial observation with exact source-cell citations and applicable reconciliation warnings. |
| `GET /api/budgets/observations.csv` | observation filters | Reviewed financial observations with provenance columns. |
| `GET /api/budgets/summary` | `municipality`, `period`, optional `entity` | Reviewed headline operating revenue/expense, capital gross/net, debt service, and coverage. |
| `GET /api/budgets/operating` | municipality, period(s), entity, department, category, amount type | Hierarchical operating facts and totals without summary/detail duplication. |
| `GET /api/budgets/capital` | municipality, period(s), entity, program, project, funding category | Project/program gross, funding, financing, and net facts. |
| `GET /api/budgets/revenue` | municipality, period(s), revenue category, tax class | Revenue facts, rates, assessments, and reported calculations. |
| `GET /api/budgets/debt` | municipality, period(s), entity, instrument | Debt balances, principal, interest, maturity, and source totals. |
| `GET /api/budgets/reserves` | municipality, period(s), entity, reserve | Reserve balances and movements where reported. |
| `GET /api/budgets/compare` | municipality, prior period, current period, optional entity/metric/category, basis | Exact-identity nominal values, numeric and percentage change, matched/unmatched coverage, and incompatibility reasons. |
| `GET /api/budgets/sources` | municipality, period | Documents, pages, tables, extraction counts, and publication state. |
| `GET /api/budgets/sources/:documentId/pages/:pageNumber` | document and page | Page metadata and authorized rendered-page asset location. |
| `GET /api/projects` | municipality, optional document, period, department, program, status, text query | Municipality-scoped capital projects linked to the selected published snapshot, with periods, assignments, and reported gross, funding, and net observations. |
| `GET /api/projects/:projectKey` | municipality | One published capital project with contextual facts, financial observations, lifecycle status, and approved source references. |

All collection endpoints support `limit`, `cursor`, and stable sort. Unknown filters return `400`; missing resources return `404`; unavailable or incompatible comparisons return `200` with an empty data array and machine-readable reasons because the query itself is valid.

## Response Contract

Every financial-observation response includes:

- `data`: observations or aggregates
- `filters`: normalized applied filters
- `periods`: source label, start/end dates, and amount type
- `scope`: municipality, reporting entity, funds, and statement kinds included
- `units`: currency, scale, denominator, and display precision
- `coverage`: published, unresolved, and excluded source counts
- `provenance`: publication snapshot and source document identifiers
- `warnings`: restatement, incompatibility, missing denominator, failed reconciliation, or partial-coverage notices

Aggregates include `aggregation_method`, `input_observation_count`, and `excludes_reported_totals`. Derived metrics include formula and input observation identifiers.

## UI Requirements

### Structured Landing Page

- Use the 2026/2027 hierarchy as the cross-edition display pattern while preserving source page ranges and source absence.
- Separate overview, operating, capital, and appendices at the first level.
- Preserve department and capital-program ordering. Repeated source subtotals and totals are permitted within their sections.
- Do not mix all line items into one landing-page list.

### Contextual Content

- A fact is source-authored narrative, attribute, or list content with a title, body, and citation.
- `content_json.blocks` preserves semantic `heading`, `paragraph`, `unordered_list`, and `ordered_list` blocks. PDF line wrapping is removed from paragraph text; source list items are rendered as semantic HTML lists.
- Universal explanations of municipal budgeting are versioned editorial guides and are not facts.
- Strategic-plan content is sourced from `docs/charlottetown/Strategic Plan 2022 to 2026_FINAL.pdf` and reused consistently across the three editions.
- Department pages combine facts with operating observations and associated capital projects.
- Project pages combine project-profile facts with capital observations.

### Spending And Revenue Explorers

- Use an accessible table as the canonical representation.
- Render one HTML row per source row or normalized line item. Render document periods and measures as ordered columns, not as separate rows.
- Ordinary financial tables use fiscal-period identity for column alignment. Tax and debt schedules use physical source-column order and reviewed source labels such as `Assessment`, `Rate`, `Tax Revenue`, `2026 Balance`, `2026/2027 Principal`, and `2026/2027 Interest`.
- Each value cell retains its own financial-observation evidence link.
- Add bar, treemap, or flow views only when the same filtered data remains available in the table.
- Support drill-down from normalized category to source department/service/line item.
- Show absolute and percentage change together; suppress percentage change when the baseline is zero or missing.
- Never combine operating and capital into one unlabeled spending total.
- Display edition-wide operating overview statements before department navigation.
- Display edition-wide capital overview statements before capital programs and project profiles.

### Capital Explorer

- Show gross project/program cost, each reported funding deduction/source, and net municipal cost separately.
- Distinguish a capital schedule line from a narrative project-profile number.
- Allow filtering by department, program, project, funding source, and period.
- Exclude registry projects that have no financial observation in the selected published snapshot.
- Display `unknown` when the registry contains no source-supported lifecycle status; do not infer a lifecycle state in the API or UI.

### Comparison

- Default to nominal reported dollars.
- Label fiscal-period date ranges, amount types, entities, units, and taxonomy version.
- Disable comparisons with incompatible units or scopes and display the specific reason.
- Show coverage side by side so missing categories are not rendered as zero.
- Per-capita and inflation-adjusted bases remain unavailable until approved denominator/index datasets exist.
- The first implemented comparison slice matches only identical municipality, taxonomy version, reporting entity, statement key, line key, amount type, and measure unit within one published snapshot.
- Unmatched observations are excluded with visible coverage counts and must never be converted to zero.
- Percentage change is unavailable when the prior value is zero.

### Source And Trust Controls

- Each financial row links to an observation detail and exact source page/cell when coordinates exist. Each contextual fact links to its source page.
- Visible badges distinguish reported, derived, restated, partial, and review-exception values.
- The sources page reports extraction and reconciliation completeness, not a generic confidence score alone.
- A rendered source page is available only when its document belongs to the selected published snapshot and its page number is within the registered PDF bounds.
- Rendered pages validate repository-local PDF paths and expose immutable document-hash headers; source paths are never returned publicly.

## Visualization Rules

- Prefer sorted bars over pie charts for category comparison. The source PDF pie chart on page 19 is evidence, not a required UI pattern.
- Use consistent colors for revenue, operating expense, capital gross, external funding, and net capital across pages.
- Do not use area or volume to compare negative funding deductions with positive spending.
- Charts must expose labels, values, units, keyboard access, text alternatives, and downloadable underlying data.
- Truncate no financial labels without a full accessible label or tooltip.

## Performance Targets

- Server response target: p95 under 500 ms for a single-municipality summary or filtered table against a publication snapshot.
- Initial route target: usable content under 2 seconds on a typical broadband connection, excluding first source-page image retrieval.
- Paginate detailed observations and facts; do not send all source rows or page images in summary responses.
- Cache immutable publication snapshots and rendered source pages by document hash.

## Sources

- [Requirements](./requirements.md)
- [Database schema](./database-schema.md)
- [Municipal portal product purpose](../product/municipal-portal-purpose.md)
- [Web UI stack](../implementation/web-ui-stack.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 19, 105, 111, 149, and 151
