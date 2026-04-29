# Charlottetown Unified Zoning Ingestion Timeline

Reference plan: `wiki/charlottetown/topics/unified-zoning-ingestion-plan.md`

## Status Summary

- Active phase: 3
- Active phase name: Section Equivalence
- Overall status: In progress
- Current progress: Phases 1 and 2 are complete. The `zoning` schema migration exists at `schema/sql/005_charlottetown_unified_zoning.sql`, the initial importer exists at `scripts/import-charlottetown-zoning.py`, and the database has populated current and draft bylaw relational-core records. Draft import batch 34 loaded the rebaseline draft outputs with 34 source files, 259 sections, 2,095 clauses, 49 raw tables, 654 raw table cells, 33 raw map references, and 2,509 structured facts. Phase 3 was reopened after QA found accepted section-equivalence mismatches and blank-side comparisons. The generator now compares clause text plus linked table-cell text, the prior reviewed `title_topic_token_v1` rows were reset, and `zoning.section_equivalence` now contains 139 regenerated `candidate` rows with 0 accepted rows and 0 blank-side candidate rows. The next active work is manual review of the regenerated section-equivalence ledger.
- Last updated: 2026-04-29

## Phase Timeline

| Phase | Name | Scope | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| 0 | Validation Baseline | Confirm current and draft JSON outputs are ready for unified ingestion planning. | Complete | Current and draft generated outputs have 0 non-empty `review_flags` arrays and 0 `confidence: "needs_review"` entries. |
| 1 | Schema and Importer Design | Design and create the `zoning` schema, import-batch model, document-revision model, coverage-gap table, manual-correction table, section-topic vocabulary, and spatial linkage tables. | Complete | Migration creates the planned `zoning` tables and seed records needed for repeatable current and draft ingestion. |
| 2 | Initial JSON Ingestion | Import current and draft bylaw JSON into relational-core, raw reconstruction, and structured-fact tables while excluding `review_flags`, `confidence`, full JSON blobs, and top-level aggregate raw text. | Complete | Completed current and draft import batches exist and core bylaw tables are populated without relying on full-file JSON storage. |
| 3 | Section Equivalence | Build current-versus-draft section-equivalence candidate generation and manual review storage. | Active | `zoning.section_equivalence` contains candidate records with method, topic, review status, and equivalence type fields populated for comparable current and draft sections, and reviewed accepted rows have no blank-side comparisons. |
| 4 | Spatial Registration and Linkage | Register approved spatial layers, validate layer contracts, resolve code mismatches, and link spatial features to zones and map references. | Pending | Approved spatial layers are represented with source contracts, feature counts, CRS, geometry diagnostics, code crosswalks, and zone/map-reference links. |
| 5 | Text Vector Support | Add text-vector support after stable relational IDs and comparison records exist. | Pending | Vector rows link back to authoritative relational records and support retrieval, equivalence assistance, and comparison workflows. |
| 6 | Deferred Current Coverage | Normalize and ingest deferred current-bylaw chapters and appendices, then re-run equivalence and comparison outputs. | Pending | Deferred coverage gaps are resolved or intentionally retained, and comparison outputs distinguish true changes from deferred current coverage. |

## Current Phase Detail

### Phase 3: Section Equivalence

Objective:

- generate candidate equivalence records between current and draft bylaw sections
- preserve manual review state in `zoning.section_equivalence`
- distinguish accepted equivalence, unresolved equivalence, true additions/removals, and deferred current coverage

Inputs:

- populated `zoning.bylaw_document`, `zoning.document_revision`, `zoning.source_file`, `zoning.bylaw_part`, `zoning.section`, `zoning.clause`, `zoning.structured_fact`, and `zoning.section_topic`
- current extraction outputs under `data/zoning/charlottetown`
- draft extraction outputs under `data/zoning/charlottetown-draft`
- plan context in `wiki/charlottetown/topics/unified-zoning-ingestion-plan.md`

Current evidence:

- database table inventory confirms the planned `zoning` schema tables exist
- current and draft import batches are completed; latest draft rebaseline import is batch 34, completed on 2026-04-29
- populated active draft counts after batch 34 include 34 source files, 34 bylaw parts, 259 sections, 2,095 clauses, 357 definitions, 34 source units, 4 raw pages, 49 raw tables, 654 raw table cells, 33 raw map references, and 2,509 structured facts
- `zoning.section_equivalence` contains 139 regenerated `title_topic_token_v1` candidate rows after the generator was repaired to include linked table-cell text and to skip blank-side comparisons. The prior reviewed rows were reset because QA found accepted mismatches and blank-side comparisons.
- after draft batch 34, section-equivalence rows 208, 217, 220, 221, 224, 225, 260, and 301 had stale inactive `draft_section_id` pointers; each was updated to the active section resolved by `draft_section_key`
- post-rerun verification found 0 accepted rows, 139 candidate rows, and 0 blank-side candidate rows
- tuning checks matched all 70 exact-title current/draft controls and removed sampled weak false positives from the first candidate set
- `zoning.coverage_gap`, `zoning.spatial_layer`, `zoning.spatial_feature`, `zoning.zone_spatial_feature`, and `zoning.spatial_reference` currently have 0 rows

Phase result:

- Section-equivalence candidate generation has been rerun for the repaired `title_topic_token_v1` set.
- Ledger review and database application are reopened because prior accepted decisions were reset.

Next actions:

1. Review the 139 regenerated section-equivalence candidates in `data/zoning/charlottetown-draft/review/section-equivalence-review.csv`.
2. Apply accepted and rejected ledger decisions to `zoning.section_equivalence`.
3. Register and validate the approved spatial layers for Phase 4 after Phase 3 review is closed.

## Progress Rules

- Update `Status Summary` whenever the active phase or overall status changes.
- Update `Current Phase Detail` whenever work starts, pauses, or completes within the active phase.
- Mark a phase `Complete` only when its exit criteria are met.
- Keep future phases `Pending` until they become active.
- If work is blocked, set `Overall status` to `Blocked` and record the blocker under the active phase.

## Completion Condition

This timeline remains active until Phase 6 is complete or the unified ingestion plan is superseded by a later approved plan.
