# Charlottetown Draft Zoning Validation Timeline

Reference plan: `plan/chalottetown-draft-zoning-plan.md`

## Status Summary

- Active phase: Phase 3
- Active phase name: High-Priority Clause Validation
- Overall status: In progress
- Current progress: Phase 2 is complete. Approved code-table normalization decisions have been applied across the affected draft zone files and `data/zoning/charlottetown-draft/code-table-match-report.json`. The report now retains only `Cluster Housing` and `Seniors Housing` as remaining true new-code candidates from this pass. Phase 3 is now active.
- Last updated: 2026-04-23

## Phase Timeline

| Phase | Name | Scope | Status | Exit Criteria |
| --- | --- | --- | --- | --- |
| 0 | Plan Baseline | Establish validation plan, scope, priorities, and acceptance criteria. | Complete | `plan/chalottetown-draft-zoning-plan.md` approved as working reference. |
| 1 | Inventory and Triage | Build the master issue ledger from all open `review_flags`, all `confidence: "needs_review"` records, and all unmatched code-table phrases. Classify each item by issue class, source location, and proposed disposition. | Complete | Complete issue ledger exists and every open item is cataloged with file, object id, source citation, issue class, and status. |
| 2 | Code-Table Normalization | Resolve repeated unmatched term and use phrases, confirm semantic matches, and decide reuse versus new reviewed codes versus extraction-artifact removal. | Complete | All draft code-table decisions are consistent across files and `code-table-match-report.json` reflects reviewed outcomes. |
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
- `data/zoning/charlottetown-draft/code-table-match-report.json` now retains only `Cluster Housing` and `Seniors Housing` as remaining true new-code candidates from this review pass
- Phase 3 opened with the high-priority clause-validation batch as the next active workstream

Next actions:

1. Validate the remaining high-priority `needs_review` entries in `zones/rn.json`, `zones/rm.json`, `zones/rh.json`, and `zones/dms.json` against the PDF.
2. Resolve the highest-density clause and numeric defects in `general-provisions-parking.json` and `general-provisions-land-use.json`.
3. Recompute the ledger counts after the first clause-validation batch.
4. Update the timeline and ledger status fields as each batch closes.

## Progress Rules

- Update `Status Summary` whenever the active phase or overall status changes.
- Update `Current Phase Detail` whenever work starts, pauses, or completes within the active phase.
- Mark a phase `Complete` only when its exit criteria are met.
- Keep future phases `Pending` until they become active.
- If work is blocked, set `Overall status` to `Blocked` and record the blocker under the active phase.

## Completion Condition

This timeline remains active until Phase 6 is complete and the acceptance criteria in `plan/chalottetown-draft-zoning-plan.md` are satisfied.
