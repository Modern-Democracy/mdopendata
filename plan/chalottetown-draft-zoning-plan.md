# Charlottetown Draft Zoning Validation and Normalization Plan

## Objective

Complete source-level validation and normalization of the regenerated Charlottetown draft zoning bylaw outputs under `data/zoning/charlottetown-draft`, with explicit resolution of all `review_flags` and all structured entries marked `confidence: "needs_review"`.

## Scope

In scope:

- `data/zoning/charlottetown-draft/**/*.json`
- `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`
- `data/zoning/charlottetown-draft/code-table-match-report.json`
- `data/zoning/charlottetown-draft/source-manifest.json`
- `scripts/regenerate-charlottetown-draft-zoning-bylaw.py` only as a reference for regeneration and revalidation workflow

Out of scope unless separately approved:

- Schema changes
- New helper modules or workflow changes
- Map digitizing or spatial layer production beyond documenting schedule-map QA requirements
- Changes to current Charlottetown outputs under `data/zoning/charlottetown`

## Current QA Baseline

As of the regenerated draft outputs dated 2026-04-23:

- 33 JSON files contain `review_flags`
- 139 total `review_flags` remain open
- 26 JSON files contain at least one `confidence: "needs_review"` entry
- 130 total `needs_review` entries remain in structured data

Review-flag distribution:

- `code_table_match_review`: 52
- `extraction_review`: 29
- `table_parsing_review`: 24
- `zone_boundary_review`: 18
- `section_assignment_review`: 9
- `schedule_map_review`: 4
- `layout_order_review`: 3

Highest `needs_review` concentration:

1. `data/zoning/charlottetown-draft/zones/rm.json` with 12
2. `data/zoning/charlottetown-draft/general-provisions-parking.json` with 11
3. `data/zoning/charlottetown-draft/general-provisions-land-use.json` with 10
4. `data/zoning/charlottetown-draft/zones/rh.json` with 9
5. `data/zoning/charlottetown-draft/zones/dms.json` with 9
6. `data/zoning/charlottetown-draft/zones/ap.json` with 8
7. `data/zoning/charlottetown-draft/zones/bp.json` with 7
8. `data/zoning/charlottetown-draft/zones/rn.json` with 7

## Validation Principles

- Validate against the visual PDF, not extracted text order alone.
- Preserve approved schema shape.
- Preserve raw clause labels exactly as written in source.
- Normalize only when the source clause, term, use, or numeric value is unambiguous.
- Keep any unresolved ambiguity visible through narrowly scoped review records until resolved.
- Treat code-table normalization, clause assignment, and schedule-map QA as separate decision tracks.

## Workstreams

### 1. Inventory and Triage

Create a working issue ledger for every open item from:

- top-level `review_flags`
- all structured records with `confidence: "needs_review"`
- all unmatched phrases in `code-table-match-report.json`

For each item, record:

- file
- clause or object id
- source PDF page range
- issue class
- proposed disposition
- reviewer status

Issue classes:

- code-table normalization
- clause text cleanup
- numeric normalization
- section assignment
- table or figure parsing
- zone boundary spillover
- schedule-map QA

### 2. Code-Table Normalization

Resolve all `code_table_match_review` items first because they affect downstream comparability between current and draft zoning.

Tasks:

1. Review all semantic matches and confirm they are acceptable reuse of existing codes.
2. Review all `new_codes` candidates from `code-table-match-report.json`.
3. Decide for each unmatched phrase whether to:
   - map to an existing reviewed code
   - create a new reviewed draft code if the concept is materially distinct
   - mark as non-use or non-term text that should be removed from structured term or use arrays
4. Apply the same decision consistently across all files containing the same phrase variant.

Priority phrases already surfaced:

- `Cluster Housing`
- `Multi-unit Dwelling`
- `Seniors Housing`
- `Tourist Accommodation`
- `Parking Lot / Structure`
- `Hostel / Hotel`
- `Warehouse, Storage Facility and/or Distribution Centre`
- `Single Detached Dwelling (up to 4 units)`
- `Semi Detached or Duplex Dwelling`

Specific check:

- `Existing uses` and the long sentence preserved in `zones/ue.json` are likely extraction artifacts or misclassified use text and should be validated before any code creation.

### 3. Clause and Requirement Validation

Resolve all structured records with `confidence: "needs_review"`.

For each flagged requirement, confirm:

- the clause belongs in the current section
- the clause label path is correct
- extracted numeric values match the source formatting and meaning
- the record type is correct for the clause
- `requirement_category` is acceptable, or should be rewritten by rerunning normalization after source cleanup

Common defect patterns already visible:

- dimensional text merged into prose, such as `3 m 2`
- site-design and landscaping clauses that may have lost superscript or unit formatting
- intent statements incorrectly preserved as structured requirements
- permitted-use line items stored as `other_requirements` instead of normalized use rows

### 4. Section Assignment and Layout Repair

Resolve `extraction_review`, `layout_order_review`, `zone_boundary_review`, and `section_assignment_review` items by checking PDF layout against the extracted clause order.

Tasks:

1. Review `content_blocks`, `source_units`, and nearby clause arrays for spillover text.
2. Confirm section boundaries where pypdf likely crossed columns, tables, or figures.
3. Remove or reassign text that was preserved in the wrong section.
4. Re-run normalization after each file-level source correction.

Initial file priority for this work:

- `zones/rn.json`
- `zones/rm.json`
- `zones/rh.json`
- `administration.json`
- `general-provisions-parking.json`
- `general-provisions-land-use.json`
- `general-provisions-signage.json`

### 5. Table, Figure, and Schedule Review

Resolve `table_parsing_review` and `schedule_map_review` separately from textual clauses.

Tasks for table and figure content:

1. Identify whether each affected clause is a table row, figure note, legend item, or ordinary text.
2. Confirm whether the current schema can represent the provision without distortion.
3. If it can, normalize the clause into existing numeric or requirement structures.
4. If it cannot, preserve the clause in raw form and document the limitation explicitly for later approved schema or workflow work.

Tasks for schedules:

1. Confirm each schedule JSON is page-text only.
2. Verify titles, citations, and map references against the PDF.
3. Keep `schedule_map_review` open until spatial QA inputs exist.
4. Do not treat schedule page text as parcel-ready zoning data.

## Recommended Execution Order

1. Build the issue ledger from all draft JSON outputs.
2. Resolve code-table decisions for repeated unmatched phrases.
3. Validate the highest-density `needs_review` files.
4. Repair section assignment and layout-order defects in the same files while the PDF pages are already open.
5. Re-run regeneration and schema validation after each completed batch.
6. Recompute counts of `review_flags`, `needs_review`, and unmatched code-table phrases.
7. Review lower-density files.
8. Close with schedule-map QA status and remaining known limits.

## File Batching Strategy

Batch 1:

- `zones/rn.json`
- `zones/rm.json`
- `zones/rh.json`
- `zones/dms.json`

Reason:

- highest overlap of unmatched residential use phrases plus layout-risk indicators

Batch 2:

- `general-provisions-parking.json`
- `general-provisions-land-use.json`
- `general-provisions-buildings-structures.json`
- `general-provisions-signage.json`

Reason:

- highest supporting-document concentration of `needs_review` and table/layout risk

Batch 3:

- `zones/ap.json`
- `zones/bp.json`
- `zones/dc.json`
- `zones/dmu.json`
- `zones/dw.json`
- `zones/gn.json`

Reason:

- medium-density unresolved items with commercial and mixed-use code-table decisions

Batch 4:

- all remaining zone and supporting files with 3 or fewer `needs_review` items
- all schedule files

## Resolution Rules

Close a `review_flag` only when one of the following is true:

- the source was checked and the structured data was corrected
- the source was checked and the flagged content was intentionally preserved as valid
- the issue was reclassified into a narrower remaining review item

Change `confidence: "needs_review"` only when:

- the clause text matches the source
- the clause is assigned to the correct schema object
- numeric values and units are confirmed
- term and use normalization are confirmed where applicable

Do not close review items by deleting evidence without recording why the item is resolved.

## Acceptance Criteria

The draft validation and normalization pass is complete when:

1. Every file under `data/zoning/charlottetown-draft` has been reviewed against the source PDF.
2. All false-positive or outdated `review_flags` have been removed.
3. All resolvable `confidence: "needs_review"` entries have been corrected or promoted to confirmed confidence.
4. All remaining open review items are intentional, specific, and documented as true residual limits.
5. `code-table-match-report.json` reflects final reviewed code decisions.
6. Regenerated outputs validate against `schema/json-schema/charlottetown-bylaw-extraction.schema.json`.
7. A final QA summary records:
   - files reviewed
   - flags resolved
   - flags intentionally retained
   - new or reused normalized codes
   - residual schedule-map limitations

## Deliverables

- Updated normalized JSON outputs under `data/zoning/charlottetown-draft`
- Updated `code-table-match-report.json`
- Updated `source-manifest.json` if regeneration changes coverage metadata
- Final QA summary document with before and after counts

## Residual Risks to Watch

- Repeated residential use phrases may represent either real new concepts or formatting variants of existing reviewed codes.
- Table and figure text may continue to leak into clause text if fixes are applied only at the normalized layer.
- Schedule pages are not yet parcel-comparison-ready and should not be treated as validated spatial zoning inputs.
- Some broad intent statements may have been normalized as enforceable requirements and must be checked clause by clause.
