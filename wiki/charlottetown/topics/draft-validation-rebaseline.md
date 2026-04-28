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
- After the final Phase 3 needs-review pass, `plan/chalottetown-draft-zoning-issue-ledger.csv` has 158 open rows: 158 `review_flag` rows and 0 `needs_review` rows. `general-provisions-lots-site-design.json`, `zones/c.json`, `zones/gn.json`, and `zones/rh.json` now have no remaining `confidence: "needs_review"` entries. Reviewed-clause promotion is applied during regeneration for the four final source refs: `doc-general-provisions-clause-5-5-1`, `zone-c-clause-27-4-2`, `zone-gn-clause-23-5-11`, and `zone-rh-clause-12-4-4-c`.
- The refreshed ledger has no unmatched code-table `new_codes` rows.
- No current regenerated draft output contains `confidence: "needs_review"`.
- Phase 4 triage classifies the 158 remaining `review_flag` rows as 94 `numeric_value_review`, 29 `extraction_review`, 24 `table_parsing_review`, 4 `section_assignment_review`, 4 `schedule_map_review`, and 3 `layout_order_review` rows.
- The first Phase 4 allowlist is `zones/rn.json`, `zones/rm.json`, and `zones/rh.json` for layout-order regression, plus `design-standards-500-lot-area.json`, `general-provisions-buildings-structures.json`, `general-provisions-lots-site-design.json`, and `general-provisions-signage.json` for explicit section-assignment review.
- The 94 numeric rows are table-cell normalization review rather than primary section-boundary repair; 60 are concentrated in `general-provisions-buildings-structures.json`.
- After the explicit section-assignment batch, the refreshed ledger still has 158 `review_flag` rows and 0 `needs_review` rows, but the distribution is 98 `numeric_value_review`, 29 `extraction_review`, 24 `table_parsing_review`, 0 `section_assignment_review`, 4 `schedule_map_review`, and 3 `layout_order_review` rows.
- The four explicit section-assignment files now have zero raw `content_blocks` and zero `section_assignment_review` flags. Part 3 `3.1.2(d)` through `(g)` are assigned under `3.1`, Part 9 purpose text is assigned under `9.1`, the displaced Part 9 liability tail is assigned under `9.2.5`, and Part 5/6 running header/footer artifacts are dropped.
- After adding building-count normalization, the refreshed ledger has 60 `review_flag` rows and 0 `needs_review` rows. The distribution is 0 `numeric_value_review`, 29 `extraction_review`, 24 `table_parsing_review`, 0 `section_assignment_review`, 4 `schedule_map_review`, and 3 `layout_order_review` rows.
- `zones/rh.json` table `12.3.3`, row 3, value `max. 4 buildings per cluster per lot` is normalized as `value: 4`, `unit: "building"`, and `measure_type: "count"`.
- After the Phase 4 broad extraction and table-parsing pass, the refreshed ledger has 7 `review_flag` rows and 0 `needs_review` rows. The distribution is 0 `numeric_value_review`, 0 `extraction_review`, 0 `table_parsing_review`, 0 `section_assignment_review`, 4 `schedule_map_review`, and 3 `layout_order_review` rows.
- The broad file-level legacy warnings were closed for reviewed supporting parts and zones after source-page regression coverage found no additional concrete wrong-section, wrong-order, figure-bleed, or table-placement defect beyond the already repaired Phase 4 items.
- Reviewed regeneration now also preserves `doc-general-provisions-clause-5-4-3-a` and `doc-general-provisions-clause-5-4-3-b` as high-confidence requirements so the Phase 3 closure remains stable.
- After the Phase 4 RN/RM/RH layout-order closure, the refreshed ledger has 4 `review_flag` rows and 0 `needs_review` rows. The distribution is 0 `numeric_value_review`, 0 `extraction_review`, 0 `table_parsing_review`, 0 `section_assignment_review`, 4 `schedule_map_review`, and 0 `layout_order_review` rows.
- After the Phase 5 schedule-map pass, the refreshed ledger has 0 `review_flag` rows and 0 `needs_review` rows. Schedules A through D are retained as page-text map artifacts with map-reference metadata only; they are not digitized zoning layers and require later spatial QA before parcel overlays, zoning-boundary comparison, or downstream GIS use.

## Plan Impact

- Phase 1 is refreshed for the current regenerated outputs.
- Phase 2 code-table drift has been rechecked for `use.new_codes`; the report now has no unresolved new use codes.
- Phase 3 is complete for all current `confidence: "needs_review"` records.
- Phase 4 has completed the RN/RM/RH layout regression and layout-order closure, the four explicit section-assignment files, all numeric table-cell flags, and broad extraction/table-parsing warnings.
- Phase 5 has completed the residual schedule-map review by documenting the schedule-map limitation in the generated README, source manifest, plan, and wiki while closing the open review-flag rows.
