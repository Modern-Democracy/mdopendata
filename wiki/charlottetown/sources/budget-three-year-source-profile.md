---
type: source
tags:
  - charlottetown
  - budget
  - source-profile
updated: 2026-07-07
---

This page profiles the three Charlottetown financial-plan PDFs and selects representative source tables for the budget schema spike.

# Charlottetown Three-Year Budget Source Profile

## Scope And Method

The profile covers every PDF page in:

- `2024-2025 Financial Plan Capital and Operational Budgets.pdf`
- `2025-2026 Financial Plan Capital and Operational Budgets.pdf`
- `2026-2027 Financial Plan Capital and Operating Budgets.pdf`

The repeatable profiler preserves per-page text, records PDF metadata and hashes, classifies financial table/profile candidates, records observed column and year-label patterns, detects named reporting entities, and flags adjacent same-family pages as continuation candidates. It does not normalize financial values or accept continuation joins.

## Document Inventory

| Document | PDF pages | Producer | Tagged | Table/profile candidates | Continuation candidates | OCR variation |
| --- | ---: | --- | --- | ---: | ---: | --- |
| 2024/2025 | 88 | Power PDF Create | No | 58 | 29 | PDF pages 78-87 have deficient embedded text; OCR fallback recovered facility tables on pages 78-86. |
| 2025/2026 | 150 | Acrobat Distiller 25.0 | No | 114 | 68 | Divider pages can require OCR for readable headings; financial tables retain embedded text. |
| 2026/2027 | 154 | Canva | Yes | 116 | 63 | Divider pages can require OCR for readable headings; financial tables retain embedded text. |

Candidate counts are deliberately broader than publishable table counts. A source page can be a summary duplicate, continuation, profile, or non-additive schedule and still remain a discovery candidate.

## Page Sections

| Section | 2024/2025 | 2025/2026 | 2026/2027 |
| --- | ---: | ---: | ---: |
| Front matter | 5 | 6 | 6 |
| Strategic Plan | 2 | 0 | 2 |
| Budget Overview | 5 | 4 | 8 |
| Operating Budget | 43 | 95 | 92 |
| Capital Budget | 33 | 36 | 39 |
| Appendix - Taxes and Rates | 0 | 2 | 2 |
| Appendix - Debt | 0 | 5 | 5 |

The 2025/2026 strategic-plan material is embedded in front matter rather than detected as a standalone section. Section counts describe observed document layout, not accounting scope.

## Table And Profile Families

| Family | 2024/2025 | 2025/2026 | 2026/2027 | Observed shape |
| --- | ---: | ---: | ---: | --- |
| Operating statement/summary | 22 | 22 | 27 | Item plus current budget, often prior budget/forecast; totals and net expenditure rows. |
| Operating detail | 0 | 49 | 42 | Hierarchical labels and amounts; 2025/2026 commonly adds a notes/comments column. |
| Facility operating statement | 4 | 4 | 4 | Bell Aliant Centre/CARI and related facility statements with current/prior budget and variance. |
| Capital rollup/schedule | 12 | 12 | 13 | Department/program/project amounts, gross totals, partner-funding deductions, and net totals. |
| Capital project profile | 20 | 23 | 24 | Department, project, description, strategic alignment, and narrative numbers/dates. |
| Tax assessment/rate schedule | 0 | 2 | 3 | Property class/residency, assessment base, rate per $100, calculated revenue, and totals. |
| Debt schedule | 0 | 2 | 2 | Instrument, opening balance, principal, interest, maturity embedded in instrument label, and totals. |
| Overview source table | 0 | 0 | 1 | Chart-supporting category, amount, and percentage table. |

The 2024/2025 facility detail on PDF pages 82-86 is currently included under operating statement candidates because the rasterized continuation pages do not repeat a stable facility header. The schema spike must treat it as a separate OCR-backed facility-detail pattern.

## Fiscal Column Patterns

| Document | Operating columns | Facility columns | Capital columns | Appendix columns |
| --- | --- | --- | --- | --- |
| 2024/2025 | Item; 2023/2024 budget; 2023/2024 forecast; 2024/2025 budget | 2024-25 budget; 2023-24 budget; variance %, plus a separate single-period 2024-2025 detailed statement | 2023/2024 and 2024/2025 rollup; single 2024/2025 schedule; some multi-year project amounts through 2028/2029 | None observed. |
| 2025/2026 | Item; 2024/2025 budget; 2024/2025 forecast; 2025/2026 budget; some notes/comments | 2025-26 budget; 2024-25 budget; variance % | 2024/25 and 2025/26 rollup; single 2025/2026 schedules | Assessment; rate per $100; tax revenue. Debt instrument; 2025 balance; 2025/26 principal; 2025/26 interest; notes/comments. |
| 2026/2027 | Item; 2025/2026 budget; 2025/2026 forecast; 2026/2027 budget | 2026-2027 budget; 2025-2026 budget; some variance % | 2025/26 and 2026/27 rollup; single 2026/2027 schedules | Assessment; rate per $100; tax revenue. Debt instrument; 2026 balance; 2026/2027 principal; 2026/2027 interest. |

All raw year tokens are retained in the machine profile. They are not all fiscal columns: debt maturities, strategic-plan ranges, project dates, and narrative dates also appear.

## Reporting Entities And Scopes

- City of Charlottetown
- Charlottetown Water and Sewer Utility
- Eastlink Centre
- Bell Aliant Centre, also labeled CARI
- Charlottetown Civic Centre Management Inc. in the 2024/2025 rasterized detailed statement

An entity mention does not prove statement ownership. For example, a facility statement can contain a City of Charlottetown grant line. Entity assignment remains a schema-spike review decision.

## Continuation Patterns

- Operating detail runs continue across adjacent pages, sometimes without repeated column headers.
- Capital schedules continue by department or program and can repeat the title while changing subgroups.
- Project profiles are adjacent but are separate records, not continuation tables.
- Facility statements span summary and department-specific pages that must not be joined solely by adjacency.
- Debt and tax divider pages precede single-page schedules and are not table continuations.
- OCR-backed 2024/2025 facility detail spans PDF pages 82-87; pages 82-86 contain table data and page 87 contains a final net-income line.

The generated continuation flags are review queues. No continuation group is approved by this profiling pass.

## Representative Tables For Schema Spike

| Pattern | Primary source page | Cross-year controls | Why selected |
| --- | --- | --- | --- |
| Consolidated operating statement | 2026/2027 PDF page 20 | 2025/2026 page 16; 2024/2025 page 14 | Current budget, prior budget, forecast, revenue/expense hierarchy, and entity scope. |
| Hierarchical operating detail | 2026/2027 page 30 | 2025/2026 page 25 | Parent labels, detailed labels, subtotals, amount alignment, and notes-column variation. |
| Facility operating summary | 2026/2027 page 105 | 2025/2026 page 103; 2024/2025 page 78 | Separate reporting entity, current/prior periods, grants, deductions, variance, and earnings/loss. |
| OCR-backed facility detail | 2024/2025 pages 82-87 | None | Raster-only multi-page detail, single period, continuation boundaries, and OCR provenance. |
| Consolidated capital rollup | 2026/2027 page 110 | 2025/2026 page 108; 2024/2025 page 45 | City/utility scope, prior/current periods, partner funding, and net totals. |
| Department capital schedule | 2026/2027 page 111 | 2025/2026 page 109; 2024/2025 page 46 | Project rows, subgroup totals, parenthesized partner funding, and net department total. |
| Capital project profile | 2026/2027 page 112 | 2025/2026 page 110; 2024/2025 page 47 | Narrative fields and non-financial numbers that must not become amount facts. |
| Property-tax calculation | 2026/2027 page 149 | 2025/2026 page 145 | Residency/property-class hierarchy, assessment multiplied by rate, revenue, subtotals, and grants. |
| Long-term debt schedule | 2026/2027 page 151 | 2025/2026 page 147 | Instrument identity, maturity in labels, balance, principal, interest, dashes/zeros, and totals. |

## Material Source Variations

- The 2024/2025 document is 62-66 pages shorter and does not include the tax and debt appendices present in later documents.
- 2024/2025 PDF pages 78-87 require OCR-aware handling; the later facility statements have usable embedded text.
- 2025/2026 operating detail commonly includes a notes/comments column that is absent or materially reduced in 2026/2027.
- Fiscal labels use slash, hyphen, two-digit, four-digit, and spaced variants within and across documents.
- Bell Aliant Centre and CARI labels vary; Charlottetown Civic Centre Management Inc. introduces another facility-level scope.
- Capital rollups mix gross amounts, negative/parenthesized partner funding, and net totals.
- Summary tables duplicate values represented at more detailed levels and must not be summed together.
- Project profiles contain years, quantities, and dates that are not financial periods or facts.

## Quality Status

The Week 1 discovery gate is complete: all 392 PDF pages are inventoried, every detected financial candidate has a table/profile family, source variations are documented, and representative tables are selected. The 160 continuation candidates remain unresolved by design and must be reviewed during the representative-table/schema spike before table assembly.

## Sources

- [Municipal budget requirements](../../budgets/requirements.md)
- [Budget implementation and test plan](../../budgets/implementation-plan.md)
- [2026/2027 first-pass profile](./budget-2026-2027-first-pass.md)
- `data/budget/charlottetown/2024-2025/source_profile.json`
- `data/budget/charlottetown/2025-2026/source_profile.json`
- `data/budget/charlottetown/2026-2027/source_profile.json`
- `scripts/profile-charlottetown-budget-pdf.py`
