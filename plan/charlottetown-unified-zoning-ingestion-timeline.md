# Charlottetown Unified Zoning Ingestion Timeline

Reference plan: `wiki/charlottetown/topics/unified-zoning-ingestion-plan.md`

## Status Summary

- Active phase: 4
- Active phase name: Spatial Registration and Linkage
- Overall status: In progress
- Current progress: Phases 1 through 3 are complete. The `zoning` schema migration exists at `schema/sql/005_charlottetown_unified_zoning.sql`, the initial importer exists at `scripts/import-charlottetown-zoning.py`, and the database has populated current and draft bylaw relational-core records. Draft import batch 34 loaded the rebaseline draft outputs with 34 source files, 259 sections, 2,095 clauses, 49 raw tables, 654 raw table cells, 33 raw map references, and 2,509 structured facts. Phase 3 ledger-first manual review has been applied to `zoning.section_equivalence`; the database now has 88 accepted rows, 49 rejected `not_equivalent` rows, and 0 `candidate` or `needs_review` rows. After batch 34, 8 stale draft section-equivalence pointers were updated to their active draft section replacements, leaving 0 inactive current or draft section links. The next active work is Phase 4 spatial registration and linkage.
- Last updated: 2026-04-29

## Phase Timeline

| Phase | Name | Scope | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| 0 | Validation Baseline | Confirm current and draft JSON outputs are ready for unified ingestion planning. | Complete | Current and draft generated outputs have 0 non-empty `review_flags` arrays and 0 `confidence: "needs_review"` entries. |
| 1 | Schema and Importer Design | Design and create the `zoning` schema, import-batch model, document-revision model, coverage-gap table, manual-correction table, section-topic vocabulary, and spatial linkage tables. | Complete | Migration creates the planned `zoning` tables and seed records needed for repeatable current and draft ingestion. |
| 2 | Initial JSON Ingestion | Import current and draft bylaw JSON into relational-core, raw reconstruction, and structured-fact tables while excluding `review_flags`, `confidence`, full JSON blobs, and top-level aggregate raw text. | Complete | Completed current and draft import batches exist and core bylaw tables are populated without relying on full-file JSON storage. |
| 3 | Section Equivalence | Build current-versus-draft section-equivalence candidate generation and manual review storage. | Complete | `zoning.section_equivalence` contains candidate records with method, topic, review status, and equivalence type fields populated for comparable current and draft sections. |
| 4 | Spatial Registration and Linkage | Register approved spatial layers, validate layer contracts, resolve code mismatches, and link spatial features to zones and map references. | Active | Approved spatial layers are represented with source contracts, feature counts, CRS, geometry diagnostics, code crosswalks, and zone/map-reference links. |
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
- `zoning.section_equivalence` contains 137 tuned `title_topic_token_v1` rows with ledger decisions applied in the database: 76 accepted `same_topic`, 10 accepted `renamed_or_restructured`, 2 accepted `partial_overlap`, and 49 rejected `not_equivalent`. No database rows remain marked `candidate` or `needs_review`.
- after draft batch 34, section-equivalence rows 208, 217, 220, 221, 224, 225, 260, and 301 had stale inactive `draft_section_id` pointers; each was updated to the active section resolved by `draft_section_key`
- post-repair verification found 0 missing current or draft section IDs, 0 inactive current or draft section IDs, 0 missing active current or draft natural-key targets, and 0 section ID/key mismatches
- tuning checks matched all 70 exact-title current/draft controls and removed sampled weak false positives from the first candidate set
- `zoning.coverage_gap`, `zoning.spatial_layer`, `zoning.spatial_feature`, `zoning.zone_spatial_feature`, and `zoning.spatial_reference` currently have 0 rows

Phase result:

- Section-equivalence candidate generation, ledger review, and database application are complete for the tuned `title_topic_token_v1` set.
- Draft rebaseline import batch 34 is complete, and section-equivalence pointers resolve to active current and draft sections.

Next actions:

1. Add review-status reporting for accepted and rejected candidates when comparison reporting work starts.
2. Revisit candidate generation after manual review identifies accepted false negatives or recurring false-positive classes.
3. Register and validate the approved spatial layers for Phase 4.

## Progress Rules

- Update `Status Summary` whenever the active phase or overall status changes.
- Update `Current Phase Detail` whenever work starts, pauses, or completes within the active phase.
- Mark a phase `Complete` only when its exit criteria are met.
- Keep future phases `Pending` until they become active.
- If work is blocked, set `Overall status` to `Blocked` and record the blocker under the active phase.

## Completion Condition

This timeline remains active until Phase 6 is complete or the unified ingestion plan is superseded by a later approved plan.
