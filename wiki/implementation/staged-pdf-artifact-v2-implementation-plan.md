---
type: implementation
tags:
  - extraction
  - pdf
  - implementation-plan
  - review-ui
  - templates
updated: 2026-07-27
---

This page defines the approved implementation sequence for version 2 staged PDF artifacts, structural propagation, and policy-governed review reduction.

# Staged PDF Artifact Version 2 Implementation Plan

## Status And Boundary

The requirements and schema design are approved. This plan does not itself authorize code, generated-artifact, dependency, database, deployment, or publication changes. Each implementation phase remains separately gated.

Version 1 stays operational and immutable while version 2 is built and validated in parallel. The pilot remains the Charlottetown 2026/2027 financial plan, and all work remains shadow-only until parity and approval gates pass.

## Implementation Status

- Phase 0 completed on 2026-07-17 with frozen version 1 hashes, inventory counts, review head, and positive and negative control catalogues in `data/budget/charlottetown/2026-2027/staged-pdf/v2/phase-0/baseline-and-controls.json`.
- Phase 1 completed on 2026-07-17 with the parallel version 2 schema, version-aware validation, expanded span coverage, title constraints, review-policy contracts, application-policy provenance, and automated-decision actor rules.
- Phase 2 completed on 2026-07-27. The deterministic migration command generated a parallel source-evidence artifact, block inventory, review-decision chain, and migration report under `data/budget/charlottetown/2026-2027/staged-pdf/v2/`.
- The migration retained 154 source pages, 442 block records, one relationship, all omitted unit spans, stable record keys, and all 104 historical event hashes. It appended decision `ctown-budget-2026-2027:decision:000105` with action `migrate_schema`.
- The pilot contains no structural-template artifacts, so zero `review_required` policies were eligible or seeded. No automatic-approval policy was created.
- A clean rerun produced zero writes and four byte-identical outputs. Version 1 hashes remained frozen, the three-artifact version 2 set validated, and database and publication write counts remained zero.
- Phase 3 completed on 2026-07-27. Parallel version 2 generator and writer entry points resolve omitted spans as `1`, propose evidence-supported formatted-text and table titles, support logical-cell merge, split, and explicit spans, protect relationship endpoints, and append valid version 2 review events. The frozen version 1 generator and writer remain byte-identical.
- The reviewer retains version 1 as its default workspace. Explicit `PDF_INVENTORY_REVIEW_SCHEMA_VERSION=2` selection enables the parallel version 2 source and block artifacts, effective-span rendering, table-title choices, numeric span controls, logical-cell split and merge, and span-aware selection.
- Phase 4 completed on 2026-07-27. Approved table and formatted-text blocks can produce deterministic, read-only current-document candidate previews with exact, light, material, and one-off classifications. Selected eligible candidates apply atomically; reviewer rejections append document-scoped negative controls to the existing review chain.
- Phase 5 completed on 2026-07-27. Human-approved structures can be promoted into immutable document-scoped templates with immutable review policies, deterministic sampling, fail-closed automation gates, suspension, and exact audit provenance.
- Phase 6 is in progress. The profile and preview contracts, deterministic embedded-document classifier, exact page-accounting controls, and read-only reviewer preview are implemented. Promotion of a real municipal-source profile remains blocked until exact approved structural-template and review-policy references plus positive and nearest-negative agenda-package controls are available.

## Phase 0: Freeze Baseline And Controls

### Work

- record version 1 schema, Stage 0, Stage 1, review-head, generator, writer, and validator hashes
- preserve the current 154-page source identity and representative controls
- inventory existing table cells, regions, relationships, and review decisions
- define positive controls for omitted spans, explicit unit spans, horizontal spans, vertical spans, corner spans, top titles, and bottom titles
- define negative controls for overlap, gap, out-of-range span, duplicate title, partial-width title, material mismatch, and policy drift

### Gate

Baseline counts, hashes, and controls are complete before a version 2 schema or artifact is generated.

## Phase 1: Version 2 Schema And Validator

### Work

- add the version 2 discriminated-union schema beside version 1
- add optional `column_span` and `row_span` with default annotations
- add `title`, `table_title`, template region rules, and table-title policy
- add `template_review_policy`, application policy evaluation, and review-event actor and decision basis
- update component and cross-artifact validators for effective spans, expanded coverage, policy eligibility, and exact references
- retain version-aware validation for version 1

### Gate

Schema self-validation and positive, negative, conditional, and cross-artifact regressions pass for both versions. Version 1 fixtures remain byte-identical.

## Phase 2: Parallel Migration

### Status

Completed on 2026-07-27 by `scripts/migrate-staged-pdf-artifacts-v1-to-v2.py`. The command requires an explicit ISO 8601 migration timestamp so identical inputs and arguments serialize identically.

### Work

- implement a deterministic version 1 to version 2 migration command through `scripts/python.ps1`
- write version 2 artifacts to a parallel directory
- preserve omitted unit spans and stable keys
- add exact schema versions to artifact references
- create append-only migration decisions linking prior and resulting hashes
- seed `review_required` policies without promoting automatic approval

### Gate

Two clean migrations are canonically identical except required timestamps. Version 1 files are unchanged, version 2 validates as a set, relationships resolve, and database and publication write counts remain zero.

Gate passed. `scripts/test-staged-pdf-artifact-v2-migration.py` covers frozen input hashes, deterministic canonical output, key and span preservation, historical review-chain preservation, exact output hashes, set validation, and atomic conflict rejection. The generated evidence is recorded in `data/budget/charlottetown/2026-2027/staged-pdf/v2/phase-2/migration-report.json`.

## Phase 3: Stage 1 Span And Title Editing

### Status

Completed on 2026-07-27. No generated version 2 pilot artifact was replaced: generation was exercised in temporary clean-run controls, and writer mutations were exercised against temporary copies.

### Work

- update grid readers to resolve effective spans
- update generators to propose internal titles and evidence-supported table titles conservatively
- add logical-cell merge, split, and span commands
- protect relationship endpoints during span mutations
- render spanning cells using their effective right and bottom boundaries
- add `title` and `table_title` controls, selection behavior, keyboard behavior, and accessible labels
- show omitted spans as effective `1` without forcing serialization

### Gate

Create, reclassify, merge, split, resize, relationship, stale-hash, and audit tests pass. Browser tests cover horizontal, vertical, and two-dimensional spans plus top and bottom titles at desktop and narrow layouts.

Gate passed. Version 1 generator and writer hashes and regressions remain valid. The parallel version 2 entry points are `scripts/generate-staged-pdf-block-inventory-v2.py` and `scripts/update-staged-pdf-block-inventory-v2.py`. Version 2 tests cover omitted and explicit unit spans, horizontal and two-dimensional spans, logical merge and split round trips, top and bottom table titles, formatted-text titles, relationship protection, append-only audit events, and the migrated 105-event pilot review chain. The 154-page version 2 generator reproduced byte-identically on a clean rerun. Static, smoke, desktop browser, and 700-pixel browser checks passed with zero console warnings, errors, or horizontal overflow.

## Phase 4: Document-Scoped Structural Propagation

### Status

Completed on 2026-07-27. Document-scoped patterns remain ephemeral and hash-bound; no structural-template or policy artifact is promoted before Phase 5.

### Work

- add `Find similar` for reviewed table-grid and formatted-text structures
- calculate target structure from target evidence and reviewed anchors
- present candidate fit, evidence, mismatches, and before-after overlays
- support selection and atomic application within the current document
- retain rejected candidates as negative controls

### Gate

No preview writes occur. Atomic apply, cancellation, stale-hash rejection, deterministic rerun, negative-control exclusion, material-mismatch blocking, and exact affected-key audit checks pass.

Gate passed. The matcher processes target evidence page by page, recalculates target table grids and formatted-text regions, reports matching and mismatch evidence, and blocks material candidates. Pilot controls find one eligible repeated table pattern from page 18 and retain 75 material controls. Regression tests cover byte-identical previews, zero preview writes, atomic application, stale review-head rejection, exact audit keys, and persisted rejection as a later `one_off` negative control. Server smoke coverage verifies the live version 2 preview endpoint leaves both artifact hashes unchanged.

## Phase 5: Structural Templates And Review Policies

### Status

Completed on 2026-07-27. Phase 5 remains restricted to the current document; municipal-source and agenda-package reuse remains Phase 6 work.

### Work

- promote reviewed structures into immutable template versions
- implement immutable policy artifacts and exact registry references
- evaluate `review_required`, `sample_review`, and `auto_approve`
- record human promotion decisions and system automatic decisions
- suspend automation on configured drift or control failures
- expose policy evidence, current mode, eligible fits, sampling, and suspension state in the UI

### Gate

No template self-promotes. Material variation never auto-approves. Sample selection is deterministic. Every automatic approval resolves exact source, template, policy, matcher, prior, result, and event hashes. Suspension prevents subsequent automatic approvals.

Gate passed. Human actions create immutable, semantic-versioned `structural_template` and `template_review_policy` artifacts bound to the recomputed source-pattern hash and exact upstream artifact hashes. Policies begin with `review_required`; `sample_review` and `auto_approve` fail closed until schema-validated positive, negative, reviewed-application, precision, and false-approval gates pass. Sampling is deterministic from the policy hash and target key. Material, non-allowlisted light, negative-control, matcher-drift, sample-rejection, and suspended-policy conditions block automatic application. Automatic writes recompute the preview and append a system-actor `auto_approve` event containing the exact policy and automation context. Isolated tests cover immutability, promotion gates, deterministic sampling, material blocking, suspension supersession, runtime sample-rejection suspension, and automatic audit hashes; server smoke tests confirm the canonical registry remains empty until a reviewer promotes a pattern. Desktop and 700-pixel browser checks show the policy panel, one eligible pilot candidate, disabled write controls in read-only mode, zero horizontal overflow, and zero console warnings or errors.

## Phase 6: Agenda-Package Reuse

### Status

In progress on 2026-07-27. `schema/json-schema/agenda-package-reuse-profile.schema.json` separates immutable municipal-source scope, package grammar, document-template boundaries, exact structural-template and review-policy references, controls, and approval. `schema/json-schema/agenda-package-reuse-preview.schema.json` records ordered document matches, page roles, boundary evidence, fit, policy outcomes, unknown pages, conflicts, and exact coverage.

`scripts/preview-agenda-package-reuse.py` is deterministic and read-only. It requires exact jurisdiction, source-family, and document-family scope; segments documents from approved start anchors; checks continuation and end anchors, page limits, first-document rules, and allowed transitions; evaluates review policies; and reports every package page exactly once as assigned, unknown, or conflicting. The ingestion UI exposes this through `POST /api/document-ingestion/packages/{packageKey}/reuse-preview` only when `AGENDA_PACKAGE_REUSE_PROFILE` names a repository profile. The endpoint does not change classifications, assemblies, extraction records, databases, or publication state.

No canonical municipal-source profile has been created. The Phase 5 registry contains no promoted agenda-package structural template or policy, so inventing exact references or approving a source profile would violate the Phase 5 and Phase 6 gates. Existing package rows without explicit `metadata.source_family` fail closed; new Charlottetown package registrations record `charlottetown-council`.

### Work

- bind templates to municipal source and document-family profiles
- detect embedded-document start and end boundaries
- represent package grammar, document sequence, page templates, blocks, and internal structures separately
- apply approved policies to later packages from the same source
- report unknown and material patterns rather than forcing template fit

### Gate

Single-page and multi-page positive controls are detected with exact source order. Nearest-negative documents remain unmatched or blocked. No package page is silently omitted or assigned to conflicting embedded documents.

The isolated synthetic gate passes. Remaining gate work is to promote exact agenda-package structures and policies, create and approve the Charlottetown source profile from reviewed real packages, backfill explicit source-family metadata where authorized, and execute the same controls against the representative single-page and multi-page package corpus.

## Phase 7: Parity And Handoff

### Work

- compare version 2 structure and extracted source coverage with the frozen version 1 and published baselines
- classify missing, extra, changed, and provenance-shifted records
- verify deterministic clean reruns and memory-bounded processing
- obtain explicit approval before changing the active review workspace or downstream extraction input

### Gate

Every discrepancy has exact source evidence and a disposition. No source fragment is lost or duplicated. Database and publication outputs remain unchanged until a later explicitly approved transition.

## Implementation Order By File

1. Version 2 schema and schema tests.
2. Semantic and cross-artifact validator.
3. Migration command and migration tests.
4. Stage 1 generator and writer effective-span support.
5. Review UI grid model, controls, rendering, and smoke tests.
6. Template generation and application artifacts.
7. Review-policy evaluator and audit events.
8. Document-scoped propagation.
9. Agenda-package source profiles and reuse.
10. Parity reports and active-workspace transition review.

## QA Matrix

| Area | Discriminating checks |
| --- | --- |
| Defaults | Omitted span and explicit `1` produce equal effective coverage and rendering. |
| Coverage | Every coordinate is covered exactly once; overlap, gap, and overflow fixtures fail. |
| Titles | Top and bottom titles pass; partial-width, internal, and duplicate titles fail. |
| Mutation | Merge and split round-trip geometry, text order, evidence, and relationship protection. |
| Templates | Exact and allowed light variation pass; material and negative controls block. |
| Policies | Human promotion, deterministic sampling, automatic audit, suspension, and supersession pass. |
| Migration | Version 1 bytes remain unchanged and two version 2 runs are canonically equal. |
| Runtime | The 154-page pilot remains incrementally loaded and local-review gates remain intact. |
| Safety | Stale writes fail atomically; database and publication write counts remain zero. |

## Stop Conditions

Stop the active phase when:

- version 1 artifacts or review history would be rewritten
- effective span coverage is ambiguous, incomplete, overlapping, or out of range
- a relationship endpoint cannot be preserved or explicitly migrated
- automatic approval lacks an exact approved policy or immutable dependency hash
- a negative control or sampled review indicates policy drift
- package boundaries conflict with source order or document identity
- a clean rerun changes canonical output without an input or version change
- any shadow phase attempts a database or publication write

## Sources

- [Staged PDF reviewer propagation requirements](./staged-pdf-reviewer-propagation-requirements.md)
- [Staged PDF artifact version 2 schema design](./staged-pdf-artifact-v2-schema-design.md)
- [Staged PDF inventory review UI plan](./staged-pdf-inventory-review-ui-plan.md)
- [Staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md)
- [Agenda package ingestion contract](./agenda-package-ingestion-contract.md)
