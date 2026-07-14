---
type: implementation
tags:
  - budget
  - schema
  - api
  - web-ui
updated: 2026-07-13
---

# Budget Content And Observation Redesign Status

## Applied Outcome

- Migration 028 performs a breaking rename of numeric `fact` records to `financial_observation` throughout schema, publication membership, extensions, views, scripts, and APIs. No compatibility aliases are provided.
- `budget.fact` now stores contextual `narrative`, `attribute`, or `list` content with page citations.
- `budget.document_section` applies the 2026/2027 table-of-contents pattern to all three published editions while preserving edition-specific page ranges and missing sections.
- Four universal municipal-budget explanations are stored as editorial guides rather than source facts.
- Eight Strategic Plan 2022 to 2026 facts are sourced from `docs/charlottetown/Strategic Plan 2022 to 2026_FINAL.pdf` and reused across all editions.
- Department pages combine source summaries, programs/services, highlights, operating observations, and source-supported capital projects.
- Projects exist only in capital views and combine profile facts with financial observations.
- Property-tax and debt appendices are separate. The 2026/2027 property-tax and City debt schedules were recovered from reviewed raw tables; 2024/2025 displays explicit source-absence placeholders.

## Published Counts

| Record | Count |
| --- | ---: |
| Canonical edition sections | 101 |
| Contextual facts | 446 |
| Financial observations | 6,381 |
| Observation-to-section mappings | 6,381 |
| 2026/2027 property-tax appendix observations | 76 |
| 2026/2027 City debt appendix observations | 49 |
| 2026/2027 Water and Sewer debt appendix observations | 33 |

## Verification

- Clean isolated migrations 025, 027, and 028 and their regression controls pass.
- The contextual-content import is idempotent against immutable published observations.
- All contextual facts are non-empty and free of detected mojibake.
- All financial observations map to exactly one reviewed document section.
- All 67 edition-specific project profiles have project, department, and description context; Strategic Alignment is published only when the source field is non-empty.
- Exact 2026/2027 controls match the source: Total Property Taxes CAD 52,916,036; Municipal Support Grant CAD 26,122,822; City debt balance CAD 144,755,212; principal CAD 5,871,868; interest CAD 5,150,182; total interest and principal CAD 11,022,050.
- The full portal smoke suite and browser checks for contents, department composition, appendix population, and absent-section handling pass.

## Formatting And Table Corrections

- Contextual facts use semantic heading, paragraph, unordered-list, and ordered-list blocks. PDF hard line wrapping is removed from normalized paragraph content.
- Financial tables pivot observations into one source-aligned row per line item, with fiscal periods or source measures as columns and evidence retained in each value cell.
- Operating overview statements appear before departments. Capital overview pages appear before programs and projects.
- Property-tax schedules align Assessment, Rate, and Tax Revenue on one row. City and Water and Sewer debt schedules align Balance, Principal, and Interest on one row with source-period labels.

## Primary Artifacts

- `schema/sql/028_budget_content_and_observation_model.sql`
- `schema/tests/028_budget_content_and_observation_model_regression.sql`
- `scripts/build-budget-context-content.py`
- `data/budget/charlottetown/context-content.json`
- `web/server.js`
- `web/public/ui_kits/budgets/index.html`
