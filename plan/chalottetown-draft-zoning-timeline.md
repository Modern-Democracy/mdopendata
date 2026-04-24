# Charlottetown Draft Zoning Validation Timeline

Reference plan: `plan/chalottetown-draft-zoning-plan.md`

## Status Summary

- Active phase: Phase 3 with Phase 1 refresh gate
- Active phase name: High-Priority Clause Validation and Inventory Rebaseline
- Overall status: In progress
- Current progress: Phase 2 is complete for the approved 2026-04-23 code-table normalization pass and the 2026-04-24 `use.new_codes` drift check. The completed Phase 1 inventory remains stale after clause and section restoration. Current generated-output marker counts before the use-code reconciliation were 246 `review_flags` across 33 JSON files and 174 `needs_review` entries across 27 JSON files. The code-table match report previously listed 25 `use.new_codes`; the reconciliation classified `Cluster Housing` and `Seniors Housing` as true draft-origin use codes, mapped renamed or compound phrases to existing codes, removed dimensional/header/pseudo-use artifacts from queryable terms, and regenerated the report with 0 `use.new_codes`, 11 `use.semantic_matches`, and 97 `use.exact_matches`. Phase 3 remains active for the pending high-priority general-provisions files, but further closure still depends on refreshing the issue ledger. Targeted layout-repair passes have already been applied in the draft extractor for RM-style figure/table bleed and the named Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, and Part 7 general-provisions parsing defects. Regenerated draft outputs now restore the missing RM `11.3.2`, `11.3.3`, `11.5`, and `11.6` clause structure, promote equivalent dimensional requirement blocks into `tables_raw`, repair draft Tables 3.1, 3.2, 3.3, 4.1, and 4.2 placement, split or reassign the reported clauses in sections `1.6`, `2.11`, `2.18`, `2.19`, `3.1`, `3.16`, `3.19`, `4.5`, `4.6`, `4.7`, `5.2`, `7.10`, and `7.11`, restore wrapped title continuations in sections `1.6`, `1.14`, `2.1`, `2.9`, `2.11`, `4.14`, `4.16`, `4.17`, `5.4`, `5.6`, `5.8`, `6.3`, `7.3`, `7.4`, `7.8`, `7.12`, and `7.13`, reorder or reparent the reported `7.3` and `7.5` clauses, and correct the Part 2/Part 3 extraction boundary so section `2.19` is generated in `permit-applications-processes.json` rather than `general-provisions-buildings-structures.json`.
- Last updated: 2026-04-24

## Phase Timeline

| Phase | Name | Scope | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| 0 | Plan Baseline | Establish validation plan, scope, priorities, and acceptance criteria. | Complete | `plan/chalottetown-draft-zoning-plan.md` approved as working reference. |
| 1 | Inventory and Triage | Build the master issue ledger from all open `review_flags`, all `confidence: "needs_review"` records, and all unmatched code-table phrases. Classify each item by issue class, source location, and proposed disposition. | Complete for 2026-04-23 baseline; refresh required | Complete issue ledger exists and every current open item is cataloged with file, object id, source citation, issue class, and status. |
| 2 | Code-Table Normalization | Resolve repeated unmatched term and use phrases, confirm semantic matches, and decide reuse versus new reviewed codes versus extraction-artifact removal. | Complete | All current draft code-table decisions are consistent across files and `code-table-match-report.json` reflects reviewed outcomes. |
| 3 | High-Priority Clause Validation | Validate and normalize the highest-density `needs_review` files and resolve clause text, numeric, and record-type defects. Initial file group: `zones/rn.json`, `zones/rm.json`, `zones/rh.json`, `zones/dms.json`, `general-provisions-parking.json`, `general-provisions-land-use.json`. | Active | High-priority files no longer contain unresolved `needs_review` entries except documented true residual limits. |
| 4 | Section and Layout Repair | Resolve extraction-order, section-assignment, zone-boundary, and table or figure bleed defects by checking the visual PDF against normalized outputs. | Pending | Targeted files have corrected section assignment and only justified residual extraction reviews remain. |
| 5 | Remaining Files and Schedule Review | Review lower-density files and confirm the schedule JSON files remain page-text artifacts with explicit downstream limits. | Pending | Remaining files are reviewed, residual schedule-map limitations are explicit, and low-density issues are closed or intentionally retained. |
| 6 | Regeneration and Final QA | Re-run regeneration and schema validation, recompute counts, verify resolved items, and write the final QA summary. | Pending | Acceptance criteria from `plan/chalottetown-draft-zoning-plan.md` are met. |

## Current Phase Detail

### Phase 3: High-Priority Clause Validation

Objective:

- validate and normalize the highest-density remaining `needs_review` records after the Phase 2 code-table cleanup

Required outputs:

- corrected high-priority clause, numeric, and record-type entries in the first validation batch
- reduced `needs_review` counts in the batch files with explicit residual issues only where source ambiguity remains
- updated draft JSON outputs and timeline tracking for the batch

Inputs:

- `plan/chalottetown-draft-zoning-issue-ledger.csv`
- `data/zoning/charlottetown-draft/zones/rn.json`
- `data/zoning/charlottetown-draft/zones/rm.json`
- `data/zoning/charlottetown-draft/zones/rh.json`
- `data/zoning/charlottetown-draft/zones/dms.json`
- `data/zoning/charlottetown-draft/general-provisions-parking.json`
- `data/zoning/charlottetown-draft/general-provisions-land-use.json`
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

Next actions:

1. Refresh `plan/chalottetown-draft-zoning-issue-ledger.csv` from the current generated JSON outputs and current `code-table-match-report.json`.
2. Resolve the highest-density clause and numeric defects in `general-provisions-parking.json` and `general-provisions-land-use.json`.
3. Review the remaining open non-clause rows in the four zone files only if they still affect Phase 3 acceptance.
4. Expand the layout-repair regression review to other draft zones that share the same figure and dimensional-table page pattern.

## Progress Rules

- Update `Status Summary` whenever the active phase or overall status changes.
- Update `Current Phase Detail` whenever work starts, pauses, or completes within the active phase.
- Mark a phase `Complete` only when its exit criteria are met.
- Keep future phases `Pending` until they become active.
- If work is blocked, set `Overall status` to `Blocked` and record the blocker under the active phase.

## Completion Condition

This timeline remains active until Phase 6 is complete and the acceptance criteria in `plan/chalottetown-draft-zoning-plan.md` are satisfied.
