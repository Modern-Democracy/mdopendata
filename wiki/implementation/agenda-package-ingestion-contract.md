---
type: implementation
tags:
  - council-meetings
  - document-ingestion
  - agenda-packages
updated: 2026-07-28
---

This page defines the approved package-level extraction contract and template-discovery gate for agenda package PDFs.

# Agenda Package Ingestion Contract

## Canonical Result

Each source agenda package produces one package JSON object conforming to `schema/json-schema/agenda-package-extraction.schema.json`. Its `documents` array contains one JSON object per logical document, including documents assembled from multiple source pages.

The first array entry is always the agenda. Every later logical document has exactly one `primary_agenda_item_key`. Page-level text, classification evidence, bounding boxes, and review history remain in the `documents` schema and are referenced through document provenance rather than copied into every normalized field.

PostgreSQL stores the canonical package JSON in `documents.package_extraction.result_json`. `documents.package_extracted_document` provides queryable rows for the ordered logical documents and their primary agenda-item bindings. The existing `council.package_document.agenda_item_id` remains the normalized council-domain relationship after key resolution during import.

## Workflow Gate

The package workflow uses these states:

1. `discovering_templates`: traverse and classify every page before final extraction.
2. `awaiting_template_approval`: one or more unknown templates have model-generated drafts awaiting user editing or approval.
3. `ready_for_extraction`: every page has an approved template and logical document assembly is defined.
4. `extracting`: run template-specific extraction and assemble multi-page documents.
5. `completed`: persist the package JSON and normalized logical-document rows.
6. `failed`: preserve diagnostics for a run that cannot continue.

Completion requires zero unresolved template gaps, an agenda document key, a package result, and a completion timestamp. A model-created template is stored with review status and cannot be used for final extraction until user approval changes it to active status.

## Template Draft Contract

A draft identifies page roles, detection cues, logical-document assembly rules, and field mappings. Each field mapping specifies a stable field key, destination JSON Pointer, value type, required status, extraction instruction, and optional page region and normalization rule.

Unknown-template discovery is package-wide. The pipeline may prepare all model drafts in one pass, but final data extraction does not begin until every draft required by the package is approved.

## Implementation Boundary

The JSON and PostgreSQL contracts are implemented. `/agenda-package-ingestion` accepts a browser-selected PDF and streams it to `POST /api/document-ingestion/packages`. The upload path validates the PDF signature, computes SHA-256, preserves the raw source under `data/document-ingestion/uploads/`, deduplicates by hash, and transactionally creates the source-document and package-extraction records in `discovering_templates` state. `GET /api/document-ingestion/packages/{packageKey}` returns the current state.

Traversal runs as a background server job after registration. The browser polls package and page state, reports active or failed traversal, and advances to classification only after every recorded page and render is available. Selecting another PDF resets all later-stage browser output before the new upload begins. The Docker web service uses an init process so terminated Poppler children are reaped.

Large-package traversal resolves Poppler page filenames by their numeric suffix because Poppler zero-pads output names according to package page count. Complete existing render sets are reused on a traversal retry. Duplicate-upload temporary-file deletion is asynchronous so Windows bind-mount cleanup cannot delay the registration response.

`POST /api/document-ingestion/packages/{packageKey}/traverse` uses Poppler to determine page count, render each page to PNG, and extract embedded page text. It stores page evidence in `documents.source_page`, render metadata in `documents.source_asset`, and artifacts under `data/document-ingestion/packages/{sourceHash}/pages/`. Page-list, page-image, and page-text GET endpoints support the browser page grid. Traversal is idempotent when the recorded page count and render assets are complete.

`POST /api/document-ingestion/packages/{packageKey}/classify` evaluates each page against active page templates attached to approved page patterns. The deterministic classifier supports text, regular-expression, and page-position cues, requires all required cues to match, applies weighted confidence thresholds, and treats ties between templates as ambiguous. Unmatched pages receive `needs_review` classifications and active blocking `new_page_template` gaps. Any unknown page moves the package to `awaiting_template_approval`; only a zero-gap result moves it to `ready_for_extraction`. Classification is rerunnable without duplicating active classification or gap rows. The browser displays matched-template or unknown-template badges and the blocking gap count.

`/document-import` remains the fixed May 12 package UI and workflow prototype. It is an implementation reference only and is not part of the general ingestion entry point.

`POST /api/document-ingestion/packages/{packageKey}/template-drafts` creates rerunnable first-pass drafts for every active page-template gap. The local `local-template-drafter-v1` implementation proposes a package-discriminating text cue, page role, document-assembly rule, and title/body field mappings. Drafts are stored separately in `documents.page_template_draft`; they are editable through the browser and cannot participate in classification.

`PUT /api/document-ingestion/packages/{packageKey}/template-drafts/{draftId}` saves an edited draft. Explicit approval through the draft approval endpoint transactionally creates an active page template, an approved page pattern and its cues, links the approved records back to the immutable draft history, resolves the draft's page gaps, and reruns package classification. Approved drafts become read-only in the browser. Remaining unknown pages continue to block extraction.

`POST /api/document-ingestion/packages/{packageKey}/assembly-plan` creates a package-specific draft with one logical document per page. The browser JSON editor allows adjacent page entries to be merged into inclusive contiguous ranges. Each row stores its order, document key, title, page range, agenda role, primary agenda-item key, participating template keys, and derived assembly rule in `documents.package_document_assembly`.

Assembly validation requires complete package coverage with no gaps or overlaps. The first row must be the sole agenda and begin on page 1. Every approved supporting document requires exactly one primary agenda-item key. Approval is blocked until every page classification is accepted; an approved plan moves the package from `awaiting_document_assembly` to `ready_for_extraction`. Approved plans become read-only in the browser.

For a single-page document, the derived rule is `single_page`. A multi-page range uses `contiguous_page_range` with `document_start`, `document_continuation`, and `document_end` roles. The range retains every distinct approved page-template key so extraction can apply page-specific configurations while emitting one document JSON object.

`POST /api/document-ingestion/packages/{packageKey}/extract` requires zero unresolved classifications and an approved assembly plan. It loads each page's approved template configuration, combines the text for each logical document in page order, applies each distinct JSON Pointer mapping once, and persists both the canonical package JSON and queryable `documents.package_extracted_document` rows. Multi-page documents retain all source page and template keys in provenance while emitting one content object.

Deterministic extraction strategies are `first_nonempty_line`, `full_text`, `regex_capture`, `constant`, and `page_texts`. Existing approved `title` and `body_text` mappings default to `first_nonempty_line` and `full_text`. Mappings support NFKC text normalization, trimming, whitespace collapsing, case conversion, primitive type conversion, required-field failure, and safe nested JSON Pointer assignment. Unsupported or conflicting mappings fail the extraction rather than silently inventing content.

Successful extraction sets the package to `completed`, records the agenda document key and completion timestamp, and exposes the result through `GET /api/document-ingestion/packages/{packageKey}/result`. A completed rerun returns the persisted result without creating duplicate active document rows. The browser displays the persisted JSON and completion state.

The template review UI includes a visual deterministic field-mapping editor. Each row exposes the stable field key, destination JSON Pointer, value type, required flag, extraction instruction, strategy, trimming, whitespace collapsing, and strategy-specific regex or constant options. Adding, editing, or removing rows synchronizes the underlying template JSON. Advanced JSON remains available and can be explicitly reapplied to the visual editor. Approved template mappings are rendered read-only.

Draft persistence rejects unsupported strategies, invalid regular expressions, invalid field keys or JSON Pointers, missing instructions, and duplicate field keys or pointers before template approval.

Each visual field mapping can optionally define a page region. The picker displays the rendered source page and supports drag selection or direct coordinate entry. Regions use normalized `x`, `y`, `width`, and `height` values in the range 0–1, making them independent of render DPI and source page dimensions. The preview page records where the draft rectangle was drawn; `page_scope: template_page` applies the reusable region to any page classified with that template rather than binding it to an absolute package page number.

During extraction, Poppler `-bbox-layout` word coordinates are normalized to the source page dimensions. Words whose centers fall inside the approved rectangle become the input text for that field's deterministic strategy. Full-page extraction remains the default when a mapping has no region. Invalid or out-of-page rectangles are rejected before persistence.

Phase 6 adds a separate read-only municipal-package reuse preview. An immutable approved profile binds one jurisdiction, source family, and document family to package grammar, ordered embedded-document templates, exact structural-template and review-policy hashes, and positive and nearest-negative controls. The deterministic preview identifies start, continuation, and end boundaries; preserves source order; evaluates fit and review policy; and accounts for every page as assigned, unknown, or conflicting.

`POST /api/document-ingestion/packages/{packageKey}/reuse-preview` runs only when `AGENDA_PACKAGE_REUSE_PROFILE` resolves to a repository file and the registered source has explicit jurisdiction, source-family, document-family, and complete page traversal evidence. The canonical Charlottetown public-meeting value is `data/document-ingestion/profiles/charlottetown-council-public-meeting/v1/profile.json`. The endpoint performs no database or artifact writes. The browser displays package status, coverage, ordered document ranges, fit, policy outcomes, and boundary/unresolved evidence counts.

`POST /api/document-ingestion/packages/{packageKey}/reuse-preview/assembly-plan` is the explicit human-approved handoff. It reruns the configured preview and fails closed unless every page is assigned exactly once, no unknown, conflicting, omitted, material, policy-blocked, or unresolved evidence remains, the source hash is unchanged, and every referenced page template is active. It also refuses to replace an approved assembly.

Structural page-role keys in a reuse preview are not extraction page-template keys. Before writing, the handoff reruns the profile's matched positive control and binds each structural role to that control page's accepted, active PostgreSQL page template. Missing, inactive, incomplete, or inconsistent positive-control bindings block the handoff. Template activity is rechecked under the write transaction.

Within one database transaction, the handoff supersedes prior active page classifications with reviewer-accepted profile assignments, records exact profile, matcher, policy, structural-template, page-role, and boundary evidence, resolves corresponding page-template gaps, and creates an editable draft assembly. The first matched document becomes the agenda; later documents retain null agenda-item bindings until manual assignment. The package moves to `awaiting_document_assembly`, not `ready_for_extraction`.

The handoff does not approve the assembly, infer agenda-item bindings, run extraction, import council-domain relationships, or publish records. A repeated handoff against the same active draft and profile hash returns the existing draft without new writes.

Live verification on 2026-07-28 cloned the reviewed six-page positive source into an ephemeral package, then removed it by cascade. The handoff created six reviewer-accepted classifications and five draft assembly rows with exact ranges `1`, `2`, `3`, `4`, and `5-6`; it created zero extracted documents. The repeated handoff created no additional classification or assembly IDs. The 453-page negative remained blocked, the reviewed positive's approved assembly remained protected, permanent positive and negative control rows were byte-for-byte equal as PostgreSQL JSON before and after, the global council package-document count did not change, and zero ephemeral source rows remained.

Council-domain import is an explicit post-extraction operation. `GET /api/document-ingestion/packages/{packageKey}/council-import` lists active meetings from the package jurisdiction and reports the meeting-selection gate. Supplying `meetingKey` previews bindings without writes. `POST /api/document-ingestion/packages/{packageKey}/council-import` performs the import only after an existing meeting is selected.

The resolver requires a completed package extraction and exact parity with the active approved assembly. Every supporting document must carry a non-empty `primary_agenda_item_key`, and that key must resolve to exactly one active `council.agenda_item` within the selected meeting. No cross-meeting or fuzzy matching is allowed. The agenda document remains unbound. Supporting documents inherit `business_item_id` only from their resolved agenda item. Missing or ambiguous keys block the complete transaction before an import batch or package document is written.

The import resolves or creates the jurisdiction-scoped `council.source_document` by source hash, then creates or versions the five `council.package_document` records in source order. It preserves exact page arrays and inclusive page ranges, records the approved assembly as boundary evidence, and writes import-batch and per-record audit events. Repeating an unchanged import records all package documents as unchanged and preserves their active IDs. It does not create a meeting, parse an agenda, infer business-item identity, approve extraction state, or publish data.

Live verification on 2026-07-28 used an ephemeral existing meeting with exact `bia-hearing` agenda-item and business-item bindings. The preview resolved all four supporting documents and left the agenda unbound. Import created five package documents with page ranges `1`, `2`, `3`, `4`, and `5-6`; supporting documents inherited the agenda item's business item. A selected meeting without `bia-hearing` returned `409` and created zero package documents or import batches. The unchanged rerun retained all five active IDs, reported five unchanged records, preserved the permanent council fingerprint exactly, and removed all ephemeral records.

The canonical profile is approved from the reviewed six-page February 3, 2026 package. It references five immutable same-edition structural templates and five `review_required` policies. Its positive control resolves five source-ordered documents with exact six-page coverage, including the two-page mailed notice and map. Its stored nearest-negative control uses the first six pages of the unreviewed January 13 regular-council package; all six remain unknown and blocked. Live endpoint verification against all 453 pages also returns zero documents, 453 unknown pages, zero conflicts, and zero omissions. Historical package rows 2 and 3 have explicit `charlottetown-council` source-family metadata. Approved-preview handoff, extraction, and explicit council-domain import resolution are implemented.

## Sources

- [Council and committee meetings](../council-committee-meetings/README.md)
- [Agenda and package document taxonomy](../council-committee-meetings/agenda-document-taxonomy.md)
- [Root wiki index](../index.md)
- `plan/document_pipeline_design.md`
- `schema/json-schema/agenda-package-extraction.schema.json`
- `schema/json-schema/agenda-package-reuse-profile.schema.json`
- `schema/json-schema/agenda-package-reuse-preview.schema.json`
- `scripts/preview-agenda-package-reuse.py`
- `schema/sql/022_agenda_package_extraction.sql`
- `schema/sql/023_page_template_drafts.sql`
- `schema/sql/024_package_document_assembly.sql`
