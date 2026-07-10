---
type: project
tags:
  - budget
  - requirements
  - municipal-portal
updated: 2026-07-09
---

This page defines the approved prototype requirements for municipal budget ingestion, publication, explanation, and comparison.

# Municipal Budget Requirements

## Objective

Provide a public, source-auditable view of where municipal money comes from, where it is spent, how approved budgets change over time, and how municipalities compare when equivalent reviewed data exists.

## Prototype Scope

In scope:

- the 2024/2025, 2025/2026, and 2026/2027 Charlottetown financial-plan PDFs
- operating and capital budgets for the City, Water and Sewer Utility, and separately reported facilities or entities
- all tabular values, including budgets, forecasts, revenues, expenses, transfers, partner funding, tax and utility rates, assessments, debt balances, principal, interest, percentages, counts, and totals
- capital project schedules and structured fields from project-profile pages
- source citations down to document, PDF page, table, row, cell, and bounding box where available
- reviewed cross-period and future cross-municipality comparisons
- public read-only pages and APIs, plus extraction-quality reporting

Out of scope for the prototype:

- changing, approving, or forecasting a municipal budget
- claiming actual spending when the source reports only budget or forecast values
- inflation, population, household, or per-capita adjustments without separately sourced denominator/index data
- automated equivalence between municipalities without review
- authentication and public data-correction workflows

## Users And Required Outcomes

| User | Required outcome |
| --- | --- |
| Public reader | Understand total revenue, spending, capital investment, funding sources, and major changes in plain language. |
| Researcher or journalist | Download filtered facts and trace each value to its exact source. |
| Municipal comparator | Compare equivalent periods and normalized categories while seeing coverage and accounting differences. |
| Data validator | Inspect extraction status, confidence, reconciliations, normalization decisions, and unresolved rows. |

## Functional Requirements

### Ingestion And Provenance

- Register each source document with municipality, title, hash, source path or URL, publication state, and observed fiscal-period labels.
- Inventory every page and detect tables, continuation pages, charts with underlying data, schedules, and project profiles.
- Preserve raw text, row order, cell text, indentation, coordinates, table headings, footnotes, signs, blank values, dashes, and parenthesized values.
- Assign stable source identifiers independent of rerun order.
- Store parser version, input hash, run status, confidence, and review state.
- Never publish a normalized fact without a source-cell or source-row citation, except an explicitly labeled derived metric.

### Financial Semantics

- Distinguish operating from capital.
- Distinguish revenue, expense, transfer, financing, funding deduction, debt, reserve movement, rate, assessment, and statistical/non-financial values.
- Distinguish amount types such as budget, forecast, actual, balance, principal, interest, gross, partner funding, net, rate, and percentage.
- Represent subtotals and totals as reported rows. Do not infer that every bold or underlined row is additive.
- Preserve the reporting entity separately from the municipality. The Bell Aliant Centre example has its own operating statement while reporting a City grant.
- Model hierarchy for departments, services, account groups, line items, capital programs, and projects.
- Store fiscal values in long form rather than year-specific columns.
- Store currency as fixed-precision numeric values and never binary floating point.
- For a reviewed currency table, an explicit `0`, blank cell, or dash cell represents a normalized numeric zero with `value_state: reported_zero`. Preserve the original source-cell display (`0`, blank, or `-`) and its physical column identity as provenance; do not apply this rule to non-currency columns without an explicit reviewed mapping.
- Approved row mappings must use the shared per-value `facts` contract: each source value carries its own source value ID, document period, amount type, measure unit, value state, and numeric value. Document layout may vary, but this normalized fact contract does not.

### Review And Reconciliation

- Route low-confidence structure, unknown row semantics, unmatched continuation pages, and new source patterns to review.
- Require reviewer-approved mappings before a raw label participates in normalized cross-period or cross-municipality comparisons.
- Reconcile published statements against reported totals within an explicit tolerance of CAD 1 unless the source uses rounded display units.
- Reconcile derived percentages against source amounts where both are present and flag differences greater than 0.1 percentage point.
- Report extraction coverage by source table and value, including excluded narrative, unresolved rows, and unresolved values.
- Preserve normalization history and reviewer rationale.

### Public Exploration

- Explain spending by department, service, account category, and capital project.
- Explain revenue by source, tax class, grant/transfer, fee, utility, financing, and other reviewed categories.
- Compare selected fiscal periods using absolute change and percentage change, with division-by-zero and missing-data states.
- Compare municipalities only on compatible fiscal periods, units, accounting scopes, and approved normalized categories.
- Provide source links and definitions beside every chart and table.
- Allow CSV and JSON downloads of the filtered, reviewed fact set with provenance identifiers.

## Source Variations And Edge Cases

- A document can contain current budget, prior budget, forecast, balance, and maturity years on the same page.
- A dash remains raw source evidence. In a reviewed currency column it normalizes to numeric zero and `reported_zero`; otherwise it remains unresolved until reviewed.
- Parentheses can indicate negative values or deductions, as on the capital partner-funding schedule at PDF page 111.
- A label can recur under different departments or statement sections and must not be globally merged by text alone.
- Multi-page schedules may omit repeated headers.
- Overview tables may duplicate detailed facts. Mark summary/detail relationships to prevent double counting.
- Department operating sections can use materially different summary/detail layouts across budget years. In 2025/2026, a mostly single-page departmental overview table is associated with one or more `Detailed Breakdown of Budget Item` pages that provide line items for the overview expense categories; totals are presented in the overview table. In 2024/2025, the operating department table pattern generally embeds totals in the department detail table and does not provide a separate overview table. Future extraction must detect which pattern is present, encode the source relationship, and normalize both patterns to the same department operating statement with line items before assigning reconciliation totals.
- Budget documents commonly repeat the same numbers across visualizations, overview pages, and backing tables to help human readers. Treat duplicate visualization or overview presentations as `duplicate_summary` unless they are approved summary/detail relationships such as department summaries versus line-item department or project tables. Do not normalize duplicate fact sets because they can corrupt totals and comparisons through double counting.
- Large-font headings, department names, project titles, and profile `Project:` fields are prone to line-wrapping, especially in narrow page columns. Extraction must reconstruct the complete string from adjacent wrapped lines before normalization, alias matching, statement naming, or project identity decisions.
- Overview chart pages can contain a visual chart followed by the backing data table. Ignore the chart graphic for normalization; public UI charts should be reproduced later from reviewed normalized facts.
- Capital profiles contain dates and narrative numbers that are not budget amounts.
- Municipality names, department structures, fiscal calendars, and accounting classifications can change over time.
- Restated prior-year figures must remain document-specific and must not overwrite the value reported in an earlier document.

## Acceptance Criteria

- All three Charlottetown PDFs have document and page inventories with input hashes.
- Every detected financial table has an extraction status and review disposition.
- Every published value has period, entity, statement scope, row semantics, unit, and source provenance.
- Published operating and capital totals reconcile to the source or carry a visible exception.
- Users can answer where money comes from and where it goes for 2026/2027 without double counting summaries and details.
- Users can compare all compatible reviewed values across the three Charlottetown documents.
- Unsupported cross-municipality or period comparisons return a reason rather than a misleading chart.
- Automated schema, parser, API, reconciliation, and browser tests pass.

## Open Decisions Before Multi-Municipality Release

- approved cross-municipality service and revenue taxonomy
- authoritative population, inflation, and assessment-denominator sources
- treatment of restatements in default comparisons
- public display policy for low-confidence but unreconciled source values
- accessibility and bilingual-content requirements beyond the repository baseline

## Sources

- [Municipal budgets](./README.md)
- [Database schema](./database-schema.md)
- [Charlottetown 2026/2027 first pass](../charlottetown/sources/budget-2026-2027-first-pass.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 10, 19, 30, 105, 111, 149, and 151
