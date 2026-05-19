# Model Gap Escalation

Use this reference when a document, section, page, or field does not fit an approved model or ingestion pipeline.

## Gap Types

- `new_document_type`: the source document type is not represented in the taxonomy or schema.
- `new_section_type`: a section recurs or matters but has no approved section model.
- `new_page_template`: the page has a repeated visual or textual structure with no approved template.
- `new_pipeline`: the content needs a repeatable ingestion process that does not exist.
- `new_field_model`: important data appears but has no destination field or relationship.
- `ambiguous_taxonomy`: multiple classifications fit and accepted variation is undefined.
- `source_quality_blocker`: scan quality, OCR failure, missing pages, or corrupted source prevents verified extraction.

## Escalation Rules

- Route taxonomy ambiguity or accepted variation to `Business Analyst`.
- Route new schema, workflow, parser architecture, or pattern-store changes to `Coding Architect`.
- Route repeatable transformation or loading work to `Data Engineer` after requirements and design are explicit.
- Route source fidelity validation to `Data Quality Analyst`.
- Route failed extraction without a discriminating cause to `Debugger`.

## Required Gap Evidence

Each model gap should include:

- exact source document and page locator
- observed content summary
- raw text excerpt or asset locator when available
- why the current model or pipeline is insufficient
- proposed owner role
- blocking status: blocks ingestion, blocks normalization, blocks routing, or non-blocking review
- suggested next decision

## Stop Conditions

Stop before normalization when assigning a value would require inventing a schema meaning, silently widening a taxonomy, or coercing materially different source content into an existing template.
