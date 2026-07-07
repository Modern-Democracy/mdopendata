---
type: implementation
tags:
  - council-meetings
  - document-ingestion
  - agenda-packages
updated: 2026-07-06
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

Remaining work is council-domain import resolution.

## Sources

- [Council and committee meetings](../council-committee-meetings/README.md)
- [Agenda and package document taxonomy](../council-committee-meetings/agenda-document-taxonomy.md)
- [Root wiki index](../index.md)
- `plan/document_pipeline_design.md`
- `schema/json-schema/agenda-package-extraction.schema.json`
- `schema/sql/022_agenda_package_extraction.sql`
- `schema/sql/023_page_template_drafts.sql`
- `schema/sql/024_package_document_assembly.sql`
