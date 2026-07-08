---
type: implementation
tags:
  - budget
  - normalization
  - import
updated: 2026-07-07
---

This page defines the reviewed mapping contract for importing the representative Charlottetown budget schema spike without inferring unsupported financial semantics.

# Representative-Spike Normalized Mapping

## Scope And Decision

The import has two explicit layers:

1. The raw layer imports all three documents, 12 representative pages, seven case tables, 408 rows, and 837 cells.
2. The normalized layer imports only records explicitly listed in a reviewed mapping manifest.

Numeric-looking cells, bold text, indentation, and row position are not sufficient to create a normalized fact. Rows absent from the mapping manifest remain raw-only and retain their source text, coordinates, confidence, and review state.

## Stable Identities

| Record | Stable key |
| --- | --- |
| Municipality | `charlottetown` |
| Source document | SHA-256 of the PDF; document labels remain `2024-2025`, `2025-2026`, and `2026-2027` |
| Source page | document label plus PDF page number |
| Source table | document label plus `case_key` |
| Source column | source table plus `column_index`; reviewed role is separate from identity |
| Source row | supplied `row_key` |
| Source cell | supplied `cell_key` |
| Statement | document label plus reviewed `statement_key` |
| Line item | statement key plus reviewed `line_key` |
| Document period | document, source column, and `period_role` |
| Fact | line item, document period, amount type, unit, and source evidence |

The importer must resolve database surrogate IDs from these keys and must not depend on insertion order.

## Raw-Layer Mapping

Each `case_key` creates one `source_table` per document represented by its pages. The six OCR pages form one multi-page `ocr_facility_detail` table. All other cases create one single-page table.

Source columns are created from distinct cell `column_index` values. Raw headers and semantic roles remain null or `unreviewed` until the normalized manifest assigns them. Artifact `parse_status = unreviewed` maps to database `parse_status = unparsed` because `unreviewed` is not a database parse-status value.

The OCR method `ocr_tesseract_word_tsv` maps to database extraction method `ocr`; the complete original method string is retained in import metrics. Embedded-text records map to `embedded_text`. Confidence percentages are divided by 100 before loading the database confidence fields.

## Normalized Case Mapping

| Case | Reporting entity | Statement kind | Approved normalized treatment |
| --- | --- | --- | --- |
| `operating_detail` | City of Charlottetown | `operating` | Import reviewed headings, detail lines, subtotals, notes, and mapped budget/forecast values. Preserve dashes as `dash_unresolved`. Do not infer row hierarchy from coordinates alone. |
| `facility_operating_summary` | Bell Aliant Centre | `operating` | Columns representing 2026-2027 and 2025-2026 are separate document periods. Revenue and expense sections remain distinct; the City grant is a line item, not the reporting entity. |
| `ocr_facility_detail` | Charlottetown Civic Centre Management Inc. | `operating` | Import reviewed revenue and expense rows across pages 82-87. Numeric `0.00` is `reported_zero`. Low-confidence rows remain `needs_review` and are not publishable. |
| `capital_partner_funding` | City of Charlottetown | `capital` | Map projects and reported totals separately. Gross, partner-funding deduction, and net use distinct amount types. Source totals use `total` or `non_additive`, never default detail aggregation. |
| `capital_project_profile` | City of Charlottetown | `capital_profile` | Import narrative fields into `capital_project_profile`. Do not create facts from dates, years, quantities, or narrative numbers. Link the reviewed Downtown Tree Planters alias to its capital project. |
| `property_tax_calculation` | City of Charlottetown | `tax` | Each reviewed detail expression can produce assessment, rate, and reported-revenue facts linked through `fact_source`. Tax-class hierarchy preserves residency and property class. The known variance remains a reconciliation issue. |
| `long_term_debt` | City of Charlottetown | `debt` | Each reviewed instrument receives balance, principal, and interest facts. Maturity belongs to `debt_instrument`; dashes remain unresolved and numeric zeros remain reported zeros. |

## Mapping Manifest Contract

Create `data/budget/charlottetown/schema-spike/normalized-mapping.json` before import. Each mapped row entry must contain:

- `case_key`, `row_key`, and applicable `cell_keys`
- `statement_key`, `statement_kind`, and `reporting_entity_key`
- `line_key`, optional `parent_line_key`, `line_kind`, and `aggregation_role`
- optional `organization_unit_key` and reviewed `normalized_category_key`
- for every fact: `source_cell_key`, `document_period_key`, `amount_type`, `measure_unit`, `value_state`, signed numeric value or text value, and `source_role`
- applicable extension identity: capital project, tax class, debt instrument, rate metadata, or profile field
- `review_status` and reviewer rationale for any non-obvious semantic assignment

The manifest must also define source-column roles and document periods. Raw column labels remain exact source text; normalized fiscal periods use explicit start and end dates.

## Review And Reconciliation Mapping

All seven supplied reconciliation records may be imported after their statement and fiscal-period links are present. Input fact IDs must resolve from manifest fact keys rather than storing unverified numeric inputs as fact references.

The three supplied review issues map to their reconciliation keys. Evidence must reference the exact source cells identified in the normalized manifest. Allowed source decision labels must be translated to the database decision codes in an explicit mapping table in the importer; no review decisions are created during initial import.

## Import Order

1. Validate PDF hashes and artifact schema versions.
2. Import municipality, documents, pages, tables, table pages, columns, rows, and cells.
3. Import reporting entities, fiscal periods, funds, and organization units declared by the manifest.
4. Import document periods, statements, line items, and extension dimensions.
5. Import facts and fact-source evidence in one deferred-constraint transaction.
6. Import reconciliations, review issues, and evidence links.
7. Record one completed `import_batch` per document and content-hash events for every imported natural key.

No publication snapshot is created by this import.

## Stop Conditions

Stop the import when:

- a source PDF hash differs from the manifest
- a manifest row or cell key is missing or duplicated
- a mapped cell belongs to a different case, row, table, or document
- a source column lacks an explicit period role where it produces facts
- a reported fact lacks `reported_value` evidence
- a dash, blank, parenthesized value, subtotal, or total lacks an explicit reviewed interpretation
- a reconciliation input cannot resolve to an imported fact
- record counts differ from 12 pages, 408 rows, 837 cells, seven reconciliations, or three review issues

## Review Result

The mapping architecture is approved for importer implementation. Normalized data import remains blocked until `normalized-mapping.json` contains reviewed row-level and cell-level assignments. The current artifacts are sufficient for the raw layer only.

## Sources

- [Municipal budget requirements](./requirements.md)
- [Municipal budget database schema](./database-schema.md)
- [Representative-table schema spike](./representative-table-schema-spike.md)
- `data/budget/charlottetown/schema-spike/representative-source-pages.json`
- `data/budget/charlottetown/schema-spike/representative-source-rows.json`
- `data/budget/charlottetown/schema-spike/representative-source-cells.json`
- `data/budget/charlottetown/schema-spike/reconciliation-results.json`
- `data/budget/charlottetown/schema-spike/review-issues.json`
