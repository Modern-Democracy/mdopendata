---
type: implementation
tags:
  - extraction
  - pdf
  - architecture
  - review-ui
  - budget
updated: 2026-07-15
---

This page specifies a review-first PDF inventory, logical-content assembly, template, extraction, and parity-validation workflow for predictable municipal document ingestion.

# Staged PDF Inventory And Extraction Architecture

## Status And Decision

This is the approved architecture specification for a future implementation. It does not authorize code, schema, database, dependency, or publication changes.

Version 1 must run in shadow mode against `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`. It must generate new artifacts beside, not over, the current artifacts and must not write to PostgreSQL or change a publication snapshot.

The workflow changes the primary unit of structural review from a page-level table candidate to a bounded page block assembled into a reviewed logical content group. Raw row and cell extraction begins only after the relevant inventory and grouping decisions are approved.

## Problem

The current budget workflow already preserves raw evidence, profiles every page, records continuation candidates, creates reviewed sections, builds deterministic manifests, validates provenance, reconciles statements, and imports transactionally. These controls remain required.

The remaining unpredictability comes from the order and granularity of work:

- text or OCR heuristics classify content before page structure is reviewed
- one page-level family cannot represent multiple unrelated blocks on one page
- continuation detection depends on both pages first being classified correctly
- source headers, continuation rows, and logical table boundaries are repaired later in document-specific mappings
- visual layout decisions, semantic mappings, and normalization exceptions are distributed across artifacts and scripts
- human review can repeat at row level when one earlier structural decision would have resolved the entire group

The new architecture moves reviewed structure ahead of raw financial extraction while retaining the current downstream source-fidelity and publication gates.

## Goals

- Inventory every page and every material content block before financial row extraction.
- Represent one logical table, schedule, profile, or narrative section across any number of pages and page blocks.
- Permit multiple logical content groups to use different regions of the same page.
- Reuse reviewed structural templates only where source structures are materially equivalent.
- Separate visual structure, raw extraction, and semantic normalization into independent approval layers.
- Reduce human work to new patterns, material mismatches, low-confidence evidence, and failed controls.
- Preserve exact source provenance and deterministic reruns.
- Compare shadow output with the current high-confidence published dataset before replacement is considered.

## Non-Goals

- Automatically infer cross-municipality semantic equivalence.
- Treat visual similarity as proof of entity, period, unit, hierarchy, or aggregation meaning.
- Replace the current budget schema, normalized manifest, importer, or publication gates in version 1.
- Mutate current raw artifacts or published observations during the pilot.
- Build a public correction workflow or authentication model.
- Generalize the first template library beyond tested source families.

## Core Concepts

| Concept | Contract |
| --- | --- |
| Source document | Immutable PDF identity defined by source path, SHA-256 hash, page count, and document metadata. |
| Source page | Physical PDF page with stable page number, dimensions, rotation, render, text layer, and OCR evidence. |
| Page block | Reviewed rectangular or polygonal page region containing one structural unit such as a table fragment, narrative, chart, profile, header, footer, divider, or signature. |
| Logical content group | Ordered collection of one or more page blocks treated as one extractable or explicitly excluded source unit. |
| Structural template | Versioned rules for anchors, regions, reading order, column bands, headers, continuation behavior, termination, and negative controls. |
| Template application | Document-specific binding between a template version and actual source pages, blocks, anchors, and tolerances. |
| Mapping package | Reviewed semantic assignments for entity, period, unit, statement scope, row roles, value states, hierarchy, and reconciliations. |
| Review decision | Append-only approval, rejection, correction, or supersession record tied to artifact hashes and exact source locations. |
| Baseline | Frozen export of current approved artifacts and published observations used for shadow parity comparison. |

Structural templates must not contain normalized category assignments or unsupported accounting semantics. Mapping packages must not alter raw block, row, cell, text, or coordinate evidence.

## Architecture Flow

```text
source registration and render
  -> page evidence inventory
  -> block inventory
  -> logical content grouping
  -> structural template review
  -> raw row and cell extraction
  -> structural and source-fidelity QA
  -> semantic mapping and normalization
  -> baseline comparison and reconciliation
  -> existing controlled import and publication gates
```

Each arrow is a stage boundary. A downstream stage reads only an approved upstream artifact hash. Re-running an upstream stage with a different canonical result invalidates dependent approvals.

## Stage 0: Source Registration And Evidence

### Inputs

- source PDF
- municipality and document identity
- expected local path or source URI

### Work

- calculate SHA-256 and page count
- record page dimensions, rotation, media and crop boxes, encryption, and embedded-text availability
- render a canonical page image and thumbnail for every page
- extract embedded words with coordinates where available
- run OCR only under a recorded OCR policy and preserve OCR engine, version, rotation, resolution, confidence, text, and coordinates
- retain embedded and OCR evidence independently when both exist

### Output And Gate

`source-manifest.json` and `page-evidence.json` are complete only when every PDF page has a render and an evidence disposition. A missing render, unreadable page, hash mismatch, or unexplained page-count change blocks Stage 1.

## Stage 1: Page And Block Inventory

### Block Requirements

Each page can contain zero or more material blocks. Candidate detection may propose blocks, but review operates on the rendered page.

Every reviewed block records:

- stable block key and physical page key
- normalized geometry in page coordinates from 0 to 1
- reading-order position
- block type and optional table-family candidate
- text source: embedded, OCR, visual-only, or mixed
- detected anchors and confidence evidence
- whether the block contains financial candidates
- review state and exact review reasons
- exclusion disposition when it is intentionally not extracted

The Stage 1 vocabulary distinguishes page-content titles and formatted text from repeating document-level headers and footers. Internal regions provide paragraph, list, header, label, cell, subtotal, and total geometry without flattening the parent block. Header, footer, and page-number blocks may be retained as layout evidence without becoming logical content.

Reviewed block relationships provide pre-grouping evidence for graph-to-source-table links, cross-page table continuations, and overview-row-to-detail-table links. An endpoint references either a whole block or an internal region; relationships do not imply normalized semantic equivalence.

### Stable Identity

Candidate block identifiers are run-scoped. On first approval, reviewed blocks receive document-and-page-scoped keys such as `ctown-budget-2026-2027:p087:b003`, ordered by reviewed reading order. Later runs match approved blocks by page, anchor fingerprint, overlap, and text evidence. Existing keys are never renumbered; unmatched candidates or missing approved blocks create review records.

### Output And Gate

`block-inventory.json` must account for every detected financial region and every reviewer-added region. Stage 2 is blocked by overlapping financial blocks without a reviewed relationship, unbounded financial content, or an unexplained high-confidence detector omission.

## Stage 2: Logical Content Groups

A logical group can contain blocks from one page, several pages, or only part of a page. Page adjacency is supporting evidence, not sufficient proof of continuation.

Each group records:

- stable group key, title, candidate family, and disposition
- ordered member block keys
- page range and per-block role such as `header`, `body`, `continuation`, `footnote`, or `signature`
- continuation edges and their evidence
- inherited headers and column-role source block
- reporting-entity and period candidates without approving them
- relationship to summary, detail, duplicate, backing table, profile, or divider groups
- required human-review state

Continuation evidence can include matching column geometry, repeated or inherited headers, uninterrupted row hierarchy, same title or entity anchor, prior-page open boundary, next-page completion, and compatible totals. A group must stop when entity, column meaning, unit, fiscal role, hierarchy, source authority, or table purpose changes.

### Output And Gate

`content-groups.json` is approved only when every financial block belongs to exactly one primary group or has an explicit reviewed exclusion. Shared header or footnote evidence may be referenced by multiple groups but cannot create duplicate financial ownership.

## Stage 3: Structural Templates

### Template Contents

A structural template contains:

- template key, immutable version, source family, and reuse scope
- required and optional text or visual anchors
- normalized anchor regions and reviewed geometric tolerances
- allowed block types, count ranges, and reading order
- table column bands and physical header patterns
- expected repeated, inherited, or absent header behavior
- row-boundary, continuation, and group-termination rules
- footer, page number, decoration, chart, and narrative negative controls
- supported OCR or embedded-text modes
- positive and nearest negative regression controls

### Fit Classification

Light variation can include page scaling, font changes, minor shifts within reviewed tolerances, optional decorative elements, or omission of an explicitly optional repeated header.

Material variation includes changed column roles, units, periods, entities, hierarchy, aggregation roles, dash or sign semantics, totals, source authority, extra financial blocks, missing required anchors, or changed group boundaries. Material variation produces `template_mismatch` and blocks extraction until a new template version or document-specific application is reviewed.

Template reuse levels are exact-document replay, same-edition repeated family, cross-edition family, and cross-municipality family. Promotion to a broader level requires positive and negative controls from that level. The Charlottetown pilot cannot establish cross-municipality support.

### Output And Gate

`template-applications.json` binds approved groups to immutable template versions. Groups without a template can use an explicit reviewed one-off application, but the decision must satisfy the existing one-off exception gate.

## Stage 4: Raw Extraction

Raw extraction runs against approved group geometry and template applications rather than independent page guesses.

The extractor must:

- preserve every physical text or OCR fragment before reconstruction
- preserve raw labels, display text, whitespace evidence, coordinates, row order, signs, dashes, blanks, and parenthesized values
- link logical rows and cells to all contributing physical fragments
- support header inheritance without copying a header into raw evidence
- support rows reconstructed across lines or pages without mutating physical rows
- distinguish detected numeric tokens from accepted financial cells
- produce deterministic keys and canonical ordering
- record source, inventory, template, extractor, and configuration hashes

`raw-groups/`, `raw-rows.json`, `raw-cells.json`, and `raw-extraction-report.json` remain separate from normalized observations.

## Stage 5: Structural And Source-Fidelity QA

Before semantic mapping, QA must verify:

- every approved group was extracted or explicitly excluded
- expected columns and required anchors are present
- physical fragments have complete page and coordinate provenance
- continuation boundaries preserve row order and inherited headers
- no source fragment is silently lost or assigned to conflicting financial cells
- narrative years, quantities, page numbers, chart labels, and profile dimensions remain negative controls where applicable
- row, cell, token, value-state, and exclusion counts are deterministic
- two clean reruns produce canonically identical artifacts excluding recorded run timestamps

Failures are classified as source, evidence acquisition, inventory, grouping, template fit, raw extraction, or QA defects. They must not be deferred silently to normalization.

## Stage 6: Semantic Mapping And Normalization

The existing per-value financial-observation contract remains authoritative. A reviewed mapping package assigns statement scope, reporting entity, organization unit, document period, amount type, unit, hierarchy, aggregation role, value state, and reconciliation participation.

Mapping packages can target structural template fields and stable logical row identities. They cannot normalize an unknown template, unresolved group, missing source link, unsupported unit, or ambiguous value state. Raw-label mappings are contextual to statement and group identity; label text alone is never a global key.

## Stage 7: Baseline Comparison And Existing Import Gates

The pilot captures three comparison layers before running the shadow pipeline:

1. Current reviewed raw and normalization artifacts.
2. Current database natural keys, values, units, periods, entities, statement scope, and source links for the target document.
3. Current published snapshot membership and reconciliations.

Parity is compared by stable semantic and provenance keys, not database surrogate IDs. Candidate, row, or block counts may differ only when an explicit equivalence record proves that the same source content is represented more accurately without loss or duplication.

The source PDF remains authoritative. A baseline disagreement is not automatically a new-pipeline failure; it is a blocking review item until source inspection determines which representation is correct.

## Review UI Contract

Version 1 should extend the existing local web runtime without adding a public route or new dependency unless separately approved.

The internal interface requires:

- document queue with source hash, stage, blockers, and review coverage
- thumbnail rail with page, block, group, and mismatch indicators
- zoomable page canvas with selectable overlays and coordinate readout
- block inspector for type, bounds, reading order, evidence source, confidence, and disposition
- group timeline showing member blocks, continuation edges, inherited headers, and stop boundaries
- template panel showing matched and missing anchors, geometry deltas, negative controls, and reuse scope
- raw preview aligned beside the source image without approving normalization
- baseline-diff panel for missing, extra, changed, and provenance-shifted records
- keyboard-accessible split, merge, resize, reorder, link, unlink, approve, reject, and supersede actions

Every write creates an append-only review event containing reviewer identity, timestamp, action, reason, prior artifact hash, resulting artifact hash, and exact affected keys. Approval applies to an artifact hash, not a mutable filename.

## Runtime And Storage Constraints

- Process and render pages incrementally; do not retain the entire 154-page bitmap corpus in memory.
- Generate canonical renders once per document hash and lazy thumbnails for the UI.
- Store versioned JSON artifacts under a document run directory until a database persistence design is separately approved.
- Use the repository Python runtime through `scripts/python.ps1`.
- Keep structural template code independent of municipality and fiscal period where the tested structure permits.
- Keep document-specific page bindings, aliases, semantics, and exceptions in reviewed packages.
- Fail on content conflicts instead of overwriting approved artifacts.

## Pilot Validation

The [Charlottetown 2026/2027 shadow pilot](./staged-pdf-inventory-extraction-charlottetown-pilot.md) defines the frozen source and publication baselines, representative PDF controls, acceptance criteria, and implementation sequence. Separating the pilot keeps this architecture reusable while preventing current Charlottetown counts from becoming universal template assumptions.

The [staged PDF artifact JSON Schemas](./staged-pdf-artifact-json-schemas.md) implement the version 1 contracts for source evidence, block inventory, logical groups, structural templates, template applications, append-only review decisions, and parity reports.

## Stop Conditions

Stop implementation or extraction when:

- the PDF hash, page count, render, or source authority differs from the registered source
- a page contains unbounded or overlapping financial regions
- a template has missing required anchors or material variation
- continuation evidence conflicts with entity, period, column, unit, hierarchy, or total evidence
- a physical fragment cannot be traced to a reviewed block, row, and cell
- a baseline difference lacks exact source evidence and a review disposition
- a rerun changes canonical artifacts without an input or version change
- a shadow process attempts a database or publication write

## Sources

- [Document extraction engineering](./document-extraction-engineering.md)
- [Charlottetown 2026/2027 shadow pilot](./staged-pdf-inventory-extraction-charlottetown-pilot.md)
- [Staged PDF artifact JSON Schemas](./staged-pdf-artifact-json-schemas.md)
- [Municipal budget requirements](../budgets/requirements.md)
- [Budget ingestion refactor tracker](../budgets/budget-ingestion-refactor-tracker.md)
- [Charlottetown three-year budget source profile](../charlottetown/sources/budget-three-year-source-profile.md)
- [2026/2027 normalization status](../budgets/2026-normalization-status.md)
- [Budget content and observation redesign status](../budgets/content-and-observation-redesign-status.md)
- `docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf`, PDF pages 10, 18-23, 28-33, 87-92, 105, 110-112, 149, and 151-153
- `data/budget/charlottetown/2026-2027/`
- `scripts/extract-charlottetown-budget-raw-rows.py`
