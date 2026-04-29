---
type: log
tags:
  - charlottetown
  - log
updated: 2026-04-29
---

Append new entries in reverse chronological order. Use headings in this format:

# Charlottetown Wiki Log

```text
## [YYYY-MM-DD] type | Short title
```

## [2026-04-29] data-engineering | Section-equivalence rerun

Reopened Phase 3 after QA found accepted section-equivalence mismatches and blank-side comparisons. Updated `scripts/generate-charlottetown-section-equivalence.py` to compare linked table-cell text as well as clause text, reset the prior 137 reviewed `title_topic_token_v1` rows, inserted 139 regenerated candidate rows, exported a fresh `section-equivalence-review.csv` with all rows marked `needs_review`, and verified 0 accepted rows and 0 blank-side candidate rows.

## [2026-04-29] validation | Draft pre-import QA gate

Completed the Phase 5 pre-import QA gate for the draft rebaseline timeline. Schema validation, marker scans, code-table report checks, draft importer dry-run, section-equivalence database parity, and schedule-map limit checks passed; the rebaseline timeline is complete and the unified ingestion timeline advances to spatial registration and linkage.

## [2026-04-29] data-engineering | Section-equivalence ledger applied

Applied all 137 `section-equivalence-review.csv` decisions to `zoning.section_equivalence`. Database verification found 88 accepted rows, 49 rejected `not_equivalent` rows, 0 `candidate` rows, 0 `needs_review` rows, and 0 ledger/database mismatches.

## [2026-04-29] data-quality | Section-equivalence needs-review closure

Closed the 18 remaining `needs_review` rows in `data/zoning/charlottetown-draft/review/section-equivalence-review.csv` after source comparison. All 18 were rejected, leaving the ledger with 88 accepted, 49 rejected, and 0 `needs_review` decisions before database application.

## [2026-04-29] data-quality | Draft numeric table review closure

Updated the draft extractor and regenerated draft outputs after closing the 41 post-fix `numeric_value_review` flags. Table 3.1 accessory-building word counts now normalize to building counts, accessible parking and bike-space lead values normalize to parking-space counts, and descriptor/prose table cells no longer create false numeric review flags.

## [2026-04-29] planning | Draft validation rebaseline timeline

Created `plan/charlottetown-draft-zoning-validation-rebaseline-timeline.md` for the post-fix draft validation pass and updated `topics/workstream-context.md` to treat it as the active validation timeline while retaining the prior completed timeline as historical context.

## [2026-04-29] extraction | Draft table reference repair

Updated `topics/draft-layout-repair-notes.md` after restoring missing regenerated `tables_raw` entries for Table 3.1, Table 8.4, Table 8.5, and Tables 9.3 through 9.8 in the Charlottetown draft outputs.

## [2026-04-29] data-quality | Partial-overlap decisions appended to ledger

Appended manual ledger decisions for all 35 `partial_overlap` section-equivalence candidates to `data/zoning/charlottetown-draft/review/section-equivalence-review.csv` before database updates: 2 accepted, 24 rejected, and 9 marked `needs_review`.

## [2026-04-29] data-quality | Renamed-or-restructured decisions appended to ledger

Appended manual ledger decisions for all 26 `renamed_or_restructured` section-equivalence candidates to `data/zoning/charlottetown-draft/review/section-equivalence-review.csv` before database updates: 10 accepted, 7 rejected, and 9 marked `needs_review`.

## [2026-04-29] data-quality | Remaining same-topic decisions appended to ledger

Appended accepted ledger decisions for the remaining 41 `same_topic` section-equivalence candidates to `data/zoning/charlottetown-draft/review/section-equivalence-review.csv` before database updates. The database still has those 41 rows as `candidate` until a later apply step.

## [2026-04-29] data-quality | Section-equivalence review ledger created

Created `data/zoning/charlottetown-draft/review/section-equivalence-review.csv` and backfilled the 35 accepted exact-title `same_topic` section-equivalence decisions from `zoning.section_equivalence`.

## [2026-04-29] data-quality | Section-equivalence manual review started

Started manual review of the 137 `zoning.section_equivalence` candidates. Accepted 35 exact-title `same_topic` matches with text similarity at or above 0.75, leaving 102 candidate rows for continued review.

## [2026-04-29] implementation | Section-equivalence candidate tuning

Tuned `scripts/generate-charlottetown-section-equivalence.py` against exact-title controls and sampled weak false positives. Repopulated `zoning.section_equivalence` with 137 `title_topic_token_v1` candidate rows: 76 `same_topic`, 26 `renamed_or_restructured`, and 35 `partial_overlap`.

## [2026-04-29] implementation | Section-equivalence candidate generation started

Implemented `scripts/generate-charlottetown-section-equivalence.py` and populated 300 `title_topic_token_v1` candidate rows in `zoning.section_equivalence`. Updated `topics/unified-zoning-ingestion-plan.md`, `topics/workstream-context.md`, `index.md`, and `plan/charlottetown-unified-zoning-ingestion-timeline.md` to reflect Phase 3 progress.

## [2026-04-29] planning | Unified zoning ingestion status and timeline

Updated `topics/unified-zoning-ingestion-plan.md`, `topics/workstream-context.md`, and `index.md` to reflect that the `zoning` schema migration and initial Charlottetown importer are implemented and populated in the database. Added `plan/charlottetown-unified-zoning-ingestion-timeline.md` to track phases for schema/importer completion, section equivalence, spatial linkage, vector support, and deferred current coverage.

## [2026-04-28] planning | Unified zoning ingestion contracts

Updated `topics/unified-zoning-ingestion-plan.md` with missing implementation contracts for source JSON field mapping, v1 import scope, stable identity and hashing, manual correction replay, coverage-gap semantics, section-topic ownership, spatial layer contracts, and readiness checks.

## [2026-04-28] planning | Unified zoning ingestion plan

Added `topics/unified-zoning-ingestion-plan.md` and updated the Charlottetown index and workstream context for the next phase of relational, spatial, comparison, revision-aware, and text-vector-ready ingestion of the current and draft zoning bylaws.

## [2026-04-28] validation | Phase 6 final QA

Completed Phase 6 final QA for the Charlottetown draft zoning validation workstream. Regeneration and schema validation passed, the final scan found 0 `review_flags`, 0 `confidence: "needs_review"` entries, and 0 unresolved new code-table entries, and `plan/chalottetown-draft-zoning-final-qa-summary.md` now records the final QA evidence.

## [2026-04-28] validation | Phase 5 schedule-map residual closure

Updated `topics/draft-validation-rebaseline.md` after closing the remaining Schedules A through D `schedule_map_review` rows as documented page-text map artifact limits. The refreshed ledger now contains 0 open rows.

## [2026-04-28] validation | Phase 4 RN/RM/RH layout-order closure

Updated `topics/draft-validation-rebaseline.md` after closing the reviewed RN/RM/RH `layout_order_review` residual warnings. The refreshed ledger now retains only 4 schedule-map rows.

## [2026-04-28] validation | Phase 4 broad extraction and table parsing

Updated `topics/draft-validation-rebaseline.md` after closing the broad file-level `extraction_review` and `table_parsing_review` rows. The refreshed ledger now retains only 4 schedule-map rows and 3 RN/RM/RH layout-order rows.

## [2026-04-28] extraction | Draft RN/RH Phase 4 layout repairs

Updated `topics/draft-layout-repair-notes.md` after repairing RN figure bleed in `10.4.7(g)` and `10.6.2`, and RH `12.3`/`12.4` table and clause assignment in regenerated draft zone outputs.

## [2026-04-28] extraction | Draft Phase 4 section-assignment repairs

Updated `topics/draft-layout-repair-notes.md` and `topics/draft-validation-rebaseline.md` after repairing the four explicit section-assignment files. Regenerated outputs now have zero raw `content_blocks` and zero `section_assignment_review` flags in those files.

## [2026-04-28] validation | Phase 4 review-flag triage

Updated `topics/draft-validation-rebaseline.md` after triaging the 158 remaining draft `review_flag` rows into numeric, extraction, table, section-assignment, schedule-map, and layout-order batches.

## [2026-04-28] extraction | Draft HI, subdivision, permit, DN, P, and RM Phase 3 review

Updated `topics/draft-validation-rebaseline.md` after resolving the Phase 3 `needs_review` entries in `zones/hi.json`, `general-provisions-subdividing-land.json`, `permit-applications-processes.json`, `zones/dn.json`, `zones/p.json`, and `zones/rm.json`.

## [2026-04-28] extraction | Draft buildings, BP, DC, I, and RN Phase 3 review

Updated `topics/draft-validation-rebaseline.md` after resolving the Phase 3 `needs_review` entries in `general-provisions-buildings-structures.json`, `zones/bp.json`, `zones/dc.json`, `zones/i.json`, and `zones/rn.json`.

## [2026-04-28] maintenance | Workstream context relocation

Moved durable Charlottetown workstream context from root startup instructions into `README.md` and `topics/workstream-context.md`; updated the index so role skills can look up the context only when relevant.

## [2026-04-28] extraction | Final Phase 3 needs-review closure

Updated `topics/draft-validation-rebaseline.md` after resolving the final Phase 3 `needs_review` entries in `general-provisions-lots-site-design.json`, `zones/c.json`, `zones/gn.json`, and `zones/rh.json`.

## [2026-04-28] extraction | Draft 500 Lot Area, DMS, and DMU Phase 3 review

Updated `topics/draft-validation-rebaseline.md` after resolving the Phase 3 `needs_review` entries in `design-standards-500-lot-area.json`, `zones/dms.json`, and `zones/dmu.json`.

## [2026-04-24] extraction | Draft DW and signage Phase 3 review

Updated `topics/draft-validation-rebaseline.md` after resolving the Phase 3 `needs_review` entries in `zones/dw.json` and `general-provisions-signage.json`.

## [2026-04-29] extraction | Draft signage table repair

Updated `topics/draft-layout-repair-notes.md` after repairing Part 9 signage sections `9.10`, `9.11`, and `9.12` so Table 9.1 and Table 9.2 are table rows instead of clause spillover in `general-provisions-signage.json`.

## [2026-04-29] extraction | General wrapped section-title repair

Updated `topics/draft-layout-repair-notes.md` after replacing the draft extractor page-specific wrapped-title allowlist with general uppercase continuation merging and removing the synthetic Part 9 `9.10` title-fragment `section` clause.

## [2026-04-29] extraction | Inline numbered subclause repair

Updated `topics/draft-layout-repair-notes.md` after generalizing draft regeneration to split inline `1)`, `2)`, and `3)` subclauses under `9.3.1(l)(i)` and `9.3.1(l)(ii)` into raw child clauses.

## [2026-04-29] extraction | Part source-unit text repair

Updated `topics/draft-layout-repair-notes.md` after removing duplicated clause text from Part-level `raw_data.source_units` in regenerated draft outputs while retaining page text for Schedule source units.

## [2026-04-24] extraction | Draft parking and land-use Phase 3 repairs

Updated `topics/draft-layout-repair-notes.md` and `topics/draft-validation-rebaseline.md` after resolving the Phase 3 `needs_review` entries in `general-provisions-parking.json` and `general-provisions-land-use.json`.

## [2026-04-24] validation | Draft issue ledger refresh

Updated `topics/draft-validation-rebaseline.md` after refreshing `plan/chalottetown-draft-zoning-issue-ledger.csv` from the current regenerated draft outputs.

## [2026-04-28] schema | Building-count numeric unit

Updated `topics/draft-validation-rebaseline.md` after adding `building` as a normalized numeric count unit and closing the final `numeric_value_review` row.

## [2026-04-28] validation | Phase 4 numeric table-cell pass

Updated `topics/draft-validation-rebaseline.md` after the lower-density numeric table-cell pass reduced draft `numeric_value_review` rows from 38 to 1, with the remaining RH cluster-building count retained as a schema-limited residual.

## [2026-04-24] validation | Draft use-code reconciliation

Updated `topics/draft-validation-rebaseline.md` after reconciling the 25 draft `use.new_codes` candidates into true new use codes, semantic matches, and extraction artifacts.

## [2026-04-24] planning | Draft validation rebaseline

Added `topics/draft-validation-rebaseline.md` for the 2026-04-24 validation-plan rebaseline after parser repairs restored or added draft bylaw clauses and sections.

## [2026-04-24] extraction | Draft Part 1 and Part 2 layout repairs

Added `topics/draft-layout-repair-notes.md` for the verified Charlottetown draft bylaw section-title and two-column ordering repairs affecting `1.6`, `1.14`, `2.1`, `2.9`, `2.11`, and `2.18`.

## [2026-04-24] setup | Charlottetown wiki scaffold

Created the v1 scaffold for the Charlottetown LLM Wiki, including the local guide, index, log, page areas, and templates. No substantive bylaw synthesis was added.

## Sources

- [Charlottetown wiki guide](./README.md)
- [Unified zoning ingestion plan](./topics/unified-zoning-ingestion-plan.md)
