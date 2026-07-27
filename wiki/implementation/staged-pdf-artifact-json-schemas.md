---
type: implementation
tags:
  - extraction
  - pdf
  - json-schema
  - architecture
  - quality-assurance
updated: 2026-07-27
---

This page defines the version 1 JSON Schema contracts and semantic validation rules for staged PDF inventory artifacts.

# Staged PDF Artifact JSON Schemas

## Status

The version 1 contracts are implemented in `schema/json-schema/staged-pdf-artifacts.schema.json` using JSON Schema Draft 2020-12.

Version 1 remains closed and unchanged. Phase 1 of the approved version 2 work was implemented separately on 2026-07-17 in `schema/json-schema/staged-pdf-artifacts-v2.schema.json`. The shared validator selects the contract from `schema_version` and validates both schemas under `--schema-only`.

Version 2 adds optional `column_span` and `row_span` properties with effective defaults of `1`, formatted-text `title` regions, `table_title` cells, internal-region and table-title template rules, immutable template review-policy artifacts, application policy evaluations, and human versus system review-event provenance. The Phase 2 parallel migration completed on 2026-07-27 without changing version 1, database, publication, or active-review state.

The schema document is a discriminated union. Every artifact uses the same `$schema` target and selects exactly one closed contract through `artifact_type`. Undeclared properties are rejected.

## Artifact Contracts

| `artifact_type` | Stage | Primary contents |
| --- | --- | --- |
| `source_evidence` | 0 | Immutable source identity, render and OCR policies, and complete page evidence. |
| `block_inventory` | 1 | Page dispositions, bounded material blocks, formatted-text regions, table grids, reviewed block relationships, evidence, confidence, exclusions, and review state. |
| `content_groups` | 2 | Ordered multi-page logical groups, continuation edges, inherited headers, candidates, and group relationships. |
| `structural_template` | 3 | Immutable template version, reuse scope, anchors, block and column rules, boundaries, and regression controls. |
| `template_applications` | 3 | Document-specific template bindings, anchor matches, geometry deltas, mismatches, one-off exceptions, and review state. |
| `review_decisions` | All reviewed stages | Append-only reviewer actions, affected keys, source locations, field changes, and event hash chain. |
| `parity_report` | 7 | Baseline identity, record-level comparison, aggregate counts, rerun controls, blockers, and pass state. |

The existing raw extraction and normalized financial-observation contracts remain separate. They can be referenced through `artifact_ref` values but are not redefined by this schema.

## Common Artifact Envelope

Every document-specific artifact requires:

- `$schema` ending in `staged-pdf-artifacts.schema.json`
- `schema_version: 1`
- one exact `artifact_type`
- stable `artifact_key`
- stable `document_key`
- immutable source PDF SHA-256
- generator name, version, and deterministic configuration SHA-256
- explicit upstream artifact references

Structural templates omit document and source identity because an approved template can be reused. They retain the remaining version and provenance fields.

Artifact files do not contain their own hash. The SHA-256 is calculated after canonical serialization and is recorded by dependent artifacts. This avoids self-referential hashing.

## Key And Path Rules

- Keys contain letters, digits, period, underscore, colon, or hyphen and cannot begin with punctuation.
- Repository paths are relative, cannot begin with a drive or slash, and cannot contain backslashes.
- SHA-256 values are lowercase 64-character hexadecimal strings.
- Template versions use three-part semantic versions such as `1.0.0`.
- Arrays representing sets use `uniqueItems`; stable ordering is still required for deterministic generation.

Candidate block keys are run-scoped. Reviewed block keys become stable document-and-page keys. Schemas preserve the distinction through nullable `candidate_key`.

## Geometry

Page block and anchor geometry uses normalized coordinates from 0 to 1. Render and PDF page boxes use native point or pixel coordinates.

JSON Schema checks numeric ranges. The repository validator separately requires:

- `x0 < x1`
- `y0 < y1`
- valid template column order
- valid minimum and maximum block counts

Polygon geometry is optional and requires at least three normalized points when present.

## Explicit Absence

Fields that affect interpretation are required even when no value exists. They use explicit `null`, not omission.

Examples include:

- unavailable OCR engine, confidence, evidence path, or hash
- absent candidate or table-family key
- unavailable source bounding box
- no exclusion disposition
- no one-off exception
- no prior review event
- missing baseline or shadow parity record
- no discrepancy disposition or decision

This makes omission distinguishable from a reviewed absence and prevents generators from silently dropping fields.

## Review Contract

Reusable review objects contain:

- status: `proposed`, `needs_review`, `approved`, `rejected`, or `superseded`
- stable reason codes
- decision IDs

Review decisions are separate append-only events. Each event records sequence, timestamp, reviewer, action, reason, prior and resulting artifact hashes, previous event hash, event hash, affected keys, source locators, and field-level changes. Stage 1 permits block create, resize, type change, and delete; formatted-text region create, resize, type change, and delete; table-grid redetection, divider movement, row and column split or merge, and cell typing; and relationship link and unlink actions. Automatically detected grids retain the invoking decision ID but use `needs_review` status.

The Stage 1 block vocabulary is `title`, `formatted_text`, `table`, `chart`, `other_visual`, `map`, `table_of_contents`, `header`, `footer`, `page_number`, `divider`, and `signature`. Formatted-text blocks can contain paragraph, bullet-list, and sorted-list regions. Each table requires a `table_grid` with page-normalized outer and internal row and column boundaries plus a complete row-major cell matrix. Cells use `table_header`, `column_label`, `row_label`, `cell`, `subtotal`, or `total`. Non-table blocks require `table_grid: null`.

Row and column boundaries are strictly increasing, their outer values equal the parent table box, and the cell matrix must cover every row-column coordinate exactly once. Moving a divider cannot cross its neighbours. Splitting duplicates each source cell type into both result cells. Merging retains a type only when all source cells at that merged coordinate match; otherwise the result resets to `cell`. Structural changes are rejected when an affected cell is referenced by a relationship, preventing silent endpoint loss.

Block relationships use whole-block, formatted-text region, or table-cell endpoints. Version 1 permits `graph_source_table`, `table_continuation`, and `overview_detail`. Semantic validation requires a whole chart linked to a whole table, whole table fragments on different pages, or a typed `row_label` cell linked to a different whole detail table, respectively.

The schema requires event fields. The validator additionally enforces consecutive sequence numbers and the previous-event hash chain.

## Template Fit Contract

Template applications classify fit as:

- `exact`
- `light_variation`
- `material_variation`
- `one_off`

Material variation cannot have approved review status. It must retain at least one material mismatch.

One-off applications require exact mismatch, nonrecurrence evidence, reuse risk, isolated allowlist key, and positive and negative controls. Exact or light fits cannot retain a material mismatch.

## Cross-Record Semantic Validation

JSON Schema cannot express all repository invariants. `scripts/validate-staged-pdf-artifacts.py` adds:

- source hash and page-count agreement
- existence and SHA-256 integrity of every Stage 0 source, render, thumbnail, embedded-word, and OCR reference
- consecutive source pages
- unique page, block, group, application, decision, and comparison keys
- complete page-to-block accounting
- valid geometry ordering
- continuation and inherited-header endpoints within their group
- consecutive member reading order
- one primary logical-group owner per block
- valid group relationship targets
- valid template anchor references
- valid template application fit and mismatch combinations
- valid review event chain
- exact parity summary counts
- passed-run requirements for deterministic hashes, zero database writes, unchanged snapshot counts, and zero blockers

When several artifact files are validated together, it also checks document and source identity, page agreement, group-to-block references, application-to-group and template references, and parity source identity.

## Validation Commands

Validate the schema itself:

```powershell
& scripts/python.ps1 scripts/validate-staged-pdf-artifacts.py --schema-only
```

Validate artifact files or directories:

```powershell
& scripts/python.ps1 scripts/validate-staged-pdf-artifacts.py <artifact-path> [<artifact-path> ...]
```

Run regression tests:

```powershell
& scripts/python.ps1 scripts/test-staged-pdf-artifact-schemas.py
```

Run Stage 1 write regressions:

```powershell
& scripts/python.ps1 scripts/test-staged-pdf-block-inventory-writes.py
```

Generate and validate the approved Charlottetown Stage 0 source evidence:

```powershell
& scripts/python.ps1 scripts/generate-staged-pdf-source-evidence.py
& scripts/python.ps1 scripts/validate-staged-pdf-artifacts.py data/budget/charlottetown/2026-2027/staged-pdf/v1/stage-0/source-evidence.json
& scripts/python.ps1 scripts/test-staged-pdf-source-evidence.py
```

## Compatibility And Versioning

Version 1 is intentionally closed. Adding an optional property, new enum value, or relaxed rule requires a reviewed schema change and regression coverage. Removing or changing a required field, identifier rule, geometry meaning, or review state requires a new schema version and an explicit artifact migration plan.

Template semantic versions are independent of the artifact schema version. A template change that affects anchors, geometry tolerances, columns, continuation, termination, or negative controls creates a new immutable template version.

No compatibility aliases are defined. Producers must emit the current approved field names.

## Sources

- [Staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md)
- [Charlottetown 2026/2027 shadow pilot](./staged-pdf-inventory-extraction-charlottetown-pilot.md)
- [Staged PDF inventory review UI plan](./staged-pdf-inventory-review-ui-plan.md)
- [Document extraction engineering](./document-extraction-engineering.md)
- [Municipal budget requirements](../budgets/requirements.md)
- `schema/json-schema/staged-pdf-artifacts.schema.json`
- `schema/json-schema/staged-pdf-artifacts-v2.schema.json`
- `scripts/validate-staged-pdf-artifacts.py`
- `scripts/test-staged-pdf-artifact-schemas.py`
- `scripts/test-staged-pdf-artifact-schemas-v2.py`
- `scripts/test-staged-pdf-v2-phase0.py`
- `scripts/generate-staged-pdf-source-evidence.py`
- `scripts/test-staged-pdf-source-evidence.py`
