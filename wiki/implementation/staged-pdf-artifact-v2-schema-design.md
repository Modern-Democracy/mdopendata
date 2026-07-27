---
type: implementation
tags:
  - extraction
  - pdf
  - json-schema
  - review-ui
  - templates
updated: 2026-07-27
---

This page defines the approved version 2 staged PDF artifact design for internal titles, spanning table cells, template policies, and policy-governed approval.

# Staged PDF Artifact Version 2 Schema Design

## Status And Compatibility Decision

The design is approved. Phase 1 schema and validator changes were implemented on 2026-07-17, and the Phase 2 parallel migration completed on 2026-07-27. Version 1 remains frozen in `schema/json-schema/staged-pdf-artifacts.schema.json`; version 2 remains separate in `schema/json-schema/staged-pdf-artifacts-v2.schema.json` with no active-workspace transition.

Version 2 is required by the new template-review-policy artifact, application-policy provenance, and automated review-event semantics. Optional span fields alone would not require rewriting version 1 instances, but they are implemented only in version 2 to preserve the closed version 1 contract.

The Phase 0 baseline and controls are stored in `data/budget/charlottetown/2026-2027/staged-pdf/v2/phase-0/baseline-and-controls.json`. `scripts/test-staged-pdf-v2-phase0.py` protects the recorded version 1 schema, artifact, generator, and writer hashes. `scripts/test-staged-pdf-artifact-schemas-v2.py` exercises version 2 positive, negative, conditional, audit, and cross-artifact controls. `scripts/test-staged-pdf-artifact-v2-migration.py` protects deterministic migration, preservation, exact references, and atomic conflict behavior.

## Schema Location And References

The planned schema path is:

```text
schema/json-schema/staged-pdf-artifacts-v2.schema.json
```

Version 2 artifacts use `schema_version: 2`. Version 2 `artifact_ref` adds required `schema_version` so a hash and key cannot ambiguously identify a contract version.

## Formatted-Text Titles

Add `title` to `internal_region.region_type`. Formatted-text regions then support:

- `title`
- `paragraph`
- `bullet_list`
- `sorted_list`

Add `internal_region_rules` to `structural_template`. Each rule records `rule_key`, `parent_block_type`, `region_type`, `minimum_count`, `maximum_count`, nullable `reading_order`, and `required`.

Semantic validation requires:

- every internal region is inside its parent block
- internal reading order is deterministic
- unsupported region overlap is rejected
- the same source geometry is not duplicated as an internal title and sibling title block without an explicit reviewed relationship

## Span-Aware Table Cells

Add these optional properties to `table_cell`:

```json
{
  "column_span": {
    "type": "integer",
    "minimum": 1,
    "default": 1
  },
  "row_span": {
    "type": "integer",
    "minimum": 1,
    "default": 1
  }
}
```

JSON Schema `default` is an annotation and does not modify an instance. Every consumer must therefore calculate:

```text
effective_column_span = cell.column_span if present else 1
effective_row_span = cell.row_span if present else 1
```

Omitted spans and explicit unit spans are semantically identical. Canonical serialization preserves omission unless a command explicitly changes the span.

### Coverage Model

A cell at `(row_index, column_index)` covers every coordinate in:

```text
row_index <= row < row_index + effective_row_span
column_index <= column < column_index + effective_column_span
```

The semantic validator expands every cell into covered coordinates and requires:

- no span extends beyond row or column bounds
- no coordinate is covered by more than one cell
- every grid coordinate is covered exactly once
- every `cell_key` remains unique
- relationship endpoints reference the logical spanning cell, not a covered coordinate

The current one-cell-per-coordinate invariant is replaced by exact expanded coverage.

## Table Titles

Add `table_title` to `table_cell.cell_type`.

A valid table-title cell requires:

- `column_index: 0`
- effective column span equal to the table column count
- effective row coverage beginning at row `0` or ending at the final row
- zero other `table_title` cells in the table
- exact source text and evidence preserved on the logical cell

The title may span one or more adjacent physical rows. Body column bands remain independent of the title span.

Add required `table_title_policy` to `structural_template`:

| Field | Contract |
| --- | --- |
| `mode` | `required`, `optional`, or `absent` |
| `allowed_positions` | Unique subset of `top` and `bottom` |
| `anchor_keys` | Template anchors used to detect the title |

A missing required title or unexpected title under `absent` is material variation.

## Span Mutation Contract

Version 2 retains global row and column boundary commands and adds logical-cell actions:

- `merge_table_cells`
- `split_table_cell`
- `set_table_cell_span`

Mutation rules are:

- merge targets form one complete rectangle without gaps
- referenced cells cannot be consumed without explicit relationship retargeting
- merged text preserves source order and all physical evidence
- split restores complete coordinate coverage and creates deterministic stable keys
- title merge sets full-width coverage; title split requires explicit reclassification away from `table_title`
- every result passes expanded-coverage validation before publication

## Template Review Policy Artifact

Add `template_review_policy` to the artifact union and artifact-reference vocabulary. It is separate from `structural_template` because structural rules and trust policy change independently.

Each immutable policy artifact records:

| Area | Required fields |
| --- | --- |
| Identity | `policy_key`, `policy_version`, `artifact_key` |
| Template binding | template key, version, schema version, artifact hash |
| History | nullable superseded policy reference |
| Scope | reuse scope, jurisdiction, source family, document family |
| Matcher | name, version, configuration hash |
| Mode | `review_required`, `sample_review`, or `auto_approve` |
| Eligibility | fit classes and allowed light-mismatch categories |
| Sampling | review sample rate |
| Promotion gates | configurable evidence and error thresholds |
| Evidence | positive applications, negative controls, validation runs, and observed counts |
| Suspension | material mismatch, control failure, sampled rejection, matcher change, and source-profile change rules |
| Approval | standard review object with human decision IDs |

Conditional validation requires:

- `review_required` uses sample rate `1`
- `sample_review` uses a rate greater than `0` and less than `1`
- `auto_approve` permits rate `0`
- `material_variation` is never eligible
- `light_variation` is eligible only when every mismatch category is allowlisted
- a policy cannot be approved without human decision evidence

Promotion, demotion, suspension, or retirement creates a superseding policy artifact. Prior policy files remain immutable.

## Template Application Policy Evaluation

Add required `policy_evaluation` to `template_application` with:

- nullable exact policy artifact reference
- outcome: `review_required`, `selected_for_sample`, `auto_approved`, or `blocked`
- `selected_for_sample`
- `fit_eligible`
- matcher configuration hash
- reason codes

Semantic validation requires:

- material variation resolves to `review_required` or `blocked`
- automatic approval resolves an approved policy, exact template hash, eligible fit, and allowed mismatch set
- `auto_approved` applications have `review.status: approved` and at least one decision ID
- a sampled application remains `needs_review` until a human decision exists

## Review Event Changes

Extend `reviewer` with required `actor_type`, using `human` or `system`. Add required `decision_basis`, using `reviewer` or `template_policy`, and nullable `policy_ref`.

Add actions:

- `auto_approve`
- `promote_policy`
- `demote_policy`
- `suspend_policy`
- `migrate_schema`

An automated approval requires a system actor, `decision_basis: template_policy`, and an exact non-null policy reference. Policy promotion requires a human actor.

## Migration Contract

1. Preserve version 1 schema, artifacts, and review chains.
2. Generate version 2 artifacts beside version 1.
3. Preserve omitted unit spans rather than materializing them mechanically.
4. Treat omitted spans as effective `1` in all version 2 consumers.
5. Do not infer internal titles, table titles, or non-unit spans during envelope migration.
6. Seed approved templates with a separate `review_required` policy before broader use.
7. Preserve stable source, page, block, region, cell, group, and application keys where structure is unchanged.
8. Record version 1 input hashes and version 2 output hashes in an append-only migration decision.
9. Revalidate relationships, templates, applications, and dependent approvals against version 2.
10. Retain zero database and publication writes throughout shadow migration.

The implemented migration command is:

```powershell
& scripts/python.ps1 scripts/migrate-staged-pdf-artifacts-v1-to-v2.py `
  --occurred-at 2026-07-27T00:00:00Z
```

It writes only the parallel `v2/stage-0`, `v2/stage-1`, `v2/review`, and `v2/phase-2` outputs. Existing identical outputs are unchanged; any conflicting output stops the run before writes. The pilot had no version 1 structural-template artifact, so the eligible and seeded `review_required` policy counts are both zero.

## Affected Implementation Surfaces

- `schema/json-schema/staged-pdf-artifacts-v2.schema.json`
- `scripts/validate-staged-pdf-artifacts.py`
- version 2 migration script and migration regressions
- `scripts/generate-staged-pdf-block-inventory.py`
- `scripts/update-staged-pdf-block-inventory.py`
- `web/public/pdf-inventory-review/app.js`
- `web/public/pdf-inventory-review/index.html`
- `web/public/pdf-inventory-review/styles.css`
- `web/server.js`
- structural-template and template-application generators

## Sources

- [Staged PDF reviewer propagation requirements](./staged-pdf-reviewer-propagation-requirements.md)
- [Staged PDF artifact version 2 implementation plan](./staged-pdf-artifact-v2-implementation-plan.md)
- [Staged PDF artifact JSON Schemas](./staged-pdf-artifact-json-schemas.md)
- [Staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md)
- `schema/json-schema/staged-pdf-artifacts.schema.json`
- `scripts/validate-staged-pdf-artifacts.py`
