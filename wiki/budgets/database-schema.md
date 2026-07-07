---
type: implementation
tags:
  - budget
  - database
  - schema
updated: 2026-07-07
---

This page defines the proposed PostgreSQL `budget` schema for raw extraction, reviewed facts, provenance, and comparison.

# Municipal Budget Database Schema

## Design Rules

- Raw source records are immutable for a document hash.
- Normalized records reference raw evidence and can be superseded through review decisions.
- Values are long-form facts keyed by fiscal period and amount type.
- A reported value is never replaced by a later document's restatement.
- Summary and detail facts can coexist but carry aggregation roles that prevent double counting.
- Cross-municipality category mappings are versioned and review-approved.

## Source And Extraction Layer

| Table | Required columns and constraints |
| --- | --- |
| `budget.source_document` | `id`, `municipality_id`, `title`, `document_kind`, `source_uri`, `local_path`, `sha256` unique, `published_on`, `retrieved_at`, `page_count`, `status`. |
| `budget.source_page` | `id`, `document_id`, `pdf_page_number`, `printed_page_label`, `section_label`, `content_type`, `text_path`, `image_path`; unique `(document_id, pdf_page_number)`. |
| `budget.source_table` | `id`, `document_id`, `table_key`, `raw_title`, `table_type`, `page_start`, `page_end`, `continuation_group_key`, `bbox`, `extraction_status`, `review_status`; unique `(document_id, table_key)`. |
| `budget.source_table_row` | `id`, `source_table_id`, `row_key`, `row_index`, `raw_text`, `raw_label`, `indent_level`, `row_style`, `bbox`, `parser_confidence`; unique `(source_table_id, row_key)`. |
| `budget.source_table_cell` | `id`, `source_row_id`, `column_index`, `raw_header`, `raw_text`, `bbox`, `parsed_numeric`, `parsed_text`, `parse_status`, `parser_confidence`; unique `(source_row_id, column_index)`. |
| `budget.import_batch` | `id`, `document_id`, `source_sha256`, `extractor_version`, `started_at`, `completed_at`, `status`, `metrics_json`, `error_json`. |
| `budget.import_record_event` | `id`, `batch_id`, `record_type`, `natural_key`, `content_hash`, `event_type`, `review_reason`. |

Coordinates should use normalized page coordinates so the UI can highlight a source cell on any render resolution.

## Shared Dimensions

| Table | Required columns and constraints |
| --- | --- |
| `budget.municipality` | `id`, `slug` unique, `legal_name`, `province_code`, `country_code`, `boundary_feature_id` nullable, effective dates. |
| `budget.reporting_entity` | `id`, `municipality_id`, `parent_entity_id`, `slug`, `display_name`, `entity_type`, effective dates; unique by municipality, slug, and effective start. |
| `budget.organization_unit` | `id`, `reporting_entity_id`, `parent_id`, `unit_key`, `display_name`, `unit_type`, effective dates. |
| `budget.fiscal_period` | `id`, `municipality_id`, `label`, `start_date`, `end_date`, `period_kind`; unique by municipality, dates, and kind. |
| `budget.document_period` | `document_id`, `fiscal_period_id`, `period_role`, `raw_column_label`, `column_order`; unique by document and raw column label. |
| `budget.fund` | `id`, `reporting_entity_id`, `parent_id`, `fund_key`, `display_name`, `fund_type`, effective dates. |
| `budget.measure_unit` | `id`, `code` unique, `display_name`, `unit_kind`, `currency_code`, `scale`, `denominator_text`. |
| `budget.amount_type` | `id`, `code` unique, `display_name`; examples include `budget`, `forecast`, `actual`, `balance`, `principal`, `interest`, `gross`, `funding_deduction`, and `net`. |
| `budget.normalized_category` | `id`, `taxonomy_version`, `category_key`, `parent_id`, `domain`, `display_name`; unique by version and key. |

`document_period` is required because the 2026/2027 document reports prior budgets and forecasts. A prior-period value in this document is a separate reported observation from the value in the 2025/2026 document.

## Statement And Fact Core

| Table | Required columns and constraints |
| --- | --- |
| `budget.statement` | `id`, `document_id`, `reporting_entity_id`, `fund_id`, `statement_key`, `statement_kind`, `title`, `scope_note`, `source_table_id`; unique `(document_id, statement_key)`. |
| `budget.line_item` | `id`, `statement_id`, `parent_id`, `line_key`, `row_order`, `raw_label`, `display_label`, `line_kind`, `aggregation_role`, `organization_unit_id`, `normalized_category_id`, `source_row_id`; unique `(statement_id, line_key)`. |
| `budget.fact` | `id`, `line_item_id`, `document_period_id`, `amount_type_id`, `measure_unit_id`, `value_numeric`, `value_text`, `value_state`, `source_cell_id`, `is_reported`, `derivation_id`, `review_status`; one numeric or text value, never both. |
| `budget.fact_derivation` | `id`, `formula_code`, `formula_text`, `input_fact_ids`, `calculated_at`, `software_version`. |
| `budget.statement_relationship` | `parent_statement_id`, `child_statement_id`, `relationship_type`; supports summary/detail and consolidated/component relationships. |

`aggregation_role` values are `detail`, `subtotal`, `total`, `memo`, and `non_additive`. Public aggregate queries include `detail` by default and use source totals only for reconciliation.

`value_state` distinguishes `reported`, `reported_zero`, `dash_unresolved`, `not_applicable`, `missing`, and `suppressed`. This prevents silent conversion of dashes to zero.

## Capital, Tax, Rate, Debt, And Reserve Extensions

| Table | Purpose and key fields |
| --- | --- |
| `budget.capital_project` | Stable project identity: municipality, reporting entity, project key, name, description, status, location text, organization unit, effective dates. |
| `budget.capital_project_alias` | Document-specific raw project label mapped to a project after review. |
| `budget.capital_project_fact` | Links a `fact` to a project and optional funding-source category; keeps gross, deduction, and net facts distinct. |
| `budget.capital_project_profile` | Structured narrative fields, source row/page, raw value, normalized value, and review status. |
| `budget.tax_class` | Municipality, parent class, residency, property/use class, special district, raw label, normalized key, effective dates. |
| `budget.rate_fact` | Links a `fact` to tax class, customer class, geography, assessment base, or denominator definition. |
| `budget.debt_instrument` | Reporting entity, lender, raw and normalized label, instrument type, issue date, maturity date, effective dates. |
| `budget.debt_fact` | Links a `fact` to an instrument and debt measure such as opening balance, principal, or interest. |
| `budget.reserve_fund` | Reporting entity, reserve key, name, reserve type, effective dates. |
| `budget.reserve_fact` | Links a `fact` to a reserve and movement type such as contribution, withdrawal, allocation, or balance. |

## Review And Publication

| Table | Purpose and key fields |
| --- | --- |
| `budget.normalization_decision` | Source entity type/key, target entity type/id, decision, rationale, reviewer, decided timestamp, taxonomy version. |
| `budget.reconciliation_result` | Statement, fiscal period, check type, calculated value, reported value, difference, tolerance, pass/fail, input fact ids. |
| `budget.review_issue` | Source or normalized record, issue code, severity, status, notes, assignee, resolution. |
| `budget.publication_snapshot` | Municipality, release label, taxonomy version, created timestamp, source document ids, status. |
| `budget.publication_fact` | Snapshot and reviewed fact ids; freezes the public release without copying fact values. |

## Required Views

| View | Purpose |
| --- | --- |
| `budget.v_published_facts` | Reviewed facts with municipality, entity, period, statement, hierarchy, category, unit, and provenance. |
| `budget.v_operating_flow` | Non-duplicated operating revenue and expense details. |
| `budget.v_capital_investment` | Gross, external funding, financing, and net capital facts by program/project. |
| `budget.v_revenue_sources` | Reviewed operating revenue, taxes, rates, transfers, fees, and financing categories. |
| `budget.v_period_comparison` | Compatible published facts joined by stable identity and taxonomy version. |
| `budget.v_extraction_coverage` | Source tables/rows/cells and published/review/unresolved counts. |

## Database Constraints And Indexes

- Use `numeric(20,4)` for general numeric facts and explicit unit scale; use `date` for period boundaries.
- Check that each fact has exactly one of `value_numeric` or `value_text`, except explicit missing states.
- Check that reported facts have `source_cell_id` or a documented row-level exception.
- Use foreign keys throughout and prevent cycles in entity, organization, category, and line-item hierarchies during import.
- Index published facts by municipality, fiscal period, statement kind, normalized category, organization unit, and project.
- Add trigram indexes only to review/search labels, not as identity logic.
- Keep source hashes, natural keys, and content hashes for idempotent re-imports.

## Compatibility Gate

This is a proposed schema. SQL migrations and importer changes require approval after a representative-table spike proves the model against operating detail, multi-period facility statements, capital deductions, tax calculations, and debt schedules.

## Sources

- [Requirements](./requirements.md)
- [Initial municipal budget data model](../implementation/municipal-budget-data-model.md)
- [Charlottetown 2026/2027 first pass](../charlottetown/sources/budget-2026-2027-first-pass.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 30, 105, 111, 149, and 151

