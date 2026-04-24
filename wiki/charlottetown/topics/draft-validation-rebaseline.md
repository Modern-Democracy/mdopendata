# Draft Validation Rebaseline

## Scope

This page records the 2026-04-24 rebaseline of the Charlottetown draft zoning validation plan after parser repairs restored or added clauses and sections.

## 2026-04-24 Findings

- Source plan: `plan/chalottetown-draft-zoning-plan.md`.
- Timeline: `plan/chalottetown-draft-zoning-timeline.md`.
- Generated outputs: `data/zoning/charlottetown-draft/**/*.json`.
- Code-table report: `data/zoning/charlottetown-draft/code-table-match-report.json`.
- The original 2026-04-23 issue ledger remains the initial baseline, but it is no longer a complete current inventory after regenerated outputs restored or added clauses and sections.
- Current generated-output marker counts on 2026-04-24 are 246 `review_flags` across 33 JSON files and 174 `confidence: "needs_review"` entries across 27 JSON files.
- The current code-table report listed 25 `use.new_codes` before the reconciliation pass.
- The reconciliation classified `Cluster Housing` and `Seniors Housing` as true draft-origin use codes, mapped compound or renamed phrases to existing use codes, and removed dimensional/header/pseudo-use artifacts from queryable use terms.
- After regeneration, `data/zoning/charlottetown-draft/code-table-match-report.json` reports 0 `use.new_codes`, 11 `use.semantic_matches`, and 97 `use.exact_matches`.
- `zones/rh.json`, `general-provisions-parking.json`, `zones/bp.json`, `zones/dw.json`, `zones/dms.json`, `zones/ap.json`, `zones/rm.json`, and `zones/rn.json` currently have the highest `needs_review` concentrations.

## Plan Impact

- Phase 1 is complete only for the 2026-04-23 baseline ledger until the ledger is refreshed from the current generated outputs.
- Phase 2 code-table drift has been rechecked for `use.new_codes`; the report now has no unresolved new use codes.
- Phase 3 remains active, but further completion claims depend on the refreshed ledger and code-table drift review.
- Phase 4 should begin with regression review of already repaired layout sections before widening to remaining layout issues.
