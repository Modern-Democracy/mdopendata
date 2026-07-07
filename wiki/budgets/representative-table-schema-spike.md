---
type: implementation
tags:
  - budget
  - schema
  - spike
updated: 2026-07-07
---

This page records the representative-table schema spike used to gate municipal budget SQL migrations.

# Representative-Table Schema Spike

## Status

The representative schema spike is ready for a draft migration. Seven source patterns have been mapped, 408 rows plus 837 cells have been materialized across 12 source pages, all OCR facility rows/cells have normalized word coordinates, and three open review issues encode unresolved source findings. No migration has been created.

## Cases Reviewed

| Case | Primary source | Cross-year controls | Result |
| --- | --- | --- | --- |
| Operating detail | 2026/2027 PDF page 30 | 2025/2026 page 25 | Supports heading-only rows, detail rows, subtotals, notes cells, and unresolved dash states. |
| Facility operating summary | 2026/2027 page 105 | 2025/2026 page 103; 2024/2025 page 78 | Requires statement entity separate from revenue-source labels and document-specific prior-period observations. |
| OCR facility detail | 2024/2025 pages 82-87 | None | Requires explicit OCR provenance and multi-page table membership. |
| Capital partner funding | 2026/2027 page 111 | 2025/2026 page 109; 2024/2025 page 46 | Requires distinct gross, funding-deduction, and net facts plus non-additive reported totals. |
| Capital project profile | 2026/2027 page 112 | 2025/2026 page 110; 2024/2025 page 47 | Narrative numbers must remain profile evidence unless explicitly labeled as financial amounts. |
| Property-tax calculation | 2026/2027 page 149 | 2025/2026 page 145 | Requires assessment, rate, denominator, and revenue facts linked to one source expression and hierarchical tax classes. |
| Long-term debt | 2026/2027 page 151 | 2025/2026 page 147 | Requires instrument maturity separate from fiscal period and distinct balance, principal, interest, zero, and dash states. |

## Confirmed Schema Fits

- Long-form facts correctly avoid fixed fiscal-year columns.
- Reporting entity must be independent from municipality and organization-unit labels.
- `aggregation_role` can distinguish details from source subtotals and totals.
- `value_state` is required to distinguish numeric zero, unresolved dash, missing, and not applicable.
- Capital project profiles belong outside the financial fact table unless a profile field explicitly reports an amount.
- Debt maturity belongs on `debt_instrument`, not `fiscal_period`.

## Resolved Schema Gaps

| Gap | Resolution |
| --- | --- |
| Document-period primary key | Add `budget.document_period.id`; facts reference it directly. |
| Extraction provenance | Add method, extractor version, confidence, and review status to `source_page`; retain parser confidence on rows/cells. |
| Tax expression with multiple facts | Add `budget.fact_source` as a many-to-many evidence junction with source roles. |
| Multi-page table membership | Add `budget.source_table_page` with page order, role, page-local bounding box, and extraction-method override. |
| Raw period-label variants | Add `budget.source_table_column`; bind each document period to a reviewed source column and use source-column identity rather than label text for uniqueness. |

Notes/comments remain raw cells even when they do not produce facts. Reported totals can participate in reconciliation while `aggregation_role` excludes them from default detail aggregation.

## Preliminary Key Decisions

| Record | Proposed natural identity for the spike |
| --- | --- |
| Source document | SHA-256 plus source identity metadata. |
| Source page | Document plus PDF page number. |
| Source table | Document plus reviewed table key. |
| Source row | Source table plus stable row key derived from page, physical row, and content hash. |
| Source cell | Source row plus source column key/index. |
| Statement | Document plus reporting entity, statement kind, and reviewed statement key. |
| Line item | Statement plus reviewed hierarchical line key; raw label alone is not identity. |
| Source table column | Source table plus stable column key; raw header remains evidence, not identity. |
| Document period | Document plus source-table column and period role; linked fiscal period carries normalized dates. |
| Fact | Line item plus document period, amount type, unit, and source evidence. |
| Fact source | Fact plus source cell and evidence role. |

## Materialized Evidence

| Artifact | Records | Purpose |
| --- | ---: | --- |
| `representative-source-pages.json` | 12 | Source-table page membership, order, role, dimensions, and extraction method. |
| `representative-source-rows.json` | 408 | Stable source row keys, exact text, page identity, extraction method, and normalized bounding boxes where available. |
| `representative-source-cells.json` | 837 | Stable cell keys, row/column identity, exact text, parse status, OCR confidence, and normalized bounding boxes. |
| `reconciliation-results.json` | 7 | Formula, inputs, calculated/reported values, value state, tolerance, difference, and disposition. |
| `review-issues.json` | 3 | Stable review identity, issue code, severity, publication effect, required resolution, allowed decisions, and prohibited action. |

Embedded-text cases use PDF word coordinates normalized to page dimensions. The 2024/2025 facility case renders six pages at 180 DPI and uses Tesseract word TSV coordinates normalized to each rendered page. It contains 221 OCR rows and 442 OCR cells with zero null bounding boxes. Mean row confidence is 91.742 and minimum row confidence is 47.068. Seventeen rows and 47 cells below confidence 80 are explicitly flagged for review because samples contain character substitutions even when coordinates are valid.

## Reconciliation Results

| Check | Result | Difference | Disposition |
| --- | --- | ---: | --- |
| Environment capital gross less partner funding | Pass | 0 | Source gross, deduction, and net agree. |
| Transit capital gross less partner funding | Pass | 0 | Source gross, deduction, and net agree. |
| Combined environment and transit net | Pass | 0 | Component net totals agree with combined net. |
| PEI-resident residential property tax | Review | -1,586,558.85 | Displayed assessment multiplied by displayed rate does not equal displayed revenue. Preserve all three reported facts and record the failed derived check. |
| Debt principal plus interest | Pass | 0 | Components agree with reported combined total. |
| Facility current-period earnings | Review | Not applicable | Calculated balance is zero, but the source reports a dash; preserve `dash_unresolved`. |
| Facility prior-period earnings | Review | Not applicable | Calculated balance is 3,250, but the source reports a dash; preserve `dash_unresolved`. |

The property-tax discrepancy is a source-level arithmetic variance, not an extraction correction. The source values remain authoritative reported facts until separate municipal documentation explains the difference.

## Review Record Design

| Review key | Severity | Publication effect | Required disposition |
| --- | --- | --- | --- |
| `budget-review-2026-2027-tax-pei-resident-residential` | High | Publish reported facts with a warning; block the derived tax check. | Authoritative clarification, accept independent reported values with warning, or corrected source. |
| `budget-review-2026-2027-facility-current-earnings-dash` | Medium | Preserve `dash_unresolved`; derived zero may be shown only as derived. | Confirm zero, confirm not applicable, or retain unresolved dash. |
| `budget-review-2026-2027-facility-prior-earnings-dash` | High | Preserve `dash_unresolved`; block derived earnings unless warned. | Authoritative clarification, warned derived balance, retained unresolved dash, or corrected source. |

Each review issue has one stable key and links to its reconciliation result plus source-cell evidence. Decisions are append-only and use controlled decision codes. A superseding decision retains the earlier rationale. No review outcome may rewrite a reported source value.

## Next Spike Work

- Convert the validated field-level design into a draft SQL migration with constraints and seed values.

## Sources

- [Database schema](./database-schema.md)
- [Budget requirements](./requirements.md)
- [Implementation and test plan](./implementation-plan.md)
- [Three-year source profile](../charlottetown/sources/budget-three-year-source-profile.md)
- `data/budget/charlottetown/schema-spike/representative-table-manifest.json`
- `data/budget/charlottetown/schema-spike/spike-summary.json`
- `data/budget/charlottetown/schema-spike/reconciliation-results.json`
- `data/budget/charlottetown/schema-spike/review-issues.json`
