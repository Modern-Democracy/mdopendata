---
type: implementation
tags:
  - extraction
  - pdf
  - review-ui
  - architecture
  - charlottetown
updated: 2026-07-15
---

This page defines the local-only inventory-review UI implementation plan for the version 1 staged PDF artifact schemas.

# Staged PDF Inventory Review UI Plan

## Implementation Status

The read-only Stage 0 evidence slice and editable Stage 1 block slice are complete. They require `PDF_INVENTORY_REVIEW_ENABLED=1`, `PDF_INVENTORY_REVIEW_WRITE_ENABLED=1`, a loopback bind, and `DEMO_MODE=false`.

```powershell
./scripts/start-staged-pdf-review.ps1
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
| `scripts/update-staged-pdf-block-inventory.py` | Validate a Stage 1 mutation, append its review event, and atomically publish both artifacts. |
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
6. Validates JSON Schema, semantic invariants, and loaded cross-artifact references.
7. Constructs the next review event and event hash.
8. Validates the proposed artifact and complete review chain together.
9. Replaces the artifact pair and restores the prior block artifact if review publication fails.
10. Returns resulting hashes and affected keys.

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

`scripts/generate-staged-pdf-block-inventory.py` deterministically converts Stage 0 word geometry into proposed title, body, and footer candidates. It uses conservative cues for formatted text, table of contents, divider, table, financial-candidate, and table-family classification. OCR-derived geometry remains `needs_review`; the generator does not create approvals or consume the legacy published inventory as an input.

The ordered block vocabulary is `title`, `formatted_text`, `table`, `chart`, `other_visual`, `map`, `table_of_contents`, `header`, `footer`, `page_number`, `divider`, and `signature`. Automated top-of-content headings are `title`; `header` and `footer` are reserved for repeating document-level material.

The UI displays normalized Stage 1 boxes over each source render, reading-order and type labels, block selection, financial flags, table-family candidates, confidence, review status, exact keys, and evidence excerpts. A reviewer can select, resize, reclassify, delete, or draw a typed block. Selected and hovered boxes remain transparent.

`formatted_text` and `table` blocks support internal edit mode. The parent remains visible but cannot be selected or resized while its page-normalized internal regions are edited. Formatted-text region types are paragraph, bullet list, and sorted list. Table region types are table header, column label, row label, cell, subtotal, and total. Stage 1 relationships link graphs to source tables, table fragments across pages, and overview table regions to detail tables.

Each completed mutation uses optimistic artifact-hash concurrency, validates the resulting artifact set, and appends one event to `review/review-decisions.json`. Table review must include the complete column-header region, row-label region, and table body; repeated headers are not assumed on continuation pages.

The Charlottetown artifact contains 440 candidates across all 154 pages, including 101 conservative financial candidates, 709 formatted-text internal regions, and one review page. Its SHA-256 is `a57783102867efc69beff296a64f3affaf67b9f504fef900c081f3ad10f00c41`.

## Later Slices

1. Extend Stage 1 mutation with split, merge, reorder, page-disposition changes, and command preview.
2. Stage 2 adds group membership, continuation linking, inherited headers, stop boundaries, and group relationship review.
3. Stage 3 adds template anchors, geometry deltas, negative controls, mismatch blocking, and exception allowlists.
4. Stage 4 extends append-only decisions to later-stage artifacts.
5. Stage 5 adds raw preview aligned to approved blocks and groups without normalization approval.
6. Stage 7 adds record-level baseline parity and discrepancy decisions.

Each slice remains shadow-only until its schema, semantic, deterministic-rerun, traversal, and browser tests pass.

## Deferred Work

1. Add private-LAN access through the local installation rather than the temporary launcher. Define authentication or session-token handling, interface selection, firewall creation and removal, discovery, and stop controls before enabling non-loopback binds.
2. Add supported phone and tablet layouts and interactions. Cover touch-sized resize handles, pointer capture, drawers, orientation changes, canvas pan/zoom, internal-region editing, association creation across pages, and device-browser regression tests.

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
- Gate C: approved for Stage 1 `create`, `resize`, `set_type`, and `delete`; later actions require separate review.
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
