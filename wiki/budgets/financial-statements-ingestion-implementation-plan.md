---
type: project
tags:
  - budget
  - financial-statements
  - ingestion
  - implementation-plan
updated: 2026-07-15
---

This page defines the gated repository implementation plan for ingesting Charlottetown financial statements and connecting reviewed actuals, balances, and cash flows to the existing municipal budget model.

# Charlottetown Financial Statements Ingestion Implementation Plan

## Objective

Ingest the eight scanned PDFs under `docs/charlottetown/financial-statements/` as four two-edition reporting-entity series, preserve every reported comparative and budget column with source-cell provenance, and publish scope-safe links between financial-plan observations and financial-statement observations.

The implementation extends the applied `budget` schema. It does not create an independent financial-statements schema, replace audited values with derived values, merge draft and audited comparatives, or add pension-plan assets to City consolidated totals.

## Source Boundary

| Series | Earlier edition | Later edition | Reporting year-end |
| --- | --- | --- | --- |
| City consolidated | `Draft 2024 CoC Consolidated Financial Statements (1).pdf` | `City of Charlottetown Consolidated Financial Statements - March 31, 2025.pdf` | March 31 |
| Water and Sewer Corporation | `Draft 2024 W&S.pdf` | `Charlottetown Water and Sewer Corporation Financial Statements - March 31, 2025.pdf` | March 31 |
| City superannuation plan | `2024 COC SA Plan.pdf` | `City of Charlottetown Supperannuation Plan Financial Statements - December 31, 2024.pdf` | December 31 |
| Water and Sewer superannuation plan | `2024 W&S SA Plan.pdf` | `Charlottetown Water and Sewer Superannuation Plan Financial Statements - December 21, 2024.pdf` | December 31 per the statement page; filename discrepancy requires review |

All eight PDFs are image-only scans and total 188 PDF pages. Every visible source column is in scope. The March 31 statements contain current budget, current actual, and prior actual columns; the pension statements contain current and prior actual columns.

## Gate 1 Status

Gate 1 completed on 2026-07-14 with eight SHA-256 hashes, 188 registered pages, source-page titles and reporting dates, reporting-entity scopes, accounting frameworks, and independent-auditor evidence. All eight documents contain unmodified audit opinions and are approved for Gate 2 profiling.

Six filename conflicts are resolved for ingestion identity: two `Draft` labels do not override audited content, two `2024` pension filenames contain December 31, 2023 statements, `Supperannuation` does not create a separate entity, and the Water and Sewer pension filename date of December 21 does not override the repeated source date of December 31. Municipal publication, adoption, or final-release status remains unknown for every document, so no document is publication-approved.

- [Source document registry](../../data/financial-statements/charlottetown/source-document-registry.json)
- [Source authority review](../../data/financial-statements/charlottetown/source-authority-review.json)

## Gate 2 Status

Gate 2 completed on 2026-07-14. The deterministic profiler validated all eight Gate 1 hashes, rendered and OCRed all 188 pages, assigned every page a disposition, and classified 139 financial-table candidates with zero unclassified financial tables. The candidates comprise 28 primary-statement pages, 14 schedule pages, and 97 note-disclosure table pages.

Six sideways City schedule pages and two sideways Water and Sewer schedule pages were recovered through recorded 270-degree OCR rotation. Visual review resolved the two dense City page 28 controls as Note 15 budget-reconciliation tables with `Per Budget Document`, `Net Adjustments`, and `Consolidated Budget` columns. Both pages are classified as `budget_reconciliation_note`; their source assurance limitation and sign/dash controls must be preserved in Gate 3. Gate 2 artifacts contain no normalized rows, observations, database writes, or publication changes.

- [Gate 2 profile summary](../../data/financial-statements/charlottetown/gate-2-profile-summary.json)
- [Gate 2 QA report](../../data/financial-statements/charlottetown/gate-2-qa-report.json)
- [Gate 2 low-confidence page review](../../data/financial-statements/charlottetown/gate-2-low-confidence-page-review.json)
- `scripts/profile-charlottetown-financial-statements.py`
- `scripts/test-financial-statements-profile.py`

## Gate 3 Status

Gate 3 completed on 2026-07-14. The seven approved controls were materialized across seven unique source pages as 247 raw OCR rows and 612 raw OCR cells with normalized coordinates. All controls fit the existing budget model plus the four migration 029 objects already planned: accounting context, controlled statement class, reviewed reporting-entity relationships, and reviewed financial-observation relationships.

The spike found zero unsupported patterns and zero unplanned schema gaps. Sixteen rows and 42 cells remain low-confidence raw extraction records for Gate 5 review; visual source controls establish schema fit without approving those records for normalized import. No migration, database write, normalized observation, snapshot, or publication change occurred.

- [Financial statements representative schema spike](./financial-statements-schema-spike.md)
- [Schema-spike summary](../../data/financial-statements/charlottetown/schema-spike/spike-summary.json)
- [Schema-fit report](../../data/financial-statements/charlottetown/schema-spike/schema-fit-report.json)
- [Schema-spike QA report](../../data/financial-statements/charlottetown/schema-spike/schema-spike-qa-report.json)
- `scripts/build-charlottetown-financial-statements-schema-spike.py`
- `scripts/test-financial-statements-schema-spike.py`

## Gate 4 Status

Gate 4 completed on 2026-07-14. Migration 029 implements accounting context, nine controlled statement classes, reviewed reporting-entity relationships, reviewed financial-observation relationships, and financial-statement review decisions. Migration 030 implements reviewed category assignments, publication compatibility gates, and six scope-safe finance views.

Both migrations and their isolated regression files passed two clean database builds from `template0`. Existing budget-only publication snapshots remain compatible, and incompatible or unreviewed financial-statement publication paths fail closed. The active `mdopendata` database remains unchanged at 2 snapshots, 12,637 observation memberships, and 2 published snapshots; migrations 029 and 030 are not applied there.

- [Financial statements migration status](./financial-statements-migration-status.md)
- [Gate 4 migration QA report](../../data/financial-statements/charlottetown/gate-4-migration-qa-report.json)
- `schema/sql/029_budget_financial_statement_context.sql`
- `schema/sql/030_budget_financial_statement_publication.sql`
- `schema/tests/029_budget_financial_statement_context_regression.sql`
- `schema/tests/030_budget_financial_statement_publication_regression.sql`
- `scripts/test-budget-migration.py`

## Gate 5 Status

Gate 5 completed formally on 2026-07-15. All 139 Gate 2 table pages were extracted across the eight documents as 4,852 raw rows and 10,085 raw cells with stable keys, normalized coordinates, OCR confidence, exact raw text, and the eight approved page rotations. The controlled raw import added 8 documents, 188 pages, 139 tables, 139 table-page links, 551 columns, 4,852 rows, 10,085 cells, and 8 import batches.

Nine base extraction regressions and six raw-database regressions pass. The imported scoped counts exactly equal the controlled artifacts, and the committed idempotence rerun inserted zero records. Active financial observations remain 6,381, publication memberships remain 12,637, and both published snapshots remain unchanged. Batch 01 through Batch 04 controlled-derived treatments remain separate from the raw import; no source-column role, normalized observation, snapshot membership, or publication decision was added.

- [Financial statements raw extraction status](./financial-statements-raw-extraction-status.md)
- [Financial statements review batch 03](./financial-statements-review-batch-03.md)
- [Financial statements review batch 04](./financial-statements-review-batch-04.md)
- [Gate 5 raw extraction summary](../../data/financial-statements/charlottetown/gate-5-raw-extraction-summary.json)
- [Gate 5 review summary](../../data/financial-statements/charlottetown/gate-5-review-summary.json)
- [Gate 5 QA report](../../data/financial-statements/charlottetown/gate-5-qa-report.json)
- [Gate 5 raw database import result](../../data/financial-statements/charlottetown/gate-5-raw-database-import-result.json)
- [Gate 5 idempotence result](../../data/financial-statements/charlottetown/gate-5-raw-database-idempotence-result.json)
- `scripts/import-charlottetown-financial-statements-raw.py`
- `scripts/test-financial-statements-raw-import.py`
- `scripts/extract-charlottetown-financial-statements-raw.py`
- `scripts/build-charlottetown-financial-statements-review.py`
- `scripts/test-financial-statements-extraction.py`

## Gate 6 Status

Gate 6 began on 2026-07-15 with a source-column readiness audit. Of 551 row-relative OCR group columns, 345 mix value cells with text or year cells and 258 span more than 25 percent of page width. These raw identities remain valid provenance but cannot safely carry stable period-column semantics.

Migration 031 is implemented and isolated-tested. It adds reviewed semantic table columns, supports several exact or manually transcribed fragments from one merged raw cell, and permits document periods to reference either one legacy raw column or one reviewed semantic period column. The active database remains unchanged. Exact source-page semantic-column and fragment proposals are the next controlled Gate 6 artifact; hierarchy, signs, value states, comparatives, budget equivalence, and taxonomy remain unapproved.

- [Gate 6 migration 031 QA report](../../data/financial-statements/charlottetown/gate-6-migration-031-qa-report.json)
- `schema/sql/031_budget_financial_statement_semantic_columns.sql`
- `schema/tests/031_budget_financial_statement_semantic_columns_regression.sql`

## Required Semantics

- Register every PDF as a distinct `budget.source_document` keyed by SHA-256.
- Preserve source document status separately as `draft`, `audited`, or `unknown`; do not infer authority from filename alone.
- Preserve repeated comparative values as separate document-owned observations.
- Record reviewed relationships between draft values and later audited comparatives without overwriting either value.
- Use exact fiscal dates. March 31 municipal and December 31 pension periods must not be joined by year label alone.
- Treat the City as the consolidated default scope, Water and Sewer as a component drill-down, and each pension plan as a related but non-additive reporting entity.
- Use `amount_type=budget` for source budget columns and `amount_type=actual` for source actual columns. Statement kind and line semantics describe whether an actual is a flow, position, balance, or movement.
- Apply budget normalized categories only to reviewed compatible operating or capital flows. Financial-position, cash-flow, and pension taxonomies remain separate domains.

## Stable Identity Candidate

Use the gated document stem `ctown_fs_<entity>_<reporting_date>_<authority>`, with source objects extending the stem as `_pNNN`, `_tNN`, `_rNNN`, and `_cNN`. Examples include `ctown_fs_city_2025_03_31_audited_p007` and `ctown_fs_city_sa_2024_12_31_audited_p006`.

The identity contract is approved only after the source-authority review confirms every document date and authority state. IDs must not depend on database insertion order, OCR output order, or filename spelling.

## Migration Plan

### Migration 029: Accounting Context And Relationships

Create `schema/sql/029_budget_financial_statement_context.sql` with:

| Change | Purpose |
| --- | --- |
| `budget.document_accounting_context` | One-to-one document metadata for reporting framework, accounting basis, reporting date, assurance status, audit opinion, consolidation scope, authority rank, and review status. |
| `budget.reporting_entity_relationship` | Effective, source-reviewed relationships such as `consolidated_component` and `related_pension_plan`; do not overload `parent_entity_id`. |
| `budget.statement_class` | Controlled statement classes for financial position, operations, changes in net debt, cash flow, changes in net assets, pension obligations, tangible capital assets, segmented disclosure, and note schedules. |
| `budget.statement.statement_class_id` | Nullable during migration, required for newly published financial-statement records. Existing budget statements retain their current `statement_kind`. |
| `budget.financial_observation_relationship` | Reviewed `comparative_of`, `restates`, `supersedes`, and `budget_equivalent` links between observations. |
| Review issue codes | Add source-authority conflict, filename/reporting-date conflict, comparative variance, accounting-scope mismatch, and unsupported statement-pattern codes with controlled resolution choices. |

Constraints must prevent self-links, cross-municipality entity relationships, duplicate active relationships, approved relationship records without a normalization decision, and `budget_equivalent` links whose periods, entities, units, or flow semantics are incompatible.

### Migration 030: Publication And Holistic Views

Create `schema/sql/030_budget_financial_statement_publication.sql` with:

- `budget.financial_statement_line_category_assignment`, versioned and review-approved, for statement-specific taxonomy domains.
- Publication-snapshot compatibility checks for financial-statement documents and observations.
- `budget.v_published_financial_statement_observations` with document authority, accounting context, entity relationship, statement class, period, hierarchy, taxonomy, and provenance.
- `budget.v_budget_actual_comparison` restricted to reviewed `budget_equivalent` links.
- `budget.v_financial_position`, `budget.v_cash_flow`, and `budget.v_pension_position` with non-additive scope controls.
- `budget.v_holistic_finance_coverage` with page, table, row, cell, mapped, published, blocked, and unresolved counts.

Migration 030 must not change membership or semantics of the current published budget snapshot. Financial statements first enter a new draft snapshot.

## Script Plan

All Python commands run through `scripts/python.ps1`.

| Script | Responsibility |
| --- | --- |
| `scripts/profile-charlottetown-financial-statements.py` | Hash all eight PDFs, record page counts, render/OCR pages, classify statement candidates, and emit the source inventory without normalized semantics. |
| `scripts/build-charlottetown-financial-statements-schema-spike.py` | Materialize representative raw rows/cells and test the migration design against every source family. |
| `scripts/extract-charlottetown-financial-statements-raw.py` | Generate deterministic page, table, column, row, and cell artifacts with normalized coordinates and OCR confidence. |
| `scripts/build-charlottetown-financial-statements-review.py` | Generate exact source-authority, period, statement-class, hierarchy, entity-scope, dash/sign, and duplicate-comparative review registers. |
| `scripts/build-charlottetown-financial-statements-normalized-manifest.py` | Build document-owned statements, line items, observations, source links, and approved relationships from reviewed mapping packages. |
| `scripts/build-charlottetown-financial-statements-reconciliation.py` | Build statement, schedule, roll-forward, comparative, and budget-to-actual reconciliation catalogues. |
| `scripts/plan-charlottetown-financial-statements-import.py` | Validate manifest hashes, expected counts, relationship compatibility, and database coexistence with zero writes. |
| `scripts/import-charlottetown-financial-statements.py` | Perform transactional, manifest-driven raw and normalized import with idempotence and content-conflict failure. |
| `scripts/validate-charlottetown-financial-statements-provenance.py` | Compare every normalized observation and relationship to its raw source evidence and document hash. |
| `scripts/verify-charlottetown-financial-statements-qa.py` | Run family-stratified source fidelity, reconciliation, double-counting, and publication-readiness checks. |
| `scripts/plan-charlottetown-holistic-finance-snapshot.py` | Produce a deterministic proposed snapshot membership report with zero writes. |
| `scripts/create-charlottetown-holistic-finance-snapshot.py` | Create the reviewed draft snapshot only after the publication gate is approved. |

Shared code may be extracted from existing budget scripts only when equivalent behavior is demonstrated across the full source family. Document-specific page ranges, mappings, authority decisions, and exceptions remain data artifacts rather than branches in shared code.

## Artifact Plan

Use `data/financial-statements/charlottetown/` as the generated-data root.

```text
data/financial-statements/charlottetown/
  source-document-registry.json
  source-authority-review.json
  reporting-entity-relationship-review.json
  comparative-relationship-review.json
  budget-equivalence-review.json
  taxonomy-review.json
  <document-key>/
    source_profile.json
    page_inventory.json
    table_manifest.json
    profile-raw-pages/
    profile-ocr-pages/
    rendered-pages/
    raw-tables/source_table_rows.json
    raw-tables/source_table_cells.json
    mapping-review.json
    normalized-import-manifest.json
    normalized-import-manifest-report.json
    reconciliation-catalogue.json
    import-dry-run-plan.json
    import-result.json
    import-idempotence-result.json
    provenance-report.json
    qa-report.json
  publication/
    holistic-finance-snapshot-plan.json
    holistic-finance-coverage.json
```

Rendered pages are generated review artifacts and must follow repository packing rules before they are committed. Source PDFs remain authoritative and immutable.

## Representative Schema Spike

The spike must include these positive controls and adjacent negative controls:

| Pattern | Representative source | Required proof |
| --- | --- | --- |
| Consolidated financial position | 2025 City PDF page 6, visible page 4 | Assets, liabilities, net debt, non-financial assets, and accumulated surplus retain hierarchy and two actual columns. |
| Budget-to-actual operations | 2025 City PDF page 7, visible page 5 | Budget 2025, actual 2025, and actual 2024 remain distinct document periods and amount types. |
| Cash flow | 2025 City PDF page 9, visible page 7 | Operating, capital, investing, and financing movements remain non-additive across sections. |
| Component operations | 2025 Water and Sewer PDF page 7, visible page 5 | The separate entity links to, but is not added to, City consolidated results. |
| Pension position | 2024 City pension PDF page 6, visible page 4 | Plan assets, obligations, and surplus use pension scope and December 31 periods. |
| Draft/audited comparative difference | Draft 2024 City PDF page 6 and 2025 City PDF page 6 | Both 2024 cash values survive and receive a reviewed comparative relationship. |
| Filename/reporting-date conflict | 2024 Water and Sewer pension filename and PDF page 6 | December 31 source content is retained and the December 21 filename discrepancy is review-blocking until resolved. |

Narrative years, note references, signatures, page numbers, and auditor-report dates are negative controls and must not become financial observations.

## Ordered Gates

| Gate | Work | Exit evidence |
| --- | --- | --- |
| 1. Source authority | Confirm eight hashes, source titles, dates, draft/audited states, and entity scopes. | Approved registry and exact discrepancy decisions. |
| 2. Full profile | OCR and classify all 188 pages and every statement or schedule candidate. | No unclassified financial table; every page has a disposition. |
| 3. Schema spike | Materialize representative patterns and test schema fit. | Architecture approval; all seven controls fit without loss of source meaning. |
| 4. Migration | Implement migrations 029 and 030 and isolated regression tests. | Clean rebuild, migration, constraint, and current-budget snapshot regression tests pass. |
| 5. Raw extraction | Generate all raw artifacts and import raw records. | Artifact/database counts agree; stable-key rerun is identical. |
| 6. Mapping review | Review periods, statement classes, hierarchy, entity scope, signs, value states, comparatives, and budget-equivalence candidates. | Every mapped row has exact source evidence; unresolved rows remain blocked individually. |
| 7. Normalized dry run | Generate manifests, reconciliations, and a zero-write import plan. | Deterministic plan hash, zero missing evidence, zero incompatible approved relationships. |
| 8. Controlled import | Back up the database, import transactionally, and rerun. | First import and idempotence evidence; no current snapshot changes. |
| 9. Data quality | Validate source fidelity and all statement roll-forwards by family. | Zero unexplained mismatches; every exception has a review decision and publication effect. |
| 10. API and UI | Add read APIs and holistic finance views against a draft snapshot. | API, browser, accessibility, scope, and source-tracing tests pass. |
| 11. Publication | Review exact snapshot membership and coverage. | Explicit authorization; no open high/critical issue; published snapshot remains immutable. |

No gate implies approval of the next database mutation. Dependency, environment, backup, migration, and deployment actions remain subject to the DevOps approval gate.

## API And Web Work

Extend `web/server.js` only after Gate 9 with:

- `GET /api/finances/summary`
- `GET /api/finances/statements`
- `GET /api/finances/budget-actual`
- `GET /api/finances/position`
- `GET /api/finances/cash-flow`
- `GET /api/finances/pensions`
- `GET /api/finances/coverage`

Add `/finances`, `/finances/budget-actual`, `/finances/position`, `/finances/cash-flow`, and `/finances/pensions`. Every response and page must expose period dates, reporting entity, consolidation scope, authority status, units, coverage, warnings, and source citations. Default citywide totals use the audited consolidated City scope.

## Test Files

| Test file | Required coverage |
| --- | --- |
| `schema/tests/029_budget_financial_statement_context_regression.sql` | New tables, constraints, relationship compatibility, controlled review decisions, and no effect on migration 028 records. |
| `schema/tests/030_budget_financial_statement_publication_regression.sql` | Draft snapshot membership, view uniqueness, non-additive entity scopes, current budget snapshot stability, and publication immutability. |
| `scripts/test-financial-statements-extraction.py` | OCR coordinates, stable keys, headers, signs, parentheses, dashes, row hierarchy, and narrative-number negative controls. |
| `scripts/test-financial-statements-normalization.py` | Period roles, statement classes, aggregation roles, value states, entity scopes, comparative preservation, and budget-equivalence rejection controls. |
| `scripts/test-financial-statements-import.py` | Dry run, transactional rollback, idempotence, changed-source conflict, expected counts, and coexistence with current budget observations. |
| `scripts/validate-charlottetown-financial-statements-provenance.py` | Exact observation-to-cell and relationship-to-decision fidelity across all four series. |
| `scripts/verify-charlottetown-financial-statements-qa.py` | Statement reconciliation, roll-forwards, draft/audited differences, component double-counting, pension isolation, and publication blockers. |
| `scripts/smoke-financial-statements-api.mjs` | Filters, pagination, incompatible-scope reasons, source details, empty states, and CSV/JSON consistency if export is added. |
| `scripts/smoke-holistic-finance-web.mjs` | Route rendering, scope labels, source links, keyboard access, responsive tables, and warning visibility. |

`scripts/test-budget-migration.py` must include migrations 029 and 030 in clean-database migration testing. `scripts/smoke-web-demo.mjs` must retain all existing budget checks as negative regression controls.

## Acceptance Criteria

- All eight documents and 188 pages are registered with hashes and reviewed authority metadata.
- Every detected statement and schedule has a disposition.
- Every published observation has document, page, table, row, cell, period, entity, statement class, unit, value state, and review provenance.
- Draft and audited comparative values remain independently queryable.
- Budget-to-actual output uses only approved observation relationships and exact compatible scope.
- City consolidated, Water and Sewer component, and pension scopes cannot be summed accidentally by publication views or APIs.
- Every reported statement total and roll-forward passes within CAD 1 or carries a visible approved exception appropriate to source rounding.
- No unresolved high or critical source-authority, extraction, normalization, scope, or reconciliation issue enters a published snapshot.
- Raw generation, manifest generation, import, and QA are deterministic and idempotent.
- Existing budget snapshot counts, API behavior, and browser routes remain unchanged until a separately approved holistic snapshot and routes are published.

## Stop Conditions

Stop at the current gate when a source date or authority state is unresolved, a statement pattern does not fit the spike, OCR loses a sign or column association, a comparative relationship is not exact enough for review, accounting scope is incompatible, a reconciliation cause is unknown, or an implementation step would expose unreviewed data.

## Sources

- [Municipal budgets](./README.md)
- [Municipal budget requirements](./requirements.md)
- [Municipal budget database schema](./database-schema.md)
- [Budget API and UI contract](./api-and-ui-contract.md)
- [Budget ingestion refactor tracker](./budget-ingestion-refactor-tracker.md)
- [Document extraction engineering](../implementation/document-extraction-engineering.md)
- `schema/sql/025_budget_schema.sql`
- `schema/sql/027_budget_web_taxonomy.sql`
- `schema/sql/028_budget_content_and_observation_model.sql`
- `docs/charlottetown/financial-statements/`
- `data/financial-statements/charlottetown/source-document-registry.json`
- `data/financial-statements/charlottetown/source-authority-review.json`
