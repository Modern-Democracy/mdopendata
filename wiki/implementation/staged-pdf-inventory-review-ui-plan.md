---
type: implementation
tags:
  - extraction
  - pdf
  - review-ui
  - architecture
  - charlottetown
updated: 2026-07-27
---

This page defines the local-only inventory-review UI implementation plan for the active staged PDF version 2 schema and frozen version 1 rollback.

# Staged PDF Inventory Review UI Plan

## Implementation Status

The read-only Stage 0 evidence slice and editable Stage 1 block slice are complete. They require `PDF_INVENTORY_REVIEW_ENABLED=1`, `PDF_INVENTORY_REVIEW_WRITE_ENABLED=1`, a loopback bind, and `DEMO_MODE=false`.

```powershell
./scripts/start-staged-pdf-review.ps1
```

Version 2 is the default. Select the frozen version 1 rollback workspace explicitly:

```powershell
./scripts/start-staged-pdf-review.ps1 -SchemaVersion 1
```

The launcher binds port 3217 to `127.0.0.1`, enables the Stage 1 command adapter, and runs the server in the foreground until Ctrl+C. The canonical Python validator validates Stage 0 and Stage 1 together before either artifact is cached; every requested Stage 0 evidence asset is re-hashed before it is returned.

## Decision

Implement the UI as an internal module of the existing Node HTTP service, disabled by default and unavailable in demo mode. Stage 0 remains immutable. Stage 1 mutations are applied only by the canonical Python writer and validator.

Do not add a database table, public route, authentication model, package dependency, or publication behavior in this workstream.

## Runtime Boundary

| Concern | Owner |
| --- | --- |
| Static UI shell and browser state | Existing `web/public` runtime |
| Local artifact discovery and safe asset reads | Existing `web/server.js` runtime |
| Schema and cross-artifact validation | `scripts/validate-staged-pdf-artifacts.py` |
| Canonical JSON serialization and atomic artifact replacement | New repository Python command invoked through the canonical runtime |
| Append-only review event construction and hash chain | New repository Python command |
| Database and publication | Out of scope |

The module is available only when `PDF_INVENTORY_REVIEW_ENABLED=1`, `DEMO_MODE` is false, and the server is bound to loopback. Write endpoints additionally require `PDF_INVENTORY_REVIEW_WRITE_ENABLED=1` and an explicit validated Python-command adapter.

The deployed demonstration must return `404` for all review routes even if review artifacts exist in the repository.

## Planned Files

| File | Responsibility |
| --- | --- |
| `web/public/pdf-inventory-review/index.html` | Local review page shell. |
| `web/public/pdf-inventory-review/app.js` | State, API calls, keyboard commands, and rendering. |
| `web/public/pdf-inventory-review/styles.css` | Accessible three-pane layout and overlays. |
| `web/server.js` | Feature gates, allowlisted read API, and Stage 1 command adapter. |
| `scripts/update-staged-pdf-block-inventory.py` | Preserve the frozen version 1 mutation workflow. |
| `scripts/update-staged-pdf-block-inventory-v2.py` | Validate a version 2 Stage 1 mutation, append its review event, and atomically publish both version 2 artifacts. |
| `scripts/test-staged-pdf-block-inventory-writes.py` | Create, resize, reclassify, delete, audit, and stale-hash regressions. |
| `scripts/smoke-staged-pdf-review-ui.mjs` | Disabled-route, safe-read, traversal, evidence-integrity, and API-contract smoke checks. |

The first slice created the static UI, read endpoints, and smoke tests. The second slice adds the Stage 1 writer and mutation controls.

## Artifact Workspace

The pilot workspace is:

```text
data/budget/charlottetown/2026-2027/staged-pdf/v1/
  stage-0/
    source-evidence.json
    renders/
    thumbnails/
    embedded-words/
    ocr-words/
  stage-1/
    block-inventory.json
  stage-2/
    content-groups.json
  stage-3/
    template-applications.json
  review/
    review-decisions.json
  parity/
    parity-report.json
```

Structural templates remain in a separate versioned template registry because they can apply to more than one document. The document manifest resolves all artifacts by exact `artifact_key`, source SHA-256, and artifact SHA-256.

## Read API

All responses use `Cache-Control: no-store`. Asset requests resolve only repository-relative paths already recorded in a validated artifact. Arbitrary filesystem paths are rejected.

| Method and path | Result |
| --- | --- |
| `GET /internal/pdf-inventory-review` | Static review shell when locally enabled. |
| `GET /api/internal/pdf-inventory-review/documents` | Allowlisted workspaces, artifact coverage, stages, blockers, and hashes. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/artifacts` | Validated artifact summaries and dependency graph. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/pages` | Page evidence with inventory and group summaries. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/pages/:pageNumber` | Page, blocks, group memberships, template matches, and decisions. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/assets/:assetType/:pageNumber` | Recorded render, thumbnail, embedded-word, or OCR evidence asset. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/groups/:groupKey` | Group members, continuation edges, inherited headers, relationships, and review state. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/templates/:applicationKey` | Template application, anchors, deltas, mismatches, and exceptions. |
| `GET /api/internal/pdf-inventory-review/documents/:documentKey/parity` | Parity counts, records, blockers, and rerun controls. |

The API returns `409` when artifact dependencies disagree on source or upstream hashes. It does not merge inconsistent artifacts for display.

## Write API

Mutation requests describe intent. The browser does not submit a replacement artifact.

```json
{
  "command_id": "client-generated-key",
  "document_key": "ctown-budget-2026-2027",
  "target_artifact_type": "block_inventory",
  "expected_artifact_sha256": "64-lowercase-hex",
  "expected_review_head_sha256": "64-lowercase-hex-or-null",
  "reviewer": {
    "reviewer_id": "local-reviewer",
    "role": "data-reviewer"
  },
  "action": "resize_block",
  "reason": "Exact source-linked explanation",
  "affected_keys": ["stable-block-key"],
  "source_locations": [],
  "changes": []
}
```

Implemented Stage 1 endpoint:

| Method and path | Intent |
| --- | --- |
| `POST /api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/commands` | Apply one allowlisted Stage 1 mutation and append one review event. |

The Python writer:

1. Re-read the current artifact and review head.
2. Reject stale expected hashes with `409` semantics.
3. Apply an allowlisted action with schema-specific rules.
4. Marks the changed block reviewed and approved by the recorded decision.
5. Canonically serializes the result to temporary files.
6. Validates changed blocks, page dispositions, relationships, and the new review event against their component schemas, then checks complete-artifact semantic and cross-artifact invariants.
7. Constructs the next review event and event hash.
8. Preserves full canonical validation as the startup, explicit validation, test, and artifact-handoff gate.
9. Replaces the artifact pair and restores the prior block artifact if review publication fails.
10. Returns resulting hashes, affected keys, and affected page numbers.

After a successful write, the Node service reparses the atomically published artifacts into its in-memory cache without repeating canonical validation because the writer has already validated the update against a canonically validated base. The response includes refreshed document totals and affected page payloads. The browser patches those pages in place rather than rerunning initialization or reloading the page render. The existing global save lock remains in effect while the command is pending.

This separation reduced a representative temporary-workspace resize from two approximately six-second full validation passes to a 0.338-second writer operation. Full validation remains authoritative and must pass before the service starts and before artifacts are handed off.

## Schema-To-UI Mapping

| Artifact | Primary view | Editable fields after write approval |
| --- | --- | --- |
| `source_evidence` | Thumbnail rail, page canvas, text/OCR layer, evidence status | None; immutable regeneration only. |
| `block_inventory` | Page overlays and block inspector | Implemented: create, resize, reclassify, financial-candidate flag, and delete. Later: split, merge, reorder, anchors, and page disposition. |
| `content_groups` | Multi-page timeline and relationship graph | Membership, order, continuation edges, inherited headers, boundaries, relationships. |
| `structural_template` | Template rule editor | Separate promotion flow only; never edited through a document application. |
| `template_applications` | Anchor and mismatch panel | Exception allowlist selection and review state; generated matches remain evidence. |
| `review_decisions` | Audit timeline | Append only; no edit or delete action. |
| `parity_report` | Baseline-diff table | Discrepancy disposition and linked decision; baseline and shadow records remain immutable. |

Every panel displays artifact type, artifact hash, source hash, generator version, upstream hashes, and review status. Approval controls are disabled when any displayed dependency is stale.

## Screen Layout

The desktop layout uses four coordinated regions:

1. A document and blocker header containing stage coverage, source identity, current hashes, and validation status.
2. A virtualized thumbnail rail containing 154 page cards, evidence status, block counts, group boundaries, mismatches, and unresolved review counts.
3. A page canvas with lazy-loaded render, selectable normalized-coordinate overlays, zoom, pan, and word evidence toggles.
4. A tabbed inspector for page, block, group, template, raw preview, parity, and review history.

The group tab includes a horizontal page timeline. It makes page breaks, repeated headers, continuation edges, inherited headers, and stop boundaries visible without flattening physical provenance.

The minimum viewport uses a single canvas with drawers. All actions remain keyboard accessible. Color is never the only status signal.

## Browser State

One normalized client store holds:

- active document, page, block, group, template application, and parity record keys
- artifact summaries indexed by `artifact_type`
- page summaries indexed by `page_key`
- entities indexed by their stable schema keys
- current zoom and evidence-layer visibility
- server validation state and stale dependency set
- an unsaved command draft, never an unsaved replacement artifact

Selection is key-based. Array positions are display order only and cannot become identities.

The URL retains `document`, `page`, `block`, `group`, and `panel` query parameters so an exact review location can be reopened.

## Initial Stage 0 Slice

Status: complete on 2026-07-15.

The first implementation slice is read-only and must provide:

- one allowlisted Charlottetown pilot document
- all 154 thumbnails with lazy loading
- page render, embedded-word overlay, and OCR overlay toggle
- page dimensions, render hash, evidence counts, disposition, and review status
- explicit indication that page 24 used OCR fallback
- artifact and source hash display
- direct navigation to representative pages 10, 18-23, 87-92, 105, 110-112, 149, and 151-153
- a schema-validation status generated on the server before serving data

Acceptance requires bounded memory use, no database query for review data, no write endpoint, no demo route, and no arbitrary path access.

The implemented client loads the 154 page summaries once, lazy-loads thumbnails, and retains only the active page render plus requested embedded/OCR word evidence. It provides representative-page controls, URL page state, keyboard navigation, 50% to 250% zoom, word overlays, hashes, validation status, source citations, and a narrow-screen layout.

## Editable Stage 1 Slice

Status: complete on 2026-07-15.

`scripts/generate-staged-pdf-block-inventory.py` remains the frozen version 1 generator. `scripts/generate-staged-pdf-block-inventory-v2.py` deterministically converts version 2 Stage 0 word geometry into proposed title, body, and footer candidates, including conservative formatted-text and table-title proposals. It uses conservative cues for formatted text, table of contents, divider, table, financial-candidate, and table-family classification. OCR-derived geometry remains `needs_review`; the generator does not create approvals or consume the legacy published inventory as an input.

The ordered block vocabulary is `title`, `formatted_text`, `table`, `chart`, `other_visual`, `map`, `table_of_contents`, `header`, `footer`, `page_number`, `divider`, and `signature`. Automated top-of-content headings are `title`; `header` and `footer` are reserved for repeating document-level material.

The UI displays normalized Stage 1 boxes over each source render, reading-order and type labels, block selection, financial flags, table-family candidates, confidence, review status, exact keys, and evidence excerpts. A reviewer can select, resize, reclassify, delete, or draw a typed block. Selected and hovered boxes remain transparent.

`formatted_text` and `table` blocks support internal edit mode. The parent remains visible but cannot be selected or resized. Formatted-text regions remain individually boxed as paragraph, bullet list, or sorted list. Tables instead render a spreadsheet grid whose horizontal and vertical dividers can be dragged.

Table selection modes are mutually exclusive and ordered Cell, Row, Column; Cell is the default. Cell selection permits `table_header`, `column_label`, `row_label`, `cell`, `subtotal`, or `total` assignment. Row and Column modes select one index or a contiguous Shift-extended range. Split divides every selected row or column in half and duplicates source cell types. Merge removes the intervening dividers; each merged coordinate retains a shared type only when all source cells match and otherwise becomes `cell`.

The Stage 1 generator clusters Stage 0 words geometrically into table rows and value-start columns. It proposes a complete grid and cell types from header, label, numeric, subtotal, and total cues. `Redetect table grid` replaces the selected grid using its current box. Reviewers can opt into the same replacement atomically when resizing the outer table box.

Stage 1 association mode is source-first. The reviewer selects a relationship type and valid source, stores it with its page and descriptive label, optionally navigates to another page, selects a valid target, and creates the link. The source persists until the write succeeds or the reviewer cancels it; failed writes retain the source and show the error. Chart links require a whole chart and whole table. Continuations require whole table blocks on different pages. Overview-detail links accept one selected overview row or any cell in that row, resolve it to the row's typed `row_label` cell, and link it to a different whole detail table.

Each completed mutation uses optimistic artifact-hash concurrency, validates the resulting artifact set, and appends one event to `review/review-decisions.json`. Table review must include the complete column-header region, row-label region, and table body; repeated headers are not assumed on continuation pages.

The deterministic Charlottetown generation baseline contains 440 candidates across all 154 pages, including 101 conservative financial candidates, 709 formatted-text internal regions, and one review page. Migration decision 39 produced the table-grid checkpoint with 441 blocks, 77 grids, 10,063 cells, and SHA-256 `f880de6838c16cf9fa5ef5f82a4633ad26c9613a9ca55b9a1074260e2eabe8c2`. Subsequent reviewer edits intentionally change the live artifact hash and cell count and remain traceable through the append-only review chain.

## Version 2 Span And Title Slice

Status: complete on 2026-07-27.

The generator selects its output schema from the source-evidence artifact. Version 2 generation may propose a short leading formatted-text region as `title` and may combine short contiguous title rows into one full-width `table_title` cell when later rows provide table-column evidence. All proposals remain proposed or `needs_review`; generation does not approve them.

The writer and reviewer resolve omitted `row_span` and `column_span` values as `1`. Version 2 adds:

- full effective-span rendering and accessible row, column, and span labels
- single-cell numeric row-span and column-span controls
- Shift-extended rectangular logical-cell selection
- logical-cell merge and split commands with deterministic keys
- top or bottom full-width `table_title` classification
- `title` classification for formatted-text regions
- rejection when a consumed cell is a relationship endpoint
- rejection of global row or column split or merge while spanning cells remain
- version 2 human actor, decision basis, exact artifact-reference, and event-chain fields

The version 2 workspace is the default and exposes title, span, propagation, policy, and parity behavior. `PDF_INVENTORY_REVIEW_SCHEMA_VERSION=1` or launcher `-SchemaVersion 1` selects the frozen version 1 rollback workspace. The selector remains local and does not change database, publication, or deployment state.

## Version 2 Document-Scoped Propagation

Phase 4 adds `Find similar` for approved table and formatted-text blocks. `scripts/preview-staged-pdf-structural-propagation.py` creates an ephemeral, deterministic source-pattern hash, recalculates candidate structure from target word evidence, and returns page, target key, confidence, matching evidence, mismatch evidence, current/proposed structure, and `exact`, `light_variation`, `material_variation`, or `one_off` fit.

Preview is read-only and bound to both the block-artifact hash and review-artifact hash. The reviewer can compare current and proposed overlays, exclude candidates, cancel without a write, atomically apply selected exact or light candidates, or append a `reject` event. Rejection records a document-scoped negative control in the review event and changes the same candidate to `one_off` on later previews. Material candidates never enter an apply command.

## Version 2 Structural Templates And Review Policies

Status: complete on 2026-07-27.

After `Find similar`, the reviewer can promote the approved source structure into an immutable document-scoped template and create a versioned review policy. The policy panel reports exact template and policy versions, current mode, runtime suspension, and each candidate's policy outcome. Controls support `review_required`, gated deterministic `sample_review`, gated `auto_approve`, demotion, suspension, and application of only the candidates that the server recomputes as automatically approved.

Template and policy promotion require a human review reason, current block and review hashes, an approved source block, and the recomputed pattern hash. The server never promotes a template from preview alone. Automatic application uses a system audit actor, exact policy reference, matcher hash, fit classification, matching and mismatch evidence, source and target locators, prior and result artifact hashes, and chained event hash. Material or non-allowlisted fits remain blocked. Configured material drift, matcher change, negative-control failure, sample rejection, explicit suspension, and demotion prevent further automatic approvals.

## Later Slices

1. Extend Stage 1 mutation with split, merge, reorder, page-disposition changes, and command preview.
2. Stage 2 adds group membership, continuation linking, inherited headers, stop boundaries, and group relationship review.
3. Phase 5 is complete for immutable document-scoped templates and policy-governed review reduction.
4. Stage 4 extends append-only decisions to later-stage artifacts.
5. Stage 5 adds raw preview aligned to approved blocks and groups without normalization approval.
6. Stage 7 adds record-level baseline parity and discrepancy decisions.

Phase 7 structural parity is visible read-only in the active version 2 workspace. The panel reports matched, missing, extra, changed, and provenance-shifted counts plus every handoff blocker. The approved final report passes with zero blockers; transition remains an operational configuration change rather than a browser control.

Each slice remains shadow-only until its schema, semantic, deterministic-rerun, traversal, and browser tests pass.

## Deferred Work

1. Add private-LAN access through the local installation rather than the temporary launcher. Define authentication or session-token handling, interface selection, firewall creation and removal, discovery, and stop controls before enabling non-loopback binds.
2. Add supported phone and tablet layouts and interactions. Cover touch-sized resize handles, pointer capture, drawers, orientation changes, canvas pan/zoom, internal-structure editing, association creation across pages, and device-browser regression tests.

## Failure And Security Controls

- Reject every non-loopback activation.
- Disable review mode whenever `DEMO_MODE` is true.
- Resolve workspaces from a server allowlist, not URL-derived paths.
- Verify every asset hash before serving it; return `409` on mismatch.
- Limit JSON body size and reject undeclared command properties.
- Reject unknown action names, artifact types, keys, source locations, and field paths.
- Use optimistic concurrency on artifact and review-head hashes.
- Never overwrite a conflicting artifact or truncate review history.
- Escape all source text and labels as text content; do not render artifact HTML.
- Apply no database credentials or publication capability to the review writer.

## Verification Matrix

| Layer | Required checks |
| --- | --- |
| Static | Node syntax, existing UI conventions, keyboard focus, narrow viewport. |
| API | Feature gates, demo denial, allowlist, range checks, traversal denial, no-store headers. |
| Schema | Valid fixture per artifact type and invalid closed-object, key, path, geometry, and reference cases. |
| Write | Preview-only behavior, atomic pair replacement, stale-hash rejection, event hash chain, approval invalidation. |
| Determinism | Same input and command sequence produce identical artifact content except required review timestamps. |
| Pilot | Representative pages, page 24 OCR fallback, 154-page navigation, all recorded asset hashes. |
| Regression | Existing portal smoke suite remains unchanged when the feature is disabled. |

## Approval Gates

- Gate A: approved for the loopback-only local route on port 3217; private-LAN installation is deferred.
- Gate B: approved for the Stage 1 validator-command adapter in the actual Node runtime.
- Gate C: approved for Stage 1 block and formatted-text-region editing, relationship editing, and table-grid editing; later actions require separate review.
- Gate D: Stage 1 generator and mutation UI are enabled; Stage 2 remains pending.
- Gate E: approve any template promotion outside the Charlottetown document scope.

## Sources

- [Staged PDF inventory and extraction architecture](./staged-pdf-inventory-extraction-architecture.md)
- [Staged PDF artifact JSON Schemas](./staged-pdf-artifact-json-schemas.md)
- [Charlottetown 2026/2027 shadow pilot](./staged-pdf-inventory-extraction-charlottetown-pilot.md)
- [Web UI stack](./web-ui-stack.md)
- [Municipal portal UI architecture](../product/municipal-portal-ui-architecture.md)
- `schema/json-schema/staged-pdf-artifacts.schema.json`
- `scripts/validate-staged-pdf-artifacts.py`
- `web/server.js`
