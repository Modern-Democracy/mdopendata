---
type: implementation
tags:
  - budget
  - normalization
  - charlottetown
updated: 2026-07-08
---

This page records implementation and review status for complete 2026/2027 Charlottetown budget normalization.

# 2026/2027 Normalization Status

## Completed

- Reconciled 114 first-pass tables against 116 profile candidates without dropping either source.
- Assigned one controlled disposition to all 116 canonical candidates.
- Assigned all 116 candidates to 31 reviewed source-defined sections while preserving page-level identities.
- Replaced 63 profiler continuation guesses with 85 explicit subsequent-page section relationships.
- Imported all 154 pages, 114 raw source tables, 3,233 rows, and 3,092 detected values.
- Replaced row-specific small-value and dash overrides with document-wide financial-column recovery, adding 672 aligned tokens without capturing narrative four-digit years.
- Preserved value character offsets in row metadata and recorded all missing bounding boxes as unavailable.
- Verified dry-run execution, initial import, two idempotent reruns, one full import batch, and zero publication snapshots.
- Retained 19 reviewed facts, seven reconciliation checks, and three existing review issues from the representative spike.
- Reviewed the consolidated operating section: pages 18 and 19 are duplicate presentation summaries; page 20 supplies 31 mapped lines and 91 reported facts across three explicit periods and two reporting entities.
- Reviewed operating supporting schedules: pages 21–22 supply 64 approved lines and 192 facts, including four preserved `dash_unresolved` values and recovered reported values of 300 and 500; page 23 supplies 15 approved property-tax and utility-rate mappings with explicit units.
- Reviewed City Government pages 28–33: page 28 supplies 31 authoritative lines and 93 facts; pages 29–33 supply 27 supporting breakdown amounts while narrative staff counts and layout marks remain non-financial source text.
- Reviewed Economic, Tourism and Cultural Development pages 35–41: pages 35–36 supply 37 authoritative lines and 111 facts; pages 37–41 supply 29 supporting breakdown amounts. The document-wide parser resolves the source-formatted `2, 250,000` as 2,250,000.
- Applied the reusable departmental mapper to nine equivalent sections covering Environment, Finance, Fire, Human Resources, Mayor and Council, Parks, Planning, Police, and Water and Sewer: 249 authoritative lines, 747 facts, and 209 supporting breakdown rows were approved.
- Reviewed Public Works and Municipal Buildings pages 87-92: 41 authoritative lines, 123 facts, and 36 supporting rows were approved. Page 87 contains two distinct `Service Contracts` rows. The Public Works row reports three dashes; the Municipal Buildings row reports 161,000, 161,000, and 164,220. The rendered source also confirms Property Taxes at 360,000, Maintenance at 250,000/250,000/255,000, Public Art Maintenance at 2,000, and Snow Removal at 36,000/36,000/36,720.
- Audited the complete document for amount-before-label extraction patterns. The five-row Municipal Buildings sequence is the only materially equivalent staggered chain; other candidates on pages 35, 36, and 76 resolve from preceding labels or totals. The raw physical rows remain unchanged, and an isolated reviewed logical-row configuration reconstructs the page 87 chain without changing other sections.
- Reviewed all 13 capital budget schedules and 24 capital project profiles. The schedules map 216 rows and 240 monetary facts with explicit detail, deduction, and reported-total roles. Profiles preserve project, department, description, and strategic-alignment text while excluding narrative years, quantities, and dimensions from financial facts.
- Reviewed the page 153 Water and Sewer debt schedule: ten instruments map separate balance, principal, and interest facts, maturity years remain instrument metadata, and the three reported totals are preserved.
- Classified page 15 Funding and Taxation as narrative-only source guidance rather than a financial table; its tax-rate examples remain source text and are not duplicated as budget facts.
- Reviewed Civic Centre operating pages 101-104: 109 single-period monetary rows preserve reported zeros, subtotals, revenue and expense totals, and net income for 2026/2027.
- Reviewed Bell Aliant departmental pages 106-108: 52 rows map 104 facts across the 2026/2027 and 2025/2026 budget columns. Presentation variance percentages are excluded from budget facts.

## Review Gate

The full raw layer and normalization review are complete. Document section membership and disposition are reviewed for all 116 candidates. No candidate remains `review_blocked`.

Current dispositions are 112 `normalize`, three `duplicate_summary`, and one `non_financial` narrative page. No publication snapshot has been created.

## Required Next Review

The unresolved review report contains zero records. The next gate is importing reviewed normalized mappings and running complete statement-level reconciliation before publication.

## Sources

- [Implementation plan](./implementation-plan.md)
- [Representative normalized mapping](./representative-spike-normalized-mapping.md)
- `data/budget/charlottetown/2026-2027/canonical-table-inventory.json`
- `data/budget/charlottetown/2026-2027/section-inventory.json`
- `data/budget/charlottetown/2026-2027/normalization-coverage.json`
- `data/budget/charlottetown/2026-2027/unresolved-review-report.json`
- `data/budget/charlottetown/2026-2027/reconciliation-report.json`
