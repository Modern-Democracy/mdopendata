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
- The current issue ledger was refreshed from regenerated outputs after the use-code reconciliation. It initially cataloged 244 open rows: 158 `review_flag` rows across 33 JSON files and 86 `needs_review` rows across 22 JSON files.
- After the Phase 3 parking and land-use pass, `plan/chalottetown-draft-zoning-issue-ledger.csv` catalogs 224 open rows: 158 `review_flag` rows and 66 `needs_review` rows. `general-provisions-parking.json` and `general-provisions-land-use.json` have no remaining `confidence: "needs_review"` entries.
- After the Phase 3 DW and signage pass, `plan/chalottetown-draft-zoning-issue-ledger.csv` catalogs 210 open rows: 158 `review_flag` rows and 52 `needs_review` rows. `zones/dw.json` and `general-provisions-signage.json` also have no remaining `confidence: "needs_review"` entries.
- The refreshed ledger has no unmatched code-table `new_codes` rows.
- `design-standards-500-lot-area.json`, `zones/dms.json`, and `zones/dmu.json` currently have the highest remaining `needs_review` concentrations.

## Plan Impact

- Phase 1 is refreshed for the current regenerated outputs.
- Phase 2 code-table drift has been rechecked for `use.new_codes`; the report now has no unresolved new use codes.
- Phase 3 remains active; the parking, land-use, DW, and signage high-priority files are closed for `needs_review` records, and the next highest-density files are `design-standards-500-lot-area.json`, `zones/dms.json`, and `zones/dmu.json`.
- Phase 4 should begin with regression review of already repaired layout sections before widening to remaining layout issues.
