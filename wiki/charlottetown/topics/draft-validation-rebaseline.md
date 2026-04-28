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
- After the Phase 3 500 Lot Area, DMS, and DMU pass, `plan/chalottetown-draft-zoning-issue-ledger.csv` has 195 open rows: 158 `review_flag` rows and 37 `needs_review` rows. `design-standards-500-lot-area.json`, `zones/dms.json`, and `zones/dmu.json` also have no remaining `confidence: "needs_review"` entries. `zones/dmu.json` clause `15.6.1` was corrected to `See Section 6.8-6.9` after source comparison showed the generated `1.5 m` value came from nearby figure or dimensional text bleed.
- After the Phase 3 buildings/structures, BP, DC, I, and RN pass, `plan/chalottetown-draft-zoning-issue-ledger.csv` has 175 open rows: 158 `review_flag` rows and 17 `needs_review` rows. `general-provisions-buildings-structures.json`, `zones/bp.json`, `zones/dc.json`, `zones/i.json`, and `zones/rn.json` also have no remaining `confidence: "needs_review"` entries. Source comparison removed figure bleed from general-provisions clause `3.9.1(a)` and RN clause `10.6.2`, and restored the truncated BP clause `18.6.13`.
- After the Phase 3 HI, subdividing land, permit applications, DN, P, and RM pass, `plan/chalottetown-draft-zoning-issue-ledger.csv` has 162 open rows: 158 `review_flag` rows and 4 `needs_review` rows. `zones/hi.json`, `general-provisions-subdividing-land.json`, `permit-applications-processes.json`, `zones/dn.json`, `zones/p.json`, and `zones/rm.json` also have no remaining `confidence: "needs_review"` entries. Reviewed-clause promotion is now applied during zone regeneration, so previously closed BP, DC, I, and RN requirement rows remain closed after regeneration.
- The refreshed ledger has no unmatched code-table `new_codes` rows.
- The remaining `needs_review` entries are one row each in `general-provisions-lots-site-design.json`, `zones/c.json`, `zones/gn.json`, and `zones/rh.json`.

## Plan Impact

- Phase 1 is refreshed for the current regenerated outputs.
- Phase 2 code-table drift has been rechecked for `use.new_codes`; the report now has no unresolved new use codes.
- Phase 3 remains active; the parking, land-use, DW, signage, 500 Lot Area, DMS, DMU, buildings/structures, BP, DC, I, RN, HI, subdividing land, permit applications, DN, P, and RM high-priority files are closed for `needs_review` records.
- Phase 4 should begin with regression review of already repaired layout sections before widening to remaining layout issues.
