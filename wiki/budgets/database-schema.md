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
| `budget.source_page` | `id`, `document_id`, `pdf_page_number`, `printed_page_label`, `section_label`, `content_type`, `text_path`, `image_path`, `extraction_method`, `extractor_version`, `extraction_confidence`, `review_status`; unique `(document_id, pdf_page_number)`. |
| `budget.source_table` | `id`, `document_id`, `table_key`, `raw_title`, `table_type`, `continuation_group_key`, `extraction_status`, `review_status`; unique `(document_id, table_key)`. |
| `budget.source_table_page` | `source_table_id`, `source_page_id`, `page_order`, `page_role`, `bbox`, `extraction_method_override`; primary key `(source_table_id, source_page_id)`, unique `(source_table_id, page_order)`. |
| `budget.source_table_column` | `id`, `source_table_id`, `column_key`, `column_index`, `raw_header`, `column_role`, `bbox`, `review_status`; unique `(source_table_id, column_key)` and `(source_table_id, column_index)`. |
| `budget.source_table_row` | `id`, `source_table_id`, `row_key`, `row_index`, `raw_text`, `raw_label`, `indent_level`, `row_style`, `bbox`, `parser_confidence`; unique `(source_table_id, row_key)`. |
| `budget.source_table_cell` | `id`, `source_row_id`, `source_table_column_id`, `raw_text`, `bbox`, `parsed_numeric`, `parsed_text`, `parse_status`, `parser_confidence`; unique `(source_row_id, source_table_column_id)`. |
| `budget.import_batch` | `id`, `document_id`, `source_sha256`, `extractor_version`, `started_at`, `completed_at`, `status`, `metrics_json`, `error_json`. |
| `budget.import_record_event` | `id`, `batch_id`, `record_type`, `natural_key`, `content_hash`, `event_type`, `review_reason`. |

Coordinates should use normalized page coordinates so the UI can highlight a source cell on any render resolution. `source_table_page` is authoritative for table membership; `page_start` and `page_end` may be exposed as derived convenience fields but are not stored as the membership model.

`extraction_method` values initially include `embedded_text`, `ocr`, and `manual_transcription`. Row and cell parser confidence does not replace page-level extraction provenance.

## Shared Dimensions

| Table | Required columns and constraints |
| --- | --- |
| `budget.municipality` | `id`, `slug` unique, `legal_name`, `province_code`, `country_code`, `boundary_feature_id` nullable, effective dates. |
| `budget.reporting_entity` | `id`, `municipality_id`, `parent_entity_id`, `slug`, `display_name`, `entity_type`, effective dates; unique by municipality, slug, and effective start. |
| `budget.organization_unit` | `id`, `reporting_entity_id`, `parent_id`, `unit_key`, `display_name`, `unit_type`, effective dates. |
| `budget.fiscal_period` | `id`, `municipality_id`, `label`, `start_date`, `end_date`, `period_kind`; unique by municipality, dates, and kind. |
| `budget.document_period` | `id`, `document_id`, `fiscal_period_id`, `source_table_column_id`, `period_role`, `raw_column_label`, `column_order`, `review_status`; unique `(document_id, source_table_column_id, period_role)`. |
| `budget.fund` | `id`, `reporting_entity_id`, `parent_id`, `fund_key`, `display_name`, `fund_type`, effective dates. |
| `budget.measure_unit` | `id`, `code` unique, `display_name`, `unit_kind`, `currency_code`, `scale`, `denominator_text`. |
| `budget.amount_type` | `id`, `code` unique, `display_name`; examples include `budget`, `forecast`, `actual`, `balance`, `principal`, `interest`, `gross`, `funding_deduction`, and `net`. |
| `budget.normalized_category` | `id`, `taxonomy_version`, `category_key`, `parent_id`, `domain`, `display_name`; unique by version and key. |

`document_period` is required because the 2026/2027 document reports prior budgets and forecasts. A prior-period value in this document is a separate reported observation from the value in the 2025/2026 document. The source-column link preserves raw label variants and permits repeated labels in separate tables without treating raw text as identity.

## Statement And Fact Core

| Table | Required columns and constraints |
| --- | --- |
| `budget.statement` | `id`, `document_id`, `reporting_entity_id`, `fund_id`, `statement_key`, `statement_kind`, `title`, `scope_note`, `source_table_id`; unique `(document_id, statement_key)`. |
| `budget.line_item` | `id`, `statement_id`, `parent_id`, `line_key`, `row_order`, `raw_label`, `display_label`, `line_kind`, `aggregation_role`, `organization_unit_id`, `normalized_category_id`, `source_row_id`; unique `(statement_id, line_key)`. |
| `budget.fact` | `id`, `line_item_id`, `document_period_id`, `amount_type_id`, `measure_unit_id`, `value_numeric`, `value_text`, `value_state`, `is_reported`, `derivation_id`, `review_status`; one numeric or text value, never both. |
| `budget.fact_source` | `fact_id`, `source_cell_id`, `source_role`, `source_order`; primary key `(fact_id, source_cell_id, source_role)`. |
| `budget.fact_derivation` | `id`, `formula_code`, `formula_text`, `input_fact_ids`, `calculated_at`, `software_version`. |
| `budget.statement_relationship` | `parent_statement_id`, `child_statement_id`, `relationship_type`; supports summary/detail and consolidated/component relationships. |

`aggregation_role` values are `detail`, `subtotal`, `total`, `memo`, and `non_additive`. Public aggregate queries include `detail` by default and use source totals only for reconciliation.

`value_state` distinguishes `reported`, `reported_zero`, `dash_unresolved`, `not_applicable`, `missing`, and `suppressed`. This prevents silent conversion of dashes to zero.

`fact_source` permits one source expression to support several facts, such as assessment base, rate, and reported tax revenue, and permits one fact to cite several cells. `source_role` values initially include `reported_value`, `assessment_operand`, `rate_operand`, `denominator`, `label_context`, and `derivation_input`. A reported fact must have at least one `reported_value` source unless it is an approved row-level exception.

## Capital, Tax, Rate, Debt, And Reserve Extensions

| Table | Purpose and key fields |
| --- | --- |
| `budget.capital_project` | Stable municipality-scoped project identity with source-supported lifecycle status; it has no budget-year ownership. |
| `budget.capital_project_reference` | Source-document-owned project reference with raw label, source table/row, adoption state, identity evidence, and review state. |
| `budget.capital_project_alias` | Legacy label convenience record derived only from an approved project reference. |
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
| `budget.review_issue` | `id`, `review_key` unique, `reconciliation_result_id` nullable, `subject_record_type`, `subject_natural_key`, `issue_code`, `severity`, `status`, `title`, `description`, `publication_effect`, `required_resolution`, `prohibited_action`, `assignee`, `created_at`, `resolved_at`. |
| `budget.review_issue_evidence` | `id`, `review_issue_id`, `source_cell_id` nullable, `reconciliation_result_id` nullable, `evidence_role`, `evidence_order`, `notes`; require at least one evidence reference. |
| `budget.review_decision` | `id`, `review_issue_id`, `decision_code`, `rationale`, `reviewer`, `decided_at`, `authoritative_source_document_id` nullable, `supersedes_decision_id` nullable; append-only. |
| `budget.publication_snapshot` | Municipality, release label, taxonomy version, created timestamp, source document ids, status. |
| `budget.publication_fact` | Snapshot and reviewed fact ids; freezes the public release without copying fact values. |

Review issue statuses are `open`, `in_review`, `resolved`, and `superseded`. Severity values are `low`, `medium`, `high`, and `critical`. Closing an issue requires a decision code allowed by its issue type; free-text notes alone do not resolve an issue.

Initial reconciliation issue codes are `reported_calculation_variance`, `reported_dash_with_calculated_balance`, and `reported_dash_with_nonzero_calculated_balance`. An unresolved issue can permit reported facts while blocking or warning on derived metrics through `publication_effect`.

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
- Enforce through import validation or a deferred constraint trigger that reported facts have a `fact_source` row with role `reported_value`, unless an approved row-level exception exists.
- Require each `document_period.source_table_column_id` to belong to a table in the same document.
- Require each `source_table_cell.source_table_column_id` to belong to the cell row's source table.
- Use foreign keys throughout and prevent cycles in entity, organization, category, and line-item hierarchies during import.
- Index published facts by municipality, fiscal period, statement kind, normalized category, organization unit, and project.
- Add trigram indexes only to review/search labels, not as identity logic.
- Keep source hashes, natural keys, and content hashes for idempotent re-imports.
- Keep review decisions append-only; corrections create a superseding decision and never rewrite prior reviewer rationale.

## Compatibility Gate

This remains a proposed schema. The representative-table spike resolved the structural gaps for document-period identity, extraction provenance, multi-page membership, raw period labels, and multi-fact source expressions. SQL migrations remain gated on materialized representative rows/cells and the required reconciliation checks.

## Sources

- [Requirements](./requirements.md)
- [Initial municipal budget data model](../implementation/municipal-budget-data-model.md)
- [Charlottetown 2026/2027 first pass](../charlottetown/sources/budget-2026-2027-first-pass.md)
- [Representative-table schema spike](./representative-table-schema-spike.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 30, 105, 111, 149, and 151
