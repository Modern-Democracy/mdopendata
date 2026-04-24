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
- The current code-table report lists 25 `use.new_codes`; these require reclassification into true new use codes, semantic matches, or extraction artifacts before Phase 2 can be treated as clean for the current outputs.
- `zones/rh.json`, `general-provisions-parking.json`, `zones/bp.json`, `zones/dw.json`, `zones/dms.json`, `zones/ap.json`, `zones/rm.json`, and `zones/rn.json` currently have the highest `needs_review` concentrations.

## Plan Impact

- Phase 1 is complete only for the 2026-04-23 baseline ledger until the ledger is refreshed from the current generated outputs.
- Phase 2 is complete only for the approved code-table normalization pass until the current code-table drift is reviewed.
- Phase 3 remains active, but further completion claims depend on the refreshed ledger and code-table drift review.
- Phase 4 should begin with regression review of already repaired layout sections before widening to remaining layout issues.
