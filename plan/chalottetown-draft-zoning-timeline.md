# Charlottetown Draft Zoning Validation Timeline

Reference plan: `plan/chalottetown-draft-zoning-plan.md`

## Status Summary

- Active phase: Phase 4
- Active phase name: Section and Layout Repair
- Overall status: In progress
- Current progress: Phase 1 has been refreshed from current regenerated outputs in `plan/chalottetown-draft-zoning-issue-ledger.csv`; after the Phase 4 RN/RM/RH layout-order closure, the ledger contains 4 open rows: 4 `review_flag` rows and 0 `needs_review` rows. Phase 2 is complete for the approved 2026-04-23 code-table normalization pass and the 2026-04-24 `use.new_codes` drift check. The code-table match report previously listed 25 `use.new_codes`; the reconciliation classified `Cluster Housing` and `Seniors Housing` as true draft-origin use codes, mapped renamed or compound phrases to existing codes, removed dimensional/header/pseudo-use artifacts from queryable terms, and regenerated the report with 0 `use.new_codes`, 11 `use.semantic_matches`, and 97 `use.exact_matches`. Phase 3 is complete for all current `confidence: "needs_review"` entries. Phase 4 is active for section, layout, table, figure, and residual review-flag validation. Targeted layout-repair passes have already been applied in the draft extractor for RM-style figure/table bleed and the named Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7, and Part 8 general-provisions parsing defects. Regenerated draft outputs now restore the missing RM `11.3.2`, `11.3.3`, `11.5`, and `11.6` clause structure, promote equivalent dimensional requirement blocks into `tables_raw`, repair draft Tables 3.1, 3.2, 3.3, 4.1, and 4.2 placement, split or reassign the reported clauses in sections `1.6`, `2.11`, `2.18`, `2.19`, `3.1`, `3.16`, `3.19`, `4.5`, `4.6`, `4.7`, `5.2`, `7.10`, and `7.11`, restore wrapped title continuations in sections `1.6`, `1.14`, `2.1`, `2.9`, `2.11`, `4.14`, `4.16`, `4.17`, `5.4`, `5.6`, `5.8`, `6.3`, `7.3`, `7.4`, `7.8`, `7.12`, and `7.13`, reorder or reparent the reported `7.3` and `7.5` clauses, correct the Part 2/Part 3 extraction boundary so section `2.19` is generated in `permit-applications-processes.json` rather than `general-provisions-buildings-structures.json`, repair Part 8 parking section assignment, clause tails, and bicycle-parking section splits for `8.4`, `8.5`, `8.7`, `8.8`, `8.12`, `8.13`, and `8.14`, remove DMU clause `15.6.1` figure/dimensional bleed, remove source figure bleed from general-provisions clause `3.9.1(a)` and RN clause `10.6.2`, and restore the truncated BP clause `18.6.13`. Phase 4 has completed the RN/RM/RH layout regression and residual layout-order closure, four explicit section-assignment reviews, the Buildings and Structures numeric-cell batch, the lower-density numeric-cell batch, and the broad extraction/table-parsing review; remaining review flags are 0 numeric table-cell normalization rows, 0 broad extraction-review rows, 0 broad table-parsing rows, 4 schedule-map QA rows, 0 section-assignment rows, and 0 layout-order rows.
- Last updated: 2026-04-28

## Phase Timeline

| Phase | Name | Scope | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| 0 | Plan Baseline | Establish validation plan, scope, priorities, and acceptance criteria. | Complete | `plan/chalottetown-draft-zoning-plan.md` approved as working reference. |
| 1 | Inventory and Triage | Build the master issue ledger from all open `review_flags`, all `confidence: "needs_review"` records, and all unmatched code-table phrases. Classify each item by issue class, source location, and proposed disposition. | Complete for current regenerated outputs | Complete issue ledger exists and every current open item is cataloged with file, object id, source citation, issue class, and status. |
| 2 | Code-Table Normalization | Resolve repeated unmatched term and use phrases, confirm semantic matches, and decide reuse versus new reviewed codes versus extraction-artifact removal. | Complete | All current draft code-table decisions are consistent across files and `code-table-match-report.json` reflects reviewed outcomes. |
| 3 | High-Priority Clause Validation | Validate and normalize the highest-density `needs_review` files and resolve clause text, numeric, and record-type defects. Initial file group: `zones/rn.json`, `zones/rm.json`, `zones/rh.json`, `zones/dms.json`, `general-provisions-parking.json`, `general-provisions-land-use.json`. | Complete | High-priority files no longer contain unresolved `needs_review` entries except documented true residual limits. |
| 4 | Section and Layout Repair | Resolve extraction-order, section-assignment, zone-boundary, and table or figure bleed defects by checking the visual PDF against normalized outputs. | Active | Targeted files have corrected section assignment and only justified residual extraction reviews remain. |
| 5 | Remaining Files and Schedule Review | Review lower-density files and confirm the schedule JSON files remain page-text artifacts with explicit downstream limits. | Pending | Remaining files are reviewed, residual schedule-map limitations are explicit, and low-density issues are closed or intentionally retained. |
| 6 | Regeneration and Final QA | Re-run regeneration and schema validation, recompute counts, verify resolved items, and write the final QA summary. | Pending | Acceptance criteria from `plan/chalottetown-draft-zoning-plan.md` are met. |

## Current Phase Detail

### Phase 4: Section and Layout Repair

Objective:

- validate remaining open `review_flag` rows after Phase 3 eliminated all current `confidence: "needs_review"` records
- separate broad legacy review warnings from actionable section, layout, table, figure, and residual numeric issues

Required outputs:

- repaired or intentionally retained section, layout, table, figure, and numeric review flags
- updated draft JSON outputs and timeline tracking for each Phase 4 batch
- residual flags narrowed to true source, schema, schedule-map, or spatial-QA limits

Inputs:

- `plan/chalottetown-draft-zoning-issue-ledger.csv`
- `data/zoning/charlottetown-draft/**/*.json`
- `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`

Current progress:

- issue ledger created at `plan/chalottetown-draft-zoning-issue-ledger.csv`
- ledger counts verified against the plan baseline: 139 `review_flags`, 130 `needs_review` records, 16 unmatched code-table phrases
- Phase 1 exit criteria satisfied
- Phase 2 code-table normalization applied across the affected draft zone files
- combined-use labels were split where approved, condition-bearing pseudo-codes were reduced to base use codes, and extraction-artifact pseudo-codes were removed from use tables
- the approved Phase 2 review pass treated only `Cluster Housing` and `Seniors Housing` as true remaining new-code candidates
- Phase 3 opened with the high-priority clause-validation batch as the next active workstream
- the remaining clause-level `other_requirements` `needs_review` entries in `zones/rn.json`, `zones/rm.json`, `zones/rh.json`, and `zones/dms.json` were reviewed against the draft PDF and promoted from `needs_review`
- direct numeric artifacts tied to those reviewed clauses were normalized where the PDF gave an unambiguous unit or comparator
- matching issue-ledger requirement rows for this batch were closed
- `scripts/extract-charlottetown-draft-zoning-bylaw.py` now uses coordinate-aware page blocks to preserve visual reading order, carry page-leading continuation text into the prior active section, and suppress obvious figure and table caption spillover
- `data/zoning/charlottetown-draft/zones/rm.json` was regenerated with `11.1` intent text cleaned, `11.3.2` and `11.3.3` restored under `11.3`, and `11.5` continuation text preserved before `11.6`
- a negative-control regeneration check on `zones/dms.json`, `zones/dmu.json`, and `zones/dw.json` did not reproduce the RM-style figure or table bleed in requirement text
- `scripts/extract-charlottetown-zoning-bylaw.py` now promotes RM-style dimensional clause groups into section tables generically for draft zone outputs, instead of limiting that repair to `RM`
- `scripts/extract-charlottetown-zoning-bylaw.py` now applies targeted draft general-provisions repairs for the named Part 3, Part 4, and Part 5 section-order, table-placement, and inline-clause defects
- regenerated draft outputs move `2.19(d-g)` to `3.1.2(d-g)`, insert Tables 3.1, 3.2, 3.3, and 4.1 after their applicable clauses, restore `3.19.2(c-i)` and `3.19.3(d-g)`, split `4.6` out of `4.5`, and split `5.2.2(a-b)`
- `scripts/extract-charlottetown-zoning-bylaw.py` now also merges the newly reported wrapped title continuations, inserts Table 4.2 under `4.11`, reorders `7.3.2(a-i)`, moves `7.5.1(e)(iv-ix)` out of `7.4`, and splits `7.10` and `7.11` out of `7.9`
- follow-up title-continuation repairs now merge `ATTACHED` into `4.6 ACCESSORY DWELLING UNITS, ATTACHED` and `SERVICES:` into `7.10 WATER, SEWER, AND OTHER SERVICES:`
- `scripts/regenerate-charlottetown-draft-zoning-bylaw.py` was rerun and completed schema validation for the regenerated draft outputs
- the Part 2/Part 3 boundary in `scripts/extract-charlottetown-draft-zoning-bylaw.py` now keeps bylaw page 16 in Part 2, so section `2.19` is generated in `permit-applications-processes.json` and Part 3 begins at bylaw page 17
- `scripts/extract-charlottetown-draft-zoning-bylaw.py` now preserves multi-line uppercase section titles with commas and applies targeted left-column-before-right-column ordering on draft PDF pages 7, 15, and 19; regenerated outputs repair section/title placement for `1.6`, `1.14`, `2.1`, `2.9`, `2.11`, and `2.18`
- 2026-04-24 plan review found that the current generated outputs have drifted from the baseline ledger after parser repairs: 246 `review_flags`, 174 `needs_review` entries, and 25 `use.new_codes` in the current code-table match report
- Phase 1 must be refreshed for the current generated outputs before additional Phase 3 completion claims
- `Cluster Housing` and `Seniors Housing` were added to the reviewed use code table as true draft-origin use codes
- compound and renamed phrases were normalized through aliases or splits: `Hostel / Hotel`, `Parking Lot / Structure`, `Warehouse, Storage Facility and/or Distribution Centre`, `Transitional Housing`, `Multi-unit Dwelling`, `Multi-Unit Dwellings`, `Tourist Accommodation`, `Semi Detached or Duplex Dwelling`, `Single Detached Dwelling (up to 4 units)`, and the UE permitted-use sentence
- extraction artifacts were removed from queryable use terms: `Existing uses`, RH dimensional requirement text, RH flaglot continuation text, and PPS footer/header bleed
- `data/zoning/charlottetown-draft/code-table-match-report.json` now reports 0 `use.new_codes`
- `plan/chalottetown-draft-zoning-issue-ledger.csv` was refreshed from current regenerated JSON outputs and now catalogs 244 open rows: 158 `review_flag` rows and 86 `needs_review` rows
- the refreshed highest-density `needs_review` files were `general-provisions-parking.json` with 13, `zones/dw.json` with 8, `general-provisions-land-use.json` with 7, and `general-provisions-signage.json` with 6
- the parking and land-use pass repaired Part 8 parking section assignment, clause-tail truncation, figure/table bleed, and `8.12`/`8.13`/`8.14` bicycle-parking splits; `general-provisions-parking.json` and `general-provisions-land-use.json` now contain 0 `needs_review` entries
- `plan/chalottetown-draft-zoning-issue-ledger.csv` now catalogs 224 open rows: 158 `review_flag` rows and 66 `needs_review` rows
- the DW and signage pass reviewed the 14 remaining numeric-clause rows in `zones/dw.json` and `general-provisions-signage.json` against their source clause IDs and promoted the generated requirement confidence to `high`
- `zones/dw.json` and `general-provisions-signage.json` now contain 0 `needs_review` entries
- `plan/chalottetown-draft-zoning-issue-ledger.csv` now catalogs 210 open rows: 158 `review_flag` rows and 52 `needs_review` rows
- the 500 Lot Area, DMS, and DMU pass reviewed 14 numeric-clause rows in `design-standards-500-lot-area.json`, `zones/dms.json`, and `zones/dmu.json` against the draft PDF and promoted the generated requirement confidence to `high`
- `zones/dmu.json` clause `15.6.1` was corrected from `See Section 6.8-6.9 1.5 m` to `See Section 6.8-6.9`, removing the spurious `1.5 m` numeric value and requirement generated from figure/dimensional bleed
- `design-standards-500-lot-area.json`, `zones/dms.json`, and `zones/dmu.json` now contain 0 `needs_review` entries
- `plan/chalottetown-draft-zoning-issue-ledger.csv` now has 195 open rows: 158 `review_flag` rows and 37 `needs_review` rows
- the buildings/structures, BP, DC, I, and RN pass reviewed 20 numeric-clause rows against the draft PDF and promoted confirmed generated requirements to `high`
- `general-provisions-buildings-structures.json` clause `3.9.1(a)` was corrected to remove figure bleed text and the spurious `6.0 m` numeric value from Figure 3.1
- `zones/rn.json` clause `10.6.2` was corrected to remove Figure 10.2 bleed text and the spurious `1.5 m` numeric value
- `zones/bp.json` clause `18.6.13` was restored to the full source sentence from the next PDF page
- `general-provisions-buildings-structures.json`, `zones/bp.json`, `zones/dc.json`, `zones/i.json`, and `zones/rn.json` now contain 0 `needs_review` entries
- `plan/chalottetown-draft-zoning-issue-ledger.csv` now has 175 open rows: 158 `review_flag` rows and 17 `needs_review` rows
- the HI, subdividing land, permit applications, DN, P, and RM pass reviewed 13 numeric-clause rows against the draft PDF and promoted confirmed generated requirements to `high`
- `scripts/extract-charlottetown-zoning-bylaw.py` now applies reviewed draft zone requirement promotion during regeneration, preserving closed BP, DC, I, RN, HI, DN, P, and RM rows after reruns
- `zones/hi.json`, `general-provisions-subdividing-land.json`, `permit-applications-processes.json`, `zones/dn.json`, `zones/p.json`, and `zones/rm.json` now contain 0 `needs_review` entries
- `plan/chalottetown-draft-zoning-issue-ledger.csv` now has 162 open rows: 158 `review_flag` rows and 4 `needs_review` rows
- the final four `needs_review` rows in `general-provisions-lots-site-design.json`, `zones/c.json`, `zones/gn.json`, and `zones/rh.json` were reviewed against the draft PDF and promoted to `high`
- `scripts/extract-charlottetown-zoning-bylaw.py` now preserves those four reviewed requirement promotions during regeneration
- `plan/chalottetown-draft-zoning-issue-ledger.csv` now has 158 open rows: 158 `review_flag` rows and 0 `needs_review` rows
- Phase 3 is complete for all current `confidence: "needs_review"` entries
- Phase 4 triage found 94 `numeric_value_review` rows, 29 `extraction_review` rows, 24 `table_parsing_review` rows, 4 `schedule_map_review` rows, 4 `section_assignment_review` rows, and 3 `layout_order_review` rows
- the 94 numeric rows are mostly table-cell preservation flags, with 60 in `general-provisions-buildings-structures.json`; handle them as table-normalization review after section and layout regression checks
- the broad extraction and table-parsing rows are mostly one or two file-level legacy warnings per affected file; close them only after source-page regression checks show section order, table placement, and figure bleed are correct for the file
- schedule-map review rows in Schedules A through D should remain open until spatial QA inputs exist, unless Phase 5 explicitly documents them as intentional residual limitations
- first Phase 4 repair allowlist: `zones/rn.json`, `zones/rm.json`, and `zones/rh.json` for layout-order regression, plus `design-standards-500-lot-area.json`, `general-provisions-buildings-structures.json`, `general-provisions-lots-site-design.json`, and `general-provisions-signage.json` for explicit section-assignment review
- the RN/RM/RH Phase 4 layout regression review found no RM regression, but confirmed RN `10.4.7(g)` figure bleed, RN `10.6.2` Figure 10.2 label bleed, and RH `12.3`/`12.4` layout corruption
- `scripts/extract-charlottetown-zoning-bylaw.py` and `scripts/regenerate-charlottetown-draft-zoning-bylaw.py` now apply a targeted RN/RH Phase 4 layout repair during draft regeneration
- regenerated `zones/rn.json` now keeps `10.4.7(g)` as `max. 40%` and removes Figure 10.2 labels from `10.6.2`
- regenerated `zones/rh.json` now restores complete `12.3.2` and `12.3.3` table rows, removes duplicate `12.3.1` clause records, and restores the full `12.4` flaglot clause
- the four explicit section-assignment files now have zero raw `content_blocks` and zero `section_assignment_review` flags after assigning Part 3 `3.1.2(d)` through `(g)` to section `3.1`, assigning the Part 9 purpose text to `9.1`, returning the displaced Part 9 liability tail to `9.2.5`, and dropping only Part 5/6 running header/footer artifacts
- the Buildings and Structures numeric-cell pass updated the generator so current draft Tables 3.1 and 3.2 are recognized as general-provisions requirement tables, descriptor cells are not treated as numeric review defects, and valid `YES`, `Unlimited`, and `N/A` values do not produce numeric review flags
- regenerated `general-provisions-buildings-structures.json` now has zero `numeric_value_review` rows, with only its broad `extraction_review` and `table_parsing_review` rows remaining open
- the lower-density numeric-cell pass updated table-cell parsing for `m2`, percent cells, `N/A`, zone-designation descriptor cells, and parenthetical bedroom counts such as `four (4) bedrooms`
- the schema and extractor now support `building` as a numeric count unit, so `zones/rh.json` table `12.3.3`, row 3, value `max. 4 buildings per cluster per lot` is normalized as `value: 4`, `unit: "building"`, and `measure_type: "count"`
- the broad extraction and table-parsing pass closed the remaining file-level legacy warnings after reviewed source-page regression coverage found no additional concrete wrong-section, wrong-order, figure-bleed, or table-placement defects beyond the already repaired Phase 4 items
- the final RN/RM/RH layout-order acceptance pass closed the conservative residual layout warnings after regeneration preserved the repaired RN, RM, and RH section/table structure
- regenerated Phase 4 ledger counts are 0 `numeric_value_review` rows, 0 `extraction_review` rows, 0 `table_parsing_review` rows, 4 `schedule_map_review` rows, 0 `section_assignment_review` rows, and 0 `layout_order_review` rows

Next actions:

1. Continue retaining schedule-map review rows until spatial QA inputs exist or Phase 5 documents them as intentional residual limitations.

## Progress Rules

- Update `Status Summary` whenever the active phase or overall status changes.
- Update `Current Phase Detail` whenever work starts, pauses, or completes within the active phase.
- Mark a phase `Complete` only when its exit criteria are met.
- Keep future phases `Pending` until they become active.
- If work is blocked, set `Overall status` to `Blocked` and record the blocker under the active phase.

## Completion Condition

This timeline remains active until Phase 6 is complete and the acceptance criteria in `plan/chalottetown-draft-zoning-plan.md` are satisfied.
