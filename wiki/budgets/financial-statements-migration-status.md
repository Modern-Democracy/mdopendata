---
type: implementation
tags:
  - budget
  - financial-statements
  - migration
updated: 2026-07-15
---

This page records isolated implementation and verification of migrations 029 through 031 for Charlottetown financial statements.

# Financial Statements Migration Status

## Status

Gate 4 is complete, and the Gate 6 semantic-column foundation is implemented. Migrations 029 through 031 and their isolated regression files pass clean database builds from `template0`. The active `mdopendata` database was not changed and does not contain these migrations.

## Migration 029

`schema/sql/029_budget_financial_statement_context.sql` adds:

- document accounting context, assurance, authority, consolidation scope, and review state
- nine controlled statement classes and a nullable legacy-compatible statement reference
- reviewed, municipality-scoped reporting-entity relationships
- reviewed financial-observation relationships, including strict budget-equivalence compatibility
- five financial-statement review issue codes and twelve allowed decisions

The migration rejects self-links, cross-municipality links, incompatible source-document scopes, approved relationships without normalization decisions, and budget-equivalent links with mismatched entity, period, unit, statement class, flow semantics, or amount roles.

## Migration 030

`schema/sql/030_budget_financial_statement_publication.sql` adds reviewed line-category assignments and six publication views:

- `budget.v_published_financial_statement_observations`
- `budget.v_budget_actual_comparison`
- `budget.v_financial_position`
- `budget.v_cash_flow`
- `budget.v_pension_position`
- `budget.v_holistic_finance_coverage`

Existing budget-only snapshots remain valid. A financial-statement document cannot enter a published snapshot without an accounting-context row, approved review, and reviewed publication authority. Published financial-statement observations require a controlled statement class and approved review state. Budget category assignments are restricted to operations flow statements. Component and pension relationships remain visible with explicit non-additive scope warnings.

## Migration 031

`schema/sql/031_budget_financial_statement_semantic_columns.sql` separates reviewed statement columns from row-relative OCR groups. It adds:

- `budget.semantic_table_column` for reviewed label, period-value, context, and note-reference columns
- `budget.source_cell_semantic_assignment` for exact or manually transcribed cell fragments
- support for one merged raw cell to map to multiple semantic columns
- `budget.document_period.semantic_column_id` with exactly-one raw-or-semantic column enforcement
- same-table, same-document, period-role, review-decision, and source-substring controls

Existing raw source records remain immutable. Legacy budget document periods continue using `source_table_column_id`.

## Verification

| Control | Result |
| --- | --- |
| Isolated migration harness | Passed twice on unique `template0` databases; temporary databases remaining: 0. |
| Migration 029 regression | Relationship, municipality, decision, budget-equivalence, and legacy-null controls passed. |
| Migration 030 regression | Authority blocking, publication compatibility, category assignment, views, and legacy snapshot controls passed. |
| Migration 031 regression | Merged-cell fragments, semantic periods, legacy periods, source fidelity, cross-table, role, decision, and document controls passed. |
| Gate 2 profile regression | 6 tests passed. |
| Gate 3 schema-spike regression | 7 tests passed. |
| Active database | Unchanged at 2 snapshots, 12,637 observation memberships, and 2 published snapshots. |
| Active migration state | Migrations 029, 030, and 031 absent. |

No active-database backup was required because the harness created and dropped only isolated temporary databases. Applying these migrations to `mdopendata`, importing normalized observations, changing snapshot membership, or publishing financial statements requires separate authorization.

## Sources

- [Financial statements ingestion implementation plan](./financial-statements-ingestion-implementation-plan.md)
- [Financial statements representative schema spike](./financial-statements-schema-spike.md)
- `data/financial-statements/charlottetown/gate-4-migration-qa-report.json`
- `schema/sql/029_budget_financial_statement_context.sql`
- `schema/sql/030_budget_financial_statement_publication.sql`
- `schema/sql/031_budget_financial_statement_semantic_columns.sql`
- `schema/tests/029_budget_financial_statement_context_regression.sql`
- `schema/tests/030_budget_financial_statement_publication_regression.sql`
- `schema/tests/031_budget_financial_statement_semantic_columns_regression.sql`
- `scripts/test-budget-migration.py`
- [Gate 6 migration 031 QA report](../../data/financial-statements/charlottetown/gate-6-migration-031-qa-report.json)
