---
type: implementation
tags:
  - budget
  - capital-project
  - lifecycle
updated: 2026-07-09
---

This page defines source-limited capital-project identity, lifecycle, and budget-reference rules for the Charlottetown prototype.

# Capital Project Lifecycle And References

## Identity Rule

A capital project is municipality-scoped and has no budget-year ownership. A budget document references a project through reviewed source evidence; it does not create a year-specific project identity.

## Lifecycle Rule

| Status | Assignment rule |
| --- | --- |
| `active` | An adopted budget allocates money to the project. |
| `proposed` | A draft budget references or allocates money to the project and has not been adopted. |
| `complete` | Default when the project is absent from the immediately following adopted budget. Explicit completion language also assigns this status. |
| `dormant` | The current budget omits funding but explicitly states that work will continue in a future fiscal year. |
| `unknown` | No source-supported lifecycle conclusion exists. |

An adopted-budget allocation establishes `active`, not spending. An omitted allocation in the immediately following adopted budget establishes `complete` by prototype default. This inference is superseded by explicit future-work language, which establishes `dormant`. Draft budgets may establish `proposed` but do not replace the adopted-budget lifecycle result.

## Reference And Evidence Rule

Each reference records the source document, source table or profile, raw label, reporting entity, document adoption state, and identity evidence. `exact` and reviewed `strong` evidence may link references to a common project. `possible`, `conflicting`, split, and merge cases remain review records and do not create compatibility claims.

## Schema Contract

`budget.capital_project` stores the project identity and current source-supported lifecycle status. `budget.capital_project_reference` is owned by the source document and links that document's table/profile reference to the project. Facts and profile fields link through the referenced project. Project identity never stores a budget-year foreign key.

## Sources

- [Municipal budget requirements](./requirements.md)
- [Municipal budget database schema](./database-schema.md)
- [Prior-year Phase 1 status](./prior-year-normalized-import-phase-1-status.md)
