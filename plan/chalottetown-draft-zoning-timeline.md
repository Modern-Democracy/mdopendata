# Charlottetown Draft Zoning Validation Timeline

Reference plan: `plan/chalottetown-draft-zoning-plan.md`

## Status Summary

- Active phase: Phase 2
- Active phase name: Code-Table Normalization
- Overall status: In progress
- Current progress: Phase 1 is complete. The issue ledger now exists at `plan/chalottetown-draft-zoning-issue-ledger.csv` with 285 open items cataloged: 139 `review_flags`, 130 structured `confidence: "needs_review"` records, and 16 unmatched code-table phrases. Phase 2 phrase review is complete, including grouped normalization proposals for split-code phrases and condition-bearing phrases. Phase 2 application work remains active.
- Last updated: 2026-04-23

## Phase Timeline

| Phase | Name | Scope | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| 0 | Plan Baseline | Establish validation plan, scope, priorities, and acceptance criteria. | Complete | `plan/chalottetown-draft-zoning-plan.md` approved as working reference. |
| 1 | Inventory and Triage | Build the master issue ledger from all open `review_flags`, all `confidence: "needs_review"` records, and all unmatched code-table phrases. Classify each item by issue class, source location, and proposed disposition. | Complete | Complete issue ledger exists and every open item is cataloged with file, object id, source citation, issue class, and status. |
| 2 | Code-Table Normalization | Resolve repeated unmatched term and use phrases, confirm semantic matches, and decide reuse versus new reviewed codes versus extraction-artifact removal. | Active | All draft code-table decisions are consistent across files and `code-table-match-report.json` reflects reviewed outcomes. |
| 3 | High-Priority Clause Validation | Validate and normalize the highest-density `needs_review` files and resolve clause text, numeric, and record-type defects. Initial file group: `zones/rn.json`, `zones/rm.json`, `zones/rh.json`, `zones/dms.json`, `general-provisions-parking.json`, `general-provisions-land-use.json`. | Pending | High-priority files no longer contain unresolved `needs_review` entries except documented true residual limits. |
| 4 | Section and Layout Repair | Resolve extraction-order, section-assignment, zone-boundary, and table or figure bleed defects by checking the visual PDF against normalized outputs. | Pending | Targeted files have corrected section assignment and only justified residual extraction reviews remain. |
| 5 | Remaining Files and Schedule Review | Review lower-density files and confirm the schedule JSON files remain page-text artifacts with explicit downstream limits. | Pending | Remaining files are reviewed, residual schedule-map limitations are explicit, and low-density issues are closed or intentionally retained. |
| 6 | Regeneration and Final QA | Re-run regeneration and schema validation, recompute counts, verify resolved items, and write the final QA summary. | Pending | Acceptance criteria from `plan/chalottetown-draft-zoning-plan.md` are met. |

## Current Phase Detail

### Phase 2: Code-Table Normalization

Objective:

- resolve the repeated unmatched term and use phrases surfaced by the Phase 1 ledger

Required outputs:

- reviewed decisions for each unmatched code-table phrase variant
- consistent reuse versus new-code versus extraction-artifact decisions across files
- updated downstream tracking in `code-table-match-report.json` when phrase decisions are approved and applied

Inputs:

- `plan/chalottetown-draft-zoning-issue-ledger.csv`
- `data/zoning/charlottetown-draft/code-table-match-report.json`
- `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`

Current progress:

- issue ledger created at `plan/chalottetown-draft-zoning-issue-ledger.csv`
- ledger counts verified against the plan baseline: 139 `review_flags`, 130 `needs_review` records, 16 unmatched code-table phrases
- Phase 1 exit criteria satisfied
- Phase 2 opened with code-table normalization as the next active workstream
- grouped review completed for the 16 unmatched code-table phrases, including proposed splits for combined use labels and separation of condition text from base use codes

Next actions:

1. Apply the approved split decisions for combined labels such as `Hostel / Hotel`, `Parking Lot / Structure`, and `Warehouse, Storage Facility and/or Distribution Centre`.
2. Replace condition-bearing pseudo-codes with base use codes plus separate requirements or references, including the RN and UE residential phrases.
3. Confirm whether draft-only concepts such as `Cluster Housing` and `Seniors Housing` should become reviewed new codes or be normalized to existing dwelling codes after source review.
4. Update the affected draft files and `code-table-match-report.json` consistently once the grouped decisions are approved.

## Progress Rules

- Update `Status Summary` whenever the active phase or overall status changes.
- Update `Current Phase Detail` whenever work starts, pauses, or completes within the active phase.
- Mark a phase `Complete` only when its exit criteria are met.
- Keep future phases `Pending` until they become active.
- If work is blocked, set `Overall status` to `Blocked` and record the blocker under the active phase.

## Completion Condition

This timeline remains active until Phase 6 is complete and the acceptance criteria in `plan/chalottetown-draft-zoning-plan.md` are satisfied.
