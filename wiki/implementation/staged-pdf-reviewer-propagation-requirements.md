---
type: implementation
tags:
  - extraction
  - pdf
  - review-ui
  - requirements
  - templates
updated: 2026-07-16
---

This page defines the approved prioritized requirements for propagating reviewed PDF structure, reducing repeated review, and reusing municipal document templates.

# Staged PDF Reviewer Propagation Requirements

## Status And Scope

These requirements are approved for implementation planning. They do not authorize code, schema-file, generated-artifact, database, dependency, or publication changes.

The capability extends the staged PDF reviewer from manual Stage 1 correction toward reviewed structural reuse within one document, across later documents from the same source, and eventually across agenda packages. Source evidence remains immutable, visual structure remains separate from semantic normalization, and material variation remains review-blocking.

## Approved Decisions

- `title` is an allowed internal region of a `formatted_text` block.
- Table cells may optionally declare `column_span` and `row_span`; each omitted value has an effective value of `1`.
- A table may optionally contain one `table_title` cell spanning the complete table width at its top or bottom boundary.
- Structural templates and review policies are independently versioned.
- Review may progress from mandatory review to sampled review and automatic approval.
- Material variation is never eligible for automatic approval.
- Automatic decisions remain append-only, hash-bound, explainable, and reversible through superseding decisions.

## P0: Safe Propagation And Progressive Trust

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| `P0-01` | The reviewer can invoke `Find similar` from a completed structural edit. | Candidate discovery performs no write and reports page, target key, confidence, matching evidence, and mismatch evidence. |
| `P0-02` | Candidate changes are previewed visually. | Current and proposed overlays can be compared, individual candidates can be excluded, and cancellation leaves artifacts unchanged. |
| `P0-03` | Propagation uses an explicit scope. | Supported scopes are selected targets, current document, and future documents covered by an approved source policy. |
| `P0-04` | Every candidate receives a fit classification. | Results are `exact`, `light_variation`, `material_variation`, or `one_off`; material variation cannot be bulk-applied. |
| `P0-05` | Bulk application is atomic. | A stale artifact hash, stale review head, invalid target, or validation failure rejects the complete command without partial publication. |
| `P0-06` | Reviewer rejection becomes negative evidence. | A rejected candidate remains linked to the template and is evaluated as a negative control on later runs. |
| `P0-07` | Propagation is deterministic. | Equal source, template, policy, matcher, configuration, and target selection produce equal canonical structural output except required timestamps. |
| `P0-08` | Propagated structure preserves provenance. | Every block, region, boundary, span, and cell remains linked to exact source pages and coordinates. |
| `P0-09` | Review policy is bound to an immutable template version and scope. | Every policy identifies the exact template hash, matcher hash, source family, document family, and reuse scope. |
| `P0-10` | Policy promotion requires a human decision. | A policy cannot promote itself; the decision records positive examples, negative controls, validation runs, and observed results. |
| `P0-11` | Promotion thresholds are configurable. | Minimum evidence, allowed light variations, sampling rate, and acceptable error thresholds are explicit policy values. |
| `P0-12` | Automatic approval is auditable. | Each automatic decision records the system actor, policy version and hash, template version and hash, matcher configuration, fit, evidence, and affected keys. |
| `P0-13` | Material variation is never automatically approved. | Material mismatch produces `needs_review` or `blocked` under every policy mode. |
| `P0-14` | Light variation is allowlisted. | Only mismatch categories explicitly permitted by the active policy are eligible for sampled or automatic approval. |
| `P0-15` | Failed controls suspend automatic use. | Material mismatch, negative-control failure, sampled rejection, matcher change, source-profile change, or validator failure prevents further automatic approval. |
| `P0-16` | Trust changes preserve history. | Promotion, demotion, suspension, and retirement create superseding policy versions without modifying prior policy artifacts or decisions. |

## P1: Table Repair And Spanning Cells

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| `P1-01` | A reviewed multi-line header repair can be reused. | Equivalent tables receive proposed header boundaries, merged cells, column labels, and cell types derived from target evidence. |
| `P1-02` | Separator recalculation uses visual and word evidence. | Detection considers word boxes, whitespace gutters, rendered rules, and table bounds instead of copying absolute source coordinates. |
| `P1-03` | Separator changes are previewable. | The UI displays current and proposed positions plus displacement and supporting evidence. |
| `P1-04` | Spanning cells preserve complete grid coverage. | Effective row and column spans cover every grid coordinate exactly once without overlap or out-of-range coverage. |
| `P1-05` | Referenced cells are protected. | A structural edit that would invalidate a relationship endpoint is rejected until the relationship is removed or retargeted. |
| `P1-06` | Semantic differences stop structural reuse. | Changed column role, unit, period, entity, hierarchy, aggregation, sign behavior, or total meaning produces material variation. |
| `P1-07` | `column_span` and `row_span` are optional cell properties. | Omitted spans resolve to `1`; explicit spans are positive integers and produce the same behavior as their effective values. |
| `P1-08` | Any table cell may span valid adjacent coordinates. | Rendering, selection, relationship endpoints, split, merge, extraction, and validation use effective span coverage. |
| `P1-09` | `table_title` is an allowed cell type. | Exact title text, evidence, position, effective spans, confidence, and review state are preserved. |
| `P1-10` | A table title spans the complete width. | Its `column_index` is `0` and its effective `column_span` equals the table column count. |
| `P1-11` | A table title is at the top or bottom boundary. | Its effective row coverage begins at row `0` or ends at the final table row. |
| `P1-12` | A table contains zero or one title cell. | Multiple title cells or a partial-width title fail semantic validation. |
| `P1-13` | A wrapped title remains one logical cell. | Multiple physical text lines do not create extra cells unless explicitly split by review. |
| `P1-14` | Title presence does not redefine body columns. | Body column bands and meanings are calculated independently of the title span. |
| `P1-15` | Templates state title expectations. | `required`, `optional`, or `absent` title policy and allowed top or bottom positions are explicit. |
| `P1-16` | Propagation recalculates the title geometry. | Target words and visual evidence determine the target title boundary; source coordinates are not replayed verbatim. |

## P2: Formatted-Text Recalculation

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| `P2-01` | Formatted-text templates record internal structure. | Region type, anchors, relative order, indentation, markers, and geometry tolerances are explicit. |
| `P2-02` | Regions are recalculated from target content. | Target words, line spacing, indentation, typography, and list markers determine proposed geometry. |
| `P2-03` | Required and optional regions are distinguished. | Missing required regions produce material variation; missing optional regions do not create empty boxes. |
| `P2-04` | Region geometry remains valid. | Regions stay inside the parent, retain deterministic reading order, and avoid unapproved overlap. |
| `P2-05` | Region changes are reviewable. | Preview identifies added, removed, resized, reordered, and reclassified regions. |
| `P2-06` | Internal types include `title`, `paragraph`, `bullet_list`, and `sorted_list`. | Schema, generator, validator, writer, UI, templates, and tests accept the four types. |
| `P2-07` | Internal titles retain full provenance. | Stable key, exact text, source geometry, evidence, confidence, and review state are present. |
| `P2-08` | Duplicate title representation is prohibited by default. | The same source geometry cannot be both an internal title and sibling title block without a reviewed relationship. |

## P3: Agenda-Package Template Reuse

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| `P3-01` | A municipal source profile defines reuse boundaries. | Jurisdiction, source family, document family, positive examples, negative controls, and reuse scope are recorded. |
| `P3-02` | Template structure is hierarchical. | Package grammar, embedded-document boundaries, page sequences, page templates, blocks, and internal structures remain distinguishable. |
| `P3-03` | Embedded-document detection reports boundary evidence. | Start and end anchors, page sequence, page count, family match, confidence, and unresolved evidence are visible. |
| `P3-04` | Single-page and multi-page documents are supported. | The package is not forced into one flat template and source page order is preserved. |
| `P3-05` | Structural templates are immutable and versioned. | Anchor, tolerance, sequence, column, continuation, termination, or negative-control changes create a new version. |
| `P3-06` | Later packages use the active policy. | Applications become `needs_review`, sampled review, automatically approved, or blocked according to exact policy evaluation. |
| `P3-07` | Material package variation blocks reuse. | Missing required anchors, changed boundaries, unexpected material blocks, or changed structural meaning cannot be automatically applied. |
| `P3-08` | Broader promotion requires broader controls. | Promotion beyond the observed source scope requires positive and nearest-negative controls from the proposed scope. |

## P4: Migration And QA

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| `P4-01` | Version 1 remains immutable and readable. | Version 2 migration creates parallel artifacts and never rewrites version 1 artifacts or review chains. |
| `P4-02` | Omitted and explicit unit spans are equivalent. | Validators, writers, generators, UI, extraction, and canonical comparison resolve omitted spans as `1`. |
| `P4-03` | Migration does not infer new structure. | Internal titles, table titles, and non-unit spans are proposed only from evidence or review, not from a mechanical version migration. |
| `P4-04` | Automatic decisions resolve exact dependencies. | Template, policy, matcher, source, prior artifact, result artifact, and review-event hashes are complete. |
| `P4-05` | Clean reruns are deterministic. | Candidate sets, effective spans, policy outcomes, and canonical structural artifacts match across two clean runs. |
| `P4-06` | The pilot remains memory-bounded. | The 154-page pilot is processed incrementally without retaining all rendered pages in memory. |
| `P4-07` | Regressions cover positive and negative controls. | Schema, migration, span coverage, title placement, relationship, stale-hash, policy, suspension, and UI tests pass. |
| `P4-08` | Shadow work cannot publish. | Version 2 planning and validation produce zero database writes and no publication-snapshot changes. |

## Completion Gate

The capability is complete only when all applicable P0 through P4 requirements pass, every automatic decision is reproducible from exact immutable inputs, material mismatches remain blocked, and baseline comparison confirms no source content was lost or duplicated.

## Sources

- [Staged PDF artifact version 2 schema design](./staged-pdf-artifact-v2-schema-design.md)
- [Staged PDF artifact version 2 implementation plan](./staged-pdf-artifact-v2-implementation-plan.md)
- [Staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md)
- [Staged PDF inventory review UI plan](./staged-pdf-inventory-review-ui-plan.md)
- [Agenda package ingestion contract](./agenda-package-ingestion-contract.md)

