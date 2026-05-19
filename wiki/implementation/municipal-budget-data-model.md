---
type: implementation
tags:
  - budget
  - schema
  - ingestion
updated: 2026-05-19
---

This page sketches a scalable municipal budget data model based on the first-pass Charlottetown 2026/2027 budget manifest.

# Municipal Budget Data Model

## Design Goals

The budget schema should store multi-year municipal budget facts without binding the repository to one municipality, one PDF layout, or one fiscal-year column pattern.

The model should preserve raw source labels and page/table provenance, while exposing normalized entities for cross-year comparison by municipality, fund, department, service area, budget item, capital project, rate, debt instrument, and funding source.

## Source And Provenance Tables

| Table | Purpose |
| --- | --- |
| `budget.source_document` | One source budget PDF or related source file. |
| `budget.source_page` | Page inventory, page class, section, subsection, and extraction priority. |
| `budget.source_table` | One detected table/profile candidate with page range, raw title, table type, and review status. |
| `budget.source_table_row` | Raw extracted row text, row order, indentation level, parsed cells, and confidence before normalization. |
| `budget.source_value` | Raw numeric/text values with source row, raw cell text, parsed value, unit, currency, and parser confidence. |

## Core Dimension Tables

| Table | Purpose |
| --- | --- |
| `budget.municipality` | Municipality or municipal corporation, such as City of Charlottetown. |
| `budget.organization_unit` | Departments, agencies, utilities, facilities, committees, and reporting groups. Supports parent-child hierarchy. |
| `budget.fiscal_period` | Fiscal year or fiscal period with start/end dates and display label. |
| `budget.budget_document_period` | Links a document to the fiscal periods it reports, including prior budget and forecast periods. |
| `budget.fund` | Operating fund, capital fund, reserve fund, utility fund, or special-purpose fund. |
| `budget.service_area` | Service/program area beneath a department, such as Parks, Simmons Arena, or Fiscal Services. |
| `budget.account_category` | Revenue, expense, transfer, debt service, funding source, tax levy, rate, asset purchase, or reserve movement. |
| `budget.budget_item` | Reusable line item identity with raw label history and optional parent item hierarchy. |
| `budget.measure_unit` | Dollars, percent, rate per assessed value, rate per day, rate per cubic metre, count, or other units. |

## Operating Budget Fact Tables

| Table | Purpose |
| --- | --- |
| `budget.operating_statement` | Header for an operating budget statement by municipality, entity, fiscal period, and document. |
| `budget.operating_line_item` | Normalized operating revenue/expense row with hierarchy, raw label, department, service area, fund, and account category. |
| `budget.operating_amount` | One amount per line item, fiscal period, and amount type: budget, forecast, actual, prior-year surplus, deficit, net expenditure, or total. |

## Capital Budget Tables

| Table | Purpose |
| --- | --- |
| `budget.capital_program` | Capital budget grouping by department, portfolio, utility, facility, or category. |
| `budget.capital_project` | Named capital project with municipality, department, project title, description, status, and strategic alignment. |
| `budget.capital_project_amount` | Project or category amounts by fiscal period and amount type: gross budget, partner funding, net budget, contribution, or carryforward. |
| `budget.capital_project_funding` | Funding source allocations, including partner funding, grants, reserves, debt, utility revenue, or external contribution. |
| `budget.capital_project_profile` | Narrative profile fields extracted from project-profile pages, linked to the project and source page. |

## Rates, Taxes, And Assessments

| Table | Purpose |
| --- | --- |
| `budget.tax_class` | Property tax class, ownership/residency class, BIA class, hotel/motel, apartment, mobile-home class, or commercial class. |
| `budget.tax_rate` | Municipal tax rate by fiscal period, tax class, geography/special district, and rate unit. |
| `budget.assessment_base` | Assessment amount by tax class and fiscal period. |
| `budget.tax_revenue_estimate` | Calculated or reported revenue by tax class, assessment base, rate, and fiscal period. |
| `budget.utility_rate` | Water/sewer base, consumption, metered, and unmetered rates by fiscal period and customer class. |
| `budget.fee_or_charge` | Other service fees, permits, user fees, facility charges, or billed service charges. |

## Debt And Reserve Tables

| Table | Purpose |
| --- | --- |
| `budget.debt_instrument` | Loan, swap, lease, or financing instrument with lender, label, maturity, fund/entity, and raw source label. |
| `budget.debt_service_amount` | Balance, principal, interest, and total debt service by fiscal period and instrument. |
| `budget.reserve_fund` | Named reserve or reserve-like funding source. |
| `budget.reserve_transaction` | Contributions, withdrawals, allocations, balances, and links to operating or capital records when available. |

## Review And Normalization Tables

| Table | Purpose |
| --- | --- |
| `budget.normalization_decision` | Reviewer-approved mapping from raw labels to normalized units, items, funds, tax classes, projects, or debt instruments. |
| `budget.import_batch` | One ingestion/import run with source document, script version, input hash, and status. |
| `budget.import_record_event` | Added, changed, unchanged, removed, or review-needed event for each normalized record. |

## Implementation Notes

Use raw-first extraction before normalized imports. `source_table_row` and `source_value` should be generated before deciding final mappings for `budget_item`, `capital_project`, `tax_class`, or `debt_instrument`.

Do not store fiscal years as fixed columns. Amounts should be long-form facts keyed by `fiscal_period_id` and `amount_type`.

Keep source labels exact. Normalized display names can be added after review, but raw row labels and raw cell values must remain available for audit.

Use hierarchy fields for municipal reporting shape. Budget pages contain nested departments, services, categories, detailed item labels, totals, and continuation pages; the model should support parent-child rows rather than flattening all rows.

## Sources

- [Charlottetown 2026/2027 budget first pass](../charlottetown/sources/budget-2026-2027-first-pass.md)
- `data/budget/charlottetown/2026-2027/table_manifest.json`
