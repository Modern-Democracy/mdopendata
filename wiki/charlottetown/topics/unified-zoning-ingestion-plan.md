---
type: project
tags:
  - charlottetown
  - zoning
  - ingestion
  - database
  - spatial
updated: 2026-04-29
---

This page records the active plan and implementation status for unified relational and spatial ingestion of the Charlottetown current and draft zoning bylaws.

# Unified Zoning Ingestion Plan

## Verified Starting Point

The current and draft generated JSON sets were ready for schema planning after validation. A scan of `data/zoning/charlottetown/**/*.json` and `data/zoning/charlottetown-draft/**/*.json` found 0 non-empty `review_flags` arrays and 0 `confidence: "needs_review"` entries.

The `zoning` schema migration and initial Charlottetown importer have now been implemented:

- Schema migration: `schema/sql/005_charlottetown_unified_zoning.sql`.
- Importer: `scripts/import-charlottetown-zoning.py`.
- Database schema: the `zoning` schema contains the planned relational, source reconstruction, comparison, coverage-gap, manual-correction, spatial-linkage, and topic tables.
- Database population: current and draft bylaw records have been imported into the relational core tables. A database check on 2026-04-29 found populated document, source, section, clause, definition, raw table, raw map-reference, and structured-fact tables, with completed import batches for both current and draft inputs.
- Section-equivalence candidate generation has started. `scripts/generate-charlottetown-section-equivalence.py` now populates 137 tuned `title_topic_token_v1` candidate rows in `zoning.section_equivalence` after exact-title and weak-false-positive controls were checked on 2026-04-29.
- Not yet populated: coverage-gap, spatial layer, spatial feature, zone-spatial-feature, and spatial-reference records.

The database target is a relational-core `zoning` schema. The importer must not store full source-file JSON blobs, top-level aggregate `text_raw` values, `review_flags`, or any `confidence` attributes. Raw text remains in scope only at reconstructable clause, table, page, map-reference, and source-unit granularity.

Source JSON field handling must be explicit in the first importer:

- `document_metadata` supplies document identity, source path, document type, zone metadata, raw titles, and citations.
- `raw_data.source_units`, `sections_raw`, nested `clauses_raw`, `entries_raw`, `pages_raw`, `tables_raw`, and `map_references_raw` are copied into normalized raw-source tables with source-order fields.
- `structured_data.terms`, `uses`, `numeric_values`, `requirements`, `regulation_groups`, `conditional_rule_groups`, `zone_relationships`, `map_layer_references`, `definitions`, `cross_references`, `site_specific_rules`, `spatial_references`, and `other_requirements` are copied into typed relational tables only when their referenced source records resolve.
- `review_flags` and all `confidence` fields are excluded from durable zoning tables. The importer may count and reject non-empty `review_flags` or `confidence: "needs_review"` values in an import-run diagnostic, but must not store them as zoning facts.
- Top-level source files may be checksummed for import diagnostics, but full JSON payloads are not stored.

## Coverage Model

The main ingestion risk is not current review state; it is asymmetric document coverage and file layout.

The draft bylaw has all chapters represented as separate JSON documents, including administration, permit applications and processes, general provisions, design standards, definitions, zones, and schedules. The current bylaw has all general provisions in one `general-provisions.json` file covering chapters 4-6 and 46-48, plus separate zone files, definitions, design standards, and appendices B/C.

The schema must therefore compare by logical bylaw structure, not by source JSON filename. Required comparison units are bylaw part, section, clause, topic, structured requirement, term, use, numeric value, relationship, and accepted equivalence link.

Skipped or not-yet-normalized current-bylaw chapters must be recorded as deferred coverage gaps. These gaps are not blockers for the first ingestion milestone, but comparison outputs must label them as deferred current content instead of treating missing current records as substantive policy differences.

`coverage_gap` records must include the bylaw document, gap type, logical bylaw part or source locator, source file when known, expected future record family, comparison effect, status, and notes. The first accepted gap types are `deferred_current_chapter`, `deferred_current_appendix_table_rows`, `pdf_only_schedule`, `not_yet_digitized_map`, and `source_layout_limit`. The first accepted statuses are `deferred`, `in_progress`, `resolved`, and `wont_fix`. A gap whose comparison effect is `suppress_missing_current_difference` must prevent comparison views from reporting draft-only content as a policy addition for that covered unit until the gap is resolved.

## Implementation Shape

The first implementation artifacts for the `zoning` schema now exist. The schema includes:

- `bylaw_document`, `document_revision`, and `import_batch` for current and draft versions, draft updates, supersession, and repeatable imports.
- `source_file`, `bylaw_part`, `section`, `clause`, `definition`, raw table/page/map-reference tables, and reconstruction ordering fields.
- `term`, `use_rule`, `numeric_value`, `requirement`, `regulation_group`, `conditional_rule_group`, and `relationship` tables for structured querying.
- `section_equivalence` for current-vs-draft comparison by topic, title, label, text similarity, vector candidates, and manual review state.
- `coverage_gap` for deferred current-bylaw normalization tasks.
- `spatial_layer`, `spatial_feature`, `zone_spatial_feature`, and `spatial_reference` for map and spatial linkage.

Draft updates must be loaded through versioned import batches. New imports should identify added, removed, changed, and unchanged records, supersede prior active draft rows, and preserve manual correction records so they can be re-applied or re-evaluated when the draft PDF changes.

## V1 Import Scope

The first JSON importer is limited to approved-schema current and draft bylaw JSON under `data/zoning/charlottetown` and `data/zoning/charlottetown-draft`, plus both source manifests. It must ingest:

- zone files, current `general-provisions.json`, draft general-provision files, design standards, definitions, draft `other` process files, draft schedule map files, and current appendix table files
- document metadata, source files, source units, bylaw parts, sections, clauses, definitions, raw pages, raw tables, raw table rows and cells, raw map references, and citations
- structured terms, uses, numeric values, requirements, regulation groups, conditional rule groups, relationships, map references, and spatial-reference metadata when their source references resolve

The first importer must defer row-level normalization of current Appendix B and Appendix C, schedule-map digitization, vector embeddings, parcel overlays, public web output, and meeting or permit records. Draft `other` process files are ingested as bylaw source structure and requirements, but no permit application workflow model is created in v1.

## Stable Identity and Diffing

Every imported table that participates in repeatable imports must have both a surrogate database ID and a stable natural key. The natural key is the canonical document revision plus the most specific stable source locator available, not the generated database ID.

Initial natural-key rules:

- document revision: `jurisdiction`, `bylaw_name`, `source_document_path`, revision label or source manifest extraction identity, and document family `current` or `draft`
- source file: document revision plus repository-relative JSON file path
- bylaw part or document section: document revision plus logical document type, zone code or document label, raw section label, raw title, citation page range, and source order as a tie-breaker
- clause: parent section natural key plus raw clause label, normalized clause path, citation page range, source order, and raw clause text hash as a tie-breaker
- definition: document revision plus normalized term key, raw term, citation page range, and raw definition text hash
- table, row, and cell: parent section natural key plus table title or table ID, row order, column ID, and raw cell text hash where needed
- structured requirement, numeric value, use, term, group, and relationship: document revision plus source reference target, raw label or raw text, structured type, applicability, and normalized value payload hash
- spatial links: spatial layer key plus feature key plus target bylaw document revision and zone or map-reference key

The importer must compute a deterministic content hash for each imported logical record after dropping volatile fields, including generated surrogate IDs, source-file load timestamps, `review_flags`, and `confidence`. Import batches classify records as `added`, `removed`, `changed`, or `unchanged` by comparing natural keys and content hashes against the prior active import for the same document family and source revision. Changed draft records supersede prior active rows; unchanged records may retain the prior row version linkage.

## Manual Corrections

Manual corrections must be stored separately from imported facts. A correction record must include correction type, target table, target natural key, target content hash at the time of correction, patch payload, author or source label, status, reason, created import batch, last evaluated import batch, and optional replacement target key.

Accepted correction statuses are `active`, `needs_re_evaluation`, `reapplied`, `superseded`, and `rejected`. Corrections apply after raw import and before comparison or vector generation. If the target natural key still exists and its content hash is unchanged, the correction can be reapplied automatically. If the natural key exists but the hash changed, or if only a replacement target key can be found, the correction must be marked `needs_re_evaluation`. If the target key is absent and no replacement target is known, the correction remains preserved but inactive for that import batch.

## Section Topics and Equivalence

The first section-topic vocabulary is owned by the `zoning` schema seed data, not by generated source JSON. Initial topics may be assigned from document type, zone code, section title, raw labels, and structured requirement categories. Topic assignment must preserve the raw section title and store the assigned controlled topic separately.

`section_equivalence` must store current section key, draft section key, candidate method, similarity scores when available, assigned topic, review status, reviewer notes, and accepted equivalence type. Accepted review statuses are `candidate`, `accepted`, `rejected`, and `needs_review`. Accepted equivalence types are `same_topic`, `renamed_or_restructured`, `partial_overlap`, `current_deferred`, and `not_equivalent`.

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

Spatial ingestion must pin each approved layer to a source path or database source before coding. The draft Schedule A derived source currently available in repository artifacts is `data/spatial/charlottetown/charlottetown-draft-map-layers-2026-04-09-municipal-fit.gpkg`, summarized by `data/spatial/charlottetown/charlottetown-draft-map-layers-2026-04-09-municipal-fit.summary.json`; its target CRS is `EPSG:2954`. The layer contracts for v1 must name source path or database connection, source layer/table, primary feature key, geometry column, expected geometry type, SRID, zone-code or feature-code field, feature-count baseline, invalid-geometry count, and code crosswalk table.

Spatial loading must not silently repair geometry. Invalid geometries are either loaded into a diagnostic table with their original geometry and validation reason, or repaired through an explicit pre-load step that writes the repair method and before/after validity counts. The known `H` to `HI` draft code mismatch and current no-hyphen to hyphenated map-code mappings must be represented as crosswalk rows, not hard-coded only in importer logic.

## Vector Scope

Vector support is text-first. Embed clauses, definitions, requirements, table-row summaries, map-reference summaries, relationship summaries, and section-equivalence summaries only after stable relational row IDs exist.

Vectors are for semantic retrieval, candidate section equivalence, draft update diff assistance, related-provision discovery, and current-vs-draft comparison support. They are not legal truth or spatial truth. Relational joins and PostGIS remain authoritative. Geometry vectors are out of scope for v1.

## Milestones

1. Complete: design and create the `zoning` schema, import-batch model, document-revision model, coverage-gap table, and section-topic vocabulary.
2. Complete: build initial JSON ingestion for current and draft records, excluding process fields and preserving granular raw reconstruction records.
3. Active next milestone: add review-status reporting and begin manual review for comparable current and draft bylaw sections. The first candidate method, `title_topic_token_v1`, is implemented, tuned, and populated.
4. Pending: register and validate the approved spatial layers, resolve code mismatches, and link spatial features to zones and map references.
5. Pending: add text-vector support after relational IDs and comparison records are stable.
6. Pending: normalize and ingest deferred current-bylaw chapters and appendices, then re-run equivalence and comparison outputs.

Track phase progress in `plan/charlottetown-unified-zoning-ingestion-timeline.md`.

## Acceptance Checks

Implementation is ready to begin when the schema and importer design can satisfy these checks:

- No ingested `review_flags`, `confidence` fields, full-file raw JSON blobs, or top-level aggregate raw text.
- Field-to-table mapping exists for every source JSON family and every accepted `structured_data` array, including explicit deferrals.
- Imported logical records have stable natural keys and deterministic content hashes, and a rerun against unchanged inputs reports unchanged records rather than duplicates.
- Manual corrections replay automatically only when the target natural key and content hash still match; changed targets are marked `needs_re_evaluation`.
- Current combined general-provision sections and draft split general-provision sections query through the same `section` and `clause` interfaces.
- Comparison views distinguish accepted equivalence, unresolved equivalence, true additions/removals, and deferred current coverage.
- Import batches preserve prior draft versions and can report added, removed, changed, and unchanged draft records.
- Coverage gaps suppress missing-current comparison differences only for their declared logical units.
- Spatial inventory is limited to the approved layers and validates source paths, feature counts, SRIDs, geometry types, invalid geometry counts, code crosswalks, and zone-code joins.
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
- [Unified zoning ingestion timeline](../../../plan/charlottetown-unified-zoning-ingestion-timeline.md)
- [Unified zoning migration](../../../schema/sql/005_charlottetown_unified_zoning.sql)
- [Charlottetown zoning importer](../../../scripts/import-charlottetown-zoning.py)
