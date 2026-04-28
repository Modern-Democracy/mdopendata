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

## 2026-04-24 Plan Review Addendum

The 2026-04-23 baseline remains useful as the original validation baseline, but it is no longer the active inventory baseline after the parser and layout repairs that added or restored many clauses and sections.

Current generated-output marker counts from `data/zoning/charlottetown-draft/**/*.json` after the 2026-04-24 ledger refresh:

- 33 JSON files contain `review_flags`
- 158 total `review_flags` are present
- 22 JSON files contain at least one `confidence: "needs_review"` entry
- 86 total `needs_review` entries are present
- 0 unmatched code-table `new_codes` entries are present

Current `review_flags` by `review_type`:

- `numeric_value_review`: 94
- `extraction_review`: 29
- `table_parsing_review`: 24
- `section_assignment_review`: 4
- `schedule_map_review`: 4
- `layout_order_review`: 3

Highest current `needs_review` concentration:

1. `data/zoning/charlottetown-draft/general-provisions-parking.json` with 13
2. `data/zoning/charlottetown-draft/zones/dw.json` with 8
3. `data/zoning/charlottetown-draft/general-provisions-land-use.json` with 7
4. `data/zoning/charlottetown-draft/general-provisions-signage.json` with 6
5. `data/zoning/charlottetown-draft/design-standards-500-lot-area.json` with 5
6. `data/zoning/charlottetown-draft/zones/dms.json` with 5
7. `data/zoning/charlottetown-draft/zones/dmu.json` with 5
8. `data/zoning/charlottetown-draft/zones/dc.json`, `zones/i.json`, and `zones/rn.json` with 4 each

Plan adjustment:

- Treat Phase 1 as refreshed for the current regenerated outputs in `plan/chalottetown-draft-zoning-issue-ledger.csv`.
- Treat Phase 2 as complete for current code-table drift because `code-table-match-report.json` now has 0 `term.new_codes` and 0 `use.new_codes`.
- Keep Phase 3 active, with `general-provisions-parking.json` and `general-provisions-land-use.json` remaining in the high-priority batch.
- Keep Phase 4 pending, but recognize that targeted layout-repair tasks have already been performed inside the Phase 3 parser-fix work. Phase 4 should begin with a regression review of those repaired sections before widening to remaining layout issues.
- Continue monitoring for new extraction defects after each regeneration. Any increase in `review_flags`, `needs_review`, unmatched code-table phrases, or section-count drift must update this plan and the timeline before further closure claims.

## 2026-04-28 Phase 4 Triage Addendum

Phase 4 is active after Phase 3 closed all current `confidence: "needs_review"` entries.

Remaining open `review_flag` rows in `plan/chalottetown-draft-zoning-issue-ledger.csv`:

- `numeric_value_review`: 38 rows
- `extraction_review`: 29 rows
- `table_parsing_review`: 24 rows
- `section_assignment_review`: 0 rows
- `schedule_map_review`: 4 rows
- `layout_order_review`: 3 rows

Triage disposition:

- Treat `layout_order_review` rows in `zones/rn.json`, `zones/rm.json`, and `zones/rh.json` as the first visual PDF regression batch because these files share the known dimensional-table and figure-placement risk pattern.
- The first explicit section-assignment batch is complete for `design-standards-500-lot-area.json`, `general-provisions-buildings-structures.json`, `general-provisions-lots-site-design.json`, and `general-provisions-signage.json`; all four now have zero raw `content_blocks` and zero `section_assignment_review` flags.
- Treat the 38 remaining `numeric_value_review` rows as table-cell normalization review, not primary section-boundary repair.
- Treat the 29 `extraction_review` and 24 `table_parsing_review` rows as broad file-level legacy warnings unless source-page inspection identifies a concrete wrong-section, wrong-order, figure-bleed, or table-placement defect.
- Retain Schedules A through D `schedule_map_review` rows until Phase 5 or later spatial QA documents the schedule-map limitations.

Buildings and Structures numeric-cell update:

- The Phase 4 Buildings and Structures numeric-cell pass is complete for `general-provisions-buildings-structures.json`.
- Current draft Table 3.1 and Table 3.2 IDs are now recognized as general-provisions requirement tables during regeneration.
- Valid Buildings and Structures descriptor cells, `YES`, and `Unlimited` table values no longer produce `numeric_value_review` flags.
- `general-provisions-buildings-structures.json` now has zero `numeric_value_review` rows; only its broad `extraction_review` and `table_parsing_review` rows remain open.
