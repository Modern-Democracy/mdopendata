---
type: implementation
tags:
  - budget
  - web-ui
  - taxonomy
  - migration
updated: 2026-07-13
---

This page records the implemented budget-edition, taxonomy-overlay, assignment, filtering, and browser-review slice.

# Budget Web And Taxonomy Implementation Status

## Authorization And Scope

On 2026-07-13, the project owner authorized the database migration, assignment writes, and a taxonomy-semantic revision for published snapshot `1`. The implementation preserves the snapshot's 6,256 fact memberships and source-document scope while changing its effective category taxonomy from `charlottetown-budget-v1` to `charlottetown-budget-category-v1` through an explicit revision overlay.

The category mappings remain `proposed`. Approved writes are limited to source-evidenced budget editions, project-to-department assignments, capital-program page assignments, and uniquely matched subsequent forecasts.

## Applied Schema

Migration `027_budget_web_taxonomy.sql` adds:

- annual budget-edition ownership and subsequent-document links
- snapshot taxonomy revision metadata
- versioned line-item and capital-funding category assignments
- project organization assignments
- capital programs and source-line assignments
- original-fact to subsequent-observation links
- an extended one-row-per-fact `budget.v_published_facts`

The pre-migration backup is `backups/database/mdopendata-before-budget-web-taxonomy-20260713.dump`.

## Applied Data

| Record | Count | Review state |
| --- | ---: | --- |
| Budget editions | 3 | approved |
| Normalized categories | 34 | candidate vocabulary |
| Controlled-label line assignments | 667 | proposed |
| Project department assignments | 24 | approved from approved profile fields |
| Capital programs | 9 | approved |
| Capital program line assignments | 577 | approved from explicit source-page headings |
| Subsequent forecast links | 333 | approved exact one-to-one matches |
| Capital funding category assignments | 0 | none met the approved rule |

The forecast links comprise 158 matches from the 2024/2025 edition into the 2025/2026 document and 175 matches from the 2025/2026 edition into the 2026/2027 document. Matching requires the same municipality entity, statement family, normalized source label, unit, and original budget value; the later observation must be the forecast cell on the same later-document line. Both the original and later forecast must have exactly one candidate. Unmatched and ambiguous observations remain unavailable.

## Public Web Behavior

- `/budgets` selects one annual PDF by `document_id`; it does not merge documents that share a fiscal-period label.
- Prior-year operating rows show the uniquely matched subsequent forecast where available.
- Revenue and expense candidates are separate tables with detail subtotals and expenditures-minus-revenue. They are visibly labeled proposed and do not replace source totals.
- Source-reported operating totals, capital programs and projects, tax/rate facts, debt facts, and external-funding deductions have separate sections.
- `/budgets/facts` explains the fact model and filters published facts by edition, department, program, project, category, category status, statement kind, amount type, aggregation role, and label search.
- Department, program, and project filters are enforced in SQL for the fact collection and relevant operating, capital, project, and CSV endpoints.

Dedicated cross-year department, project-detail, and municipal-analysis pages remain planned work. The current fact explorer supplies the review surface required to evaluate assignments before those pages are built.

## Verification

- Isolated migration and regression SQL passed.
- The assignment script is idempotent; a repeat apply wrote zero additional records.
- Snapshot membership and `budget.v_published_facts` both remain exactly 6,256 rows with no duplicate fact rows.
- The 30-check web smoke suite passed, including edition, department, program, and project filtering.
- Browser checks confirmed edition switching, a rendered subsequent forecast, URL-applied project filtering, and no console errors.

## Known Limits

- Proposed category subtotals are incomplete and may contain false-positive controlled-label matches. Browser review is required before approval.
- Source hierarchy is preserved through statement identity, source order, reporting entity, organization assignments, aggregation roles, and explicit capital-program headings. No parent-child line-item links were invented where the source import did not encode them.
- Only exact, unique subsequent forecasts are displayed. This is not a general restatement or actual-results matching system.
- The annual page loads every primary-period fact for source completeness; detailed interactive analysis remains paginated in the fact explorer.

## Sources

- [Dedicated budget page views plan](./dedicated-page-views-plan.md)
- [Normalized category taxonomy proposal](./normalized-category-taxonomy-proposal.md)
- [API and UI contract](./api-and-ui-contract.md)
- [Database schema](./database-schema.md)
- [Project environment](../platform/project-environment.md)
- [Migration SQL](../../schema/sql/027_budget_web_taxonomy.sql)
- [Assignment script](../../scripts/apply-budget-web-taxonomy.py)
- [Apply report](../../data/budget/charlottetown/budget-web-taxonomy-apply-report.json)
