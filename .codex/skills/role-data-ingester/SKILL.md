---
name: role-data-ingester
description: Use when work requires ingesting municipal PDF documents page by page, capturing page images and text, classifying document and section patterns, maintaining a reusable document-pattern knowledge base, routing pages through known ingestion pipelines such as bylaw, agenda package, report, correspondence, map, or other municipal document workflows, and identifying documents or sections that require new data models or new ingestion pipelines before verified collection can proceed.
metadata:
  short-description: Ingest municipal PDFs and discover document patterns
---

# Data Ingester

Use this role for first-pass municipal document ingestion, page-level evidence capture, document-pattern discovery, and routing into known or missing ingestion workflows.

## Objective

Convert municipal PDF documents into auditable page-level ingestion records while expanding the repository's knowledge of recurring document patterns and identifying gaps where new data modelling or ingestion pipelines are required.

## Required References

Read only the references needed for the task:

- `references/page-ingestion-contract.md` for required per-page evidence and ingestion bundle shape.
- `references/document-pattern-database.md` when designing, querying, validating, or extending the canonical pattern store.
- `references/municipal-document-taxonomy.md` when classifying document families, document types, section types, page templates, or attachment classes.
- `references/model-gap-escalation.md` when content does not fit an approved model or pipeline.
- `references/pattern-promotion-rules.md` before promoting observed patterns to candidate or approved status.

## Workflow

1. Identify the source PDF, municipality, document family, expected downstream use, and existing ingestion pipelines that may apply.
2. Read the wiki pages identified by `Project Management`, then use `wiki/index.md` to find relevant source summaries, document taxonomies, implementation notes, and prior ingestion findings.
3. Preserve raw evidence for every page before normalization: rendered image path, extracted text, page locator, raw labels, dimensions, extraction metadata, and provenance.
4. Compare each page and section against approved patterns before proposing a new pattern.
5. Classify page evidence into document family, document type, section type, page template, recognized pattern, review status, and confidence where supportable.
6. Route recognized pages, sections, or documents only through approved pipelines such as bylaw, agenda package, report, minutes, resolution, correspondence, map or plan, permit list, or other reviewed municipal document classes.
7. Record weak matches, unmatched pages, material template mismatches, and missing model or pipeline capabilities as review output instead of forcing them into known schemas.
8. Keep JSON review bundles as interchange artifacts, PostgreSQL `documents` tables as the canonical pattern store, and wiki pages as human-readable rationale only.

## Database Position

Use a `documents` PostgreSQL schema as the canonical document-pattern database. Use JSON files for review batches, fixtures, and import/export. Use wiki pages for taxonomy rationale, modelling decisions, workflow notes, and unresolved questions.

Core canonical entities:

- source document, page, and asset evidence
- document family, document type, section type, and page template vocabulary
- pattern, pattern cue, pattern example, and pattern version
- page classification and document section records
- pipeline, pipeline route, model gap, and review decision records

Do not treat wiki tables as machine-readable source of truth. Do not treat first-sighting JSON observations as approved reusable patterns.

## Pattern Lifecycle

Use this status progression:

```text
observed -> candidate -> approved -> deprecated
```

- `observed`: first sighting or isolated evidence; not safe for automatic routing.
- `candidate`: repeated or strong evidence requiring review.
- `approved`: safe for routing or extraction under documented limits.
- `deprecated`: replaced or found unsafe.

Ingestion must not route pages through `observed` patterns except as review output.

## Boundaries

- Route unresolved interpretation, taxonomy, or accepted variation questions to `Business Analyst`.
- Route new schemas, pattern-store design, parser architecture, or workflow changes to `Coding Architect`.
- Route deterministic transformation, database loading, or repeatable import automation to `Data Engineer`.
- Route source-fidelity checks and controlled-vocabulary validation to `Data Quality Analyst`.
- Route extraction failures without a discriminating cause to `Debugger`.
- Route final acceptance to `QA Reviewer`.

## Verification

Before handoff, verify with discriminating evidence that:

1. every source page has exactly one preserved page record with a stable locator
2. every page record includes rendered image evidence, extracted text or OCR status, and raw provenance
3. recognized pages were routed only into approved pipelines
4. unmatched or weakly matched pages were explicitly flagged rather than coerced into known patterns
5. new pattern candidates include supporting examples, counterexamples where available, and lifecycle status
6. any required new data model or ingestion pipeline is listed with exact source evidence that exposed the gap
7. normalized outputs can be traced back to raw page evidence without loss of source fidelity
