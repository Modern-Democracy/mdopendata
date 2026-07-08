---
type: implementation
tags:
  - budget
  - import
  - reconciliation
  - data-quality
updated: 2026-07-08
---

This report identifies the exact gaps between the reviewed Charlottetown 2026/2027 normalization artifacts and the PostgreSQL normalized-import contract.

# 2026/2027 Normalized Import Gap Report

## Conclusion

The reviewed artifacts are source-faithful but are not database-ready. A direct import is blocked because required statement identities, database vocabularies, source-column periods, fact keys, extension links, and complete reconciliation definitions do not yet exist. No database writes were performed during this audit.

## Audited Scope

| Item | Observed |
| --- | ---: |
| Normalization JSON files | 28 |
| Mapped rows | 1,157 |
| Mapped facts | 2,159 |
| Narrative capital profiles | 24 |
| Facts with `source_value_id` | 2,159 |
| Source IDs missing from raw values | 0 |
| Current database statements | 7 |
| Current database line items | 16 |
| Current database facts | 19 |
| Current database fact-source links | 21 |
| Current database reconciliations | 7 |
| Current database review issues | 3 |
| Publication snapshots | 0 |

The current normalized database content is the representative spike, not the completed full-document review.

## Blocking Gaps

### 1. No Full-Document Import Manifest

The representative importer requires one manifest containing documents, cases, reporting entities, fiscal periods, document periods, source columns, statements, line items, facts, fact-source evidence, reconciliation inputs, and review-issue links. The 2026/2027 output is split across family-specific review files and does not provide this import-level identity graph.

Required output: a deterministic full-document manifest with stable natural keys and expected counts.

### 2. Missing Statement Identity And Scope

The row mappings generally identify a section and page but do not consistently define:

- `statement_key`
- `statement_kind`
- `reporting_entity_key`
- source table identity for the statement
- fund identity where applicable
- parent/component statement relationships

These values cannot be inferred solely from row labels. They must be configured per reviewed section or table family.

### 3. Missing Stable Line And Fact Keys

Rows preserve `row_id` and raw labels, but do not define database `line_key` values. Facts do not define stable fact keys. The importer therefore cannot resolve reconciliation inputs, detect rerun equivalence, or distinguish repeated labels within one statement without a key-generation contract.

Required rule: line keys must derive from stable statement identity plus source row identity, not insertion order or label text alone. Fact keys must include line, document period, amount type, and measure unit.

### 4. Source Values Are Not Yet Source Cells

All 2,159 mapped facts resolve to raw `source_value_id` records. The database requires `fact_source.source_cell_id`. A deterministic bridge is required from:

`source_value_id` -> raw row -> source table -> value column index -> imported `source_table_cell`.

This bridge is viable, but must validate that the selected source cell contains the same raw token and parsed numeric value. Page 87 split-line reconstruction requires explicit evidence that one logical line may cite cells from more than one physical row.

### 5. Document Periods Are Not Materialized Per Source Table

Observed fact period labels are:

| Artifact period | Facts |
| --- | ---: |
| `2026-2027-budget` | 1,163 |
| `2025-2026-budget` | 529 |
| `2025-2026-forecast` | 452 |
| Top-level rate period, absent from row facts | 15 |

The schema requires each `document_period` to reference the exact source-table column. A global period label is insufficient because column 1 has different meanings across table families. The manifest builder must create table-specific period records and validate every fact against its source column.

### 6. Vocabulary Mismatches

Artifact aggregation roles do not match database constraints:

| Artifact role | Rows | Required database treatment |
| --- | ---: | --- |
| `additive_detail` | 711 | `detail` |
| `supporting_breakdown` | 301 | Usually `non_additive`; must remain linked to its authoritative summary |
| `reported_total` | 121 | `total` or `subtotal`, based on reviewed hierarchy |
| `deduction` | 9 | Explicit detail/non-additive treatment plus funding-deduction amount type |
| Missing on rate rows | 15 | Define rate-specific non-additive treatment |

Artifact value state `reported_value` appears on 2,118 facts, while the database accepts `reported`. The 41 `dash_unresolved` facts already match the database vocabulary.

Artifact measure units require translation and schema coverage:

| Artifact unit | Facts | Database status |
| --- | ---: | --- |
| `CAD` | 2,144 | Translate to seeded `cad` |
| `CAD_per_100_assessed_value` | 8 | Translate to seeded `cad_per_100_assessed` |
| `CAD_per_year` | 3 | Missing seed |
| `CAD_per_day` | 2 | Missing seed |
| `CAD_per_cubic_metre` | 2 | Missing seed |

Adding the three missing measure units is a schema seed change and must be separately approved.

### 7. Amount Types Are Incomplete

Of 2,159 facts, 1,603 lack `amount_type`. Existing explicit values are `reported_amount` (512), `partner_funding` (11), and debt `balance`, `principal`, and `interest` (11 each).

Required mappings include:

- operating period roles to `budget` or `forecast`
- capital details to `gross`
- external partner deductions to `funding_deduction`
- net capital totals to `net`
- rate facts to an approved rate amount-type treatment
- `reported_amount` and `partner_funding` translation to seeded database codes

Capital totals cannot all use one amount type because gross, funding deduction, and net are distinct facts.

### 8. Reporting Entities And Organization Units Are Partial

Some artifacts name organization units, but the full set of reporting entities and unit hierarchies is not declared in an importable dimension block. The manifest must explicitly cover at least City of Charlottetown, Charlottetown Water and Sewer, Civic Centre Management Inc., and Bell Aliant Centre, with reviewed organization units for departmental statements.

### 9. Capital And Debt Extensions Are Not Import-Complete

The 24 capital profiles preserve narrative fields, but do not provide stable capital-project keys, aliases, source-row links for each profile field, or project-to-fact links. Capital schedule rows require `capital_project_fact` links and distinct gross/deduction/net treatment.

The ten debt instruments preserve labels and maturity years, but still require stable instrument keys, lender/type parsing decisions, effective dates, and `debt_fact` links. Unknown lender/type attributes should remain null rather than inferred.

### 10. Reconciliation Coverage Is Representative Only

`reconciliation-report.json` currently carries seven representative-spike checks: four passed and three review results. It does not reconcile the 2,159 reviewed full-document facts.

Required full-document checks include:

- operating revenue, expense, and net totals by statement and period
- departmental summary/detail comparisons without double counting
- Civic Centre revenue minus expenses equals net income
- Bell Aliant departmental totals and earnings/loss for both periods
- capital gross less partner funding equals reported net
- consolidated capital component totals
- debt principal plus interest equals reported debt service where asserted
- rate and assessment calculations where the source supplies all operands

Every reconciliation must identify exact imported fact keys. Failures require review issues before publication.

### 11. Importer Mode And Batch Identity Are Missing

The importer supports `representative` normalized import and `full` raw import only. A normalized full-document mode needs:

- an explicit extractor/importer version distinct from `full-1`
- dry-run validation before mutation
- one transaction
- expected-count checks
- source hash and manifest hash checks
- idempotent rerun behavior
- changed-content detection rather than silent `ON CONFLICT DO NOTHING`
- no publication snapshot creation

### 12. Existing Representative Data Requires Coexistence Rules

The database already contains 19 representative facts. A full import must either reuse identical natural keys or use distinct full-document statement keys and explicitly retire the spike as test-only. Without a coexistence rule, the database may contain duplicate facts from representative and full-document source tables.

## Non-Blocking Strengths

- All 116 canonical candidates have final dispositions.
- All 2,159 mapped facts resolve to raw source values.
- Raw document, page, table, row, cell, and import-batch controls already exist.
- Period labels cover the three expected budget/forecast roles.
- Dashes remain distinct from zero.
- No publication snapshot exists, so incomplete normalized records are not public.

## Required Implementation Sequence

1. Approve the full-document manifest protocol and representative-data coexistence rule.
2. Approve or add the three missing rate measure-unit seeds.
3. Generate deterministic statement, line, fact, entity, unit, period, amount-type, and extension identities.
4. Validate all 2,159 source-value-to-cell links and all 24 profile field source links.
5. Generate full reconciliation definitions using stable fact keys.
6. Add a dry-run-only full normalized importer mode and verify expected counts.
7. Run the dry run twice and compare manifest/import plans for exact equality.
8. Import in one transaction, rerun idempotently, and compare file/database counts.
9. Run source-fidelity and reconciliation QA.
10. Keep publication snapshots at zero until all blocking reconciliation issues are resolved.

## Acceptance Criteria

- Every normalized fact has one stable key, statement, line, document period, amount type, unit, value state, and reported-value source cell.
- Every artifact vocabulary value maps explicitly to an allowed database value.
- Every profile and extension record has stable identity and source provenance.
- File and database counts agree exactly by statement family.
- A second import creates no duplicate logical records and reports no silent content conflicts.
- All reported statement totals either reconcile within approved tolerance or have an open blocking review issue.
- Zero unresolved high-severity issues and zero publication snapshots remain the publication gate.

## Sources

- [Database schema](./database-schema.md)
- [Representative normalized mapping](./representative-spike-normalized-mapping.md)
- [2026/2027 normalization status](./2026-normalization-status.md)
- [Document extraction engineering](../implementation/document-extraction-engineering.md)
- `schema/sql/025_budget_schema.sql`
- `scripts/import-budget-schema-spike.py`
- `data/budget/charlottetown/2026-2027/normalization/`
- `data/budget/charlottetown/2026-2027/raw-tables/source_values.json`
