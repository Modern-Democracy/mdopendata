# Document Pattern Database

Use this reference when designing, querying, validating, or extending the canonical document-pattern store.

## Storage Decision

Use PostgreSQL tables in a `documents` schema as the canonical pattern database. Use JSON files for review batches, fixtures, import/export, and Git-readable diffs. Use wiki pages for taxonomy rationale, modelling decisions, workflow notes, and unresolved questions only.

## Core Entities

- `documents.ingest_batch`: ingestion run metadata.
- `documents.source_document`: one municipal PDF or source file.
- `documents.source_page`: one page with raw text and page metadata.
- `documents.source_asset`: rendered page image, OCR image, embedded image, thumbnail, or other evidence asset.
- `documents.document_family`: broad family such as bylaw, agenda package, report, correspondence, or map.
- `documents.document_type`: specific document class within a family.
- `documents.section_type`: logical section class.
- `documents.page_template`: observed page-level template.
- `documents.pattern`: reusable recognition unit.
- `documents.pattern_cue`: text, regex, layout, visual, metadata, or page-position signal.
- `documents.pattern_example`: positive, negative, or edge-case source-page example.
- `documents.pattern_version`: lifecycle and replacement history.
- `documents.page_classification`: observed page assignment.
- `documents.document_section`: contiguous page range or logical section.
- `documents.extracted_field`: raw and normalized field observations.
- `documents.pipeline`: known ingestion pipeline.
- `documents.pipeline_route`: routing decision for page, section, or document.
- `documents.model_gap`: missing model or missing pipeline record.
- `documents.review_decision`: human or agent review decision.

## Pattern Status

Use this lifecycle:

```text
observed -> candidate -> approved -> deprecated
```

Only `approved` patterns may support automatic routing. `observed` and `candidate` patterns can support review queues and candidate discovery.

## Minimal Pattern Fields

A pattern record should include:

- `pattern_key`
- `pattern_scope`: `document`, `section`, or `page`
- `pattern_name`
- `jurisdiction_scope`: `global`, province, municipality, or source-specific
- optional family, type, section, and template keys
- `status`
- `confidence_rule` as JSON
- `notes`
- `natural_key`, `content_hash`, `is_active`, and supersession fields when stored in PostgreSQL

## Minimal Cue Fields

A pattern cue should include:

- `cue_type`: `text`, `regex`, `layout`, `visual`, `metadata`, or `page_position`
- `cue_value`
- `cue_config`
- `required`
- `weight`
- `notes`

## Minimal Example Fields

A pattern example should include:

- `pattern_key`
- `source_page` locator or ID
- `example_type`: `positive`, `negative`, or `edge_case`
- `evidence_note`
- `reviewer_status`

## Verification Invariants

- Every page classification must trace to a pattern, reviewer decision, or model gap.
- Pattern reuse requires positive examples and nearby negative examples where available.
- JSON review bundles must be importable without changing semantic meaning.
- Wiki pages must not be required for machine correctness.
