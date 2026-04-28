---
type: project
tags:
  - charlottetown
  - zoning
  - ingestion
  - database
  - spatial
updated: 2026-04-28
---

This page records the next-phase plan for unified relational and spatial ingestion of the Charlottetown current and draft zoning bylaws.

# Unified Zoning Ingestion Plan

## Verified Starting Point

The current and draft generated JSON sets are ready for schema planning. A scan of `data/zoning/charlottetown/**/*.json` and `data/zoning/charlottetown-draft/**/*.json` found 0 non-empty `review_flags` arrays and 0 `confidence: "needs_review"` entries.

The database target is a relational-core `zoning` schema. The importer must not store full source-file JSON blobs, top-level aggregate `text_raw` values, `review_flags`, or any `confidence` attributes. Raw text remains in scope only at reconstructable clause, table, page, map-reference, and source-unit granularity.

## Coverage Model

The main ingestion risk is not current review state; it is asymmetric document coverage and file layout.

The draft bylaw has all chapters represented as separate JSON documents, including administration, permit applications and processes, general provisions, design standards, definitions, zones, and schedules. The current bylaw has all general provisions in one `general-provisions.json` file covering chapters 4-6 and 46-48, plus separate zone files, definitions, design standards, and appendices B/C.

The schema must therefore compare by logical bylaw structure, not by source JSON filename. Required comparison units are bylaw part, section, clause, topic, structured requirement, term, use, numeric value, relationship, and accepted equivalence link.

Skipped or not-yet-normalized current-bylaw chapters must be recorded as deferred coverage gaps. These gaps are not blockers for the first ingestion milestone, but comparison outputs must label them as deferred current content instead of treating missing current records as substantive policy differences.

## Implementation Shape

Create implementation artifacts for a new `zoning` schema after this wiki update. The schema should include:

- `bylaw_document`, `document_revision`, and `import_batch` for current and draft versions, draft updates, supersession, and repeatable imports.
- `source_file`, `bylaw_part`, `section`, `clause`, `definition`, raw table/page/map-reference tables, and reconstruction ordering fields.
- `term`, `use_rule`, `numeric_value`, `requirement`, `regulation_group`, `conditional_rule_group`, and `relationship` tables for structured querying.
- `section_equivalence` for current-vs-draft comparison by topic, title, label, text similarity, vector candidates, and manual review state.
- `coverage_gap` for deferred current-bylaw normalization tasks.
- `spatial_layer`, `spatial_feature`, `zone_spatial_feature`, and `spatial_reference` for map and spatial linkage.

Draft updates must be loaded through versioned import batches. New imports should identify added, removed, changed, and unchanged records, supersede prior active draft rows, and preserve manual correction records so they can be re-applied or re-evaluated when the draft PDF changes.

## Spatial and Map Scope

Only these live spatial layers are in scope for first ingestion:

- `CHTWN_Draft_Zoning_Boundaries`
- `CHTWN_Parcel_Map`
- `CHTWN_Street_Network`
- `CHTWN_Zoning_Boundaries`
- `CHTWN_Schedule_A_Wetlands`

The abandoned parcel-review workflow layers are out of scope for first ingestion, including `CHTWN_Current_Zoning_Parcel_Review` and `CHTWN_Draft_Parcel_Map`.

Known spatial preparation items:

- Resolve draft spatial layer code `H` against draft bylaw zone code `HI`.
- Fix or document the 3 invalid geometries in `CHTWN_Zoning_Boundaries`.
- Maintain current map-code to bylaw-code crosswalks, such as no-hyphen map codes that correspond to hyphenated bylaw zone codes.
- Classify referenced maps and diagrams as already spatial, PDF-only image, schedule needing digitization, or text-only reference.

## Vector Scope

Vector support is text-first. Embed clauses, definitions, requirements, table-row summaries, map-reference summaries, relationship summaries, and section-equivalence summaries only after stable relational row IDs exist.

Vectors are for semantic retrieval, candidate section equivalence, draft update diff assistance, related-provision discovery, and current-vs-draft comparison support. They are not legal truth or spatial truth. Relational joins and PostGIS remain authoritative. Geometry vectors are out of scope for v1.

## Milestones

1. Design the `zoning` schema, import-batch model, document-revision model, coverage-gap table, and section-topic vocabulary.
2. Build initial JSON ingestion for current and draft records, excluding process fields and preserving granular raw reconstruction records.
3. Build section-equivalence candidate generation and manual review storage for comparable current and draft bylaw sections.
4. Register and validate the approved spatial layers, resolve code mismatches, and link spatial features to zones and map references.
5. Add text-vector support after relational IDs and comparison records are stable.
6. Normalize and ingest deferred current-bylaw chapters and appendices, then re-run equivalence and comparison outputs.

## Acceptance Checks

Implementation is ready to begin when the schema and importer design can satisfy these checks:

- No ingested `review_flags`, `confidence` fields, full-file raw JSON blobs, or top-level aggregate raw text.
- Current combined general-provision sections and draft split general-provision sections query through the same `section` and `clause` interfaces.
- Comparison views distinguish accepted equivalence, unresolved equivalence, true additions/removals, and deferred current coverage.
- Import batches preserve prior draft versions and can report added, removed, changed, and unchanged draft records.
- Spatial inventory is limited to the approved layers and validates feature counts, SRIDs, geometry types, invalid geometry counts, and zone-code joins.
- Vector rows always link back to authoritative relational records.

## Sources

- [Charlottetown workstream context](./workstream-context.md)
- [Draft validation rebaseline](./draft-validation-rebaseline.md)
- [Draft final QA summary](../../../plan/chalottetown-draft-zoning-final-qa-summary.md)
- [Current zoning source manifest](../../../data/zoning/charlottetown/source-manifest.json)
- [Draft zoning source manifest](../../../data/zoning/charlottetown-draft/source-manifest.json)
- [Current zoning extraction outputs](../../../data/zoning/charlottetown/README.md)
- [Draft zoning extraction outputs](../../../data/zoning/charlottetown-draft/README.md)
- [Current parcel review schema](../../../data/spatial/charlottetown/current-zoning-parcel-review-schema.json)
- [Draft map layers summary](../../../data/spatial/charlottetown/charlottetown-draft-map-layers-2026-04-09-municipal-fit.summary.json)
