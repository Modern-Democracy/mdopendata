# Draft Layout Repair Notes

## Scope

This page records durable extraction notes for reported Charlottetown draft zoning bylaw layout defects that affect section titles and clause assignment.

## 2026-04-24 Part 1 and Part 2 Repairs

- Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, bylaw pages 3, 4, 5, 9, 11, and 15.
- Extractor: `scripts/extract-charlottetown-draft-zoning-bylaw.py`.
- Outputs: `data/zoning/charlottetown-draft/administration.json` and `data/zoning/charlottetown-draft/permit-applications-processes.json`.
- The source uses multi-line uppercase headings for `1.6 OTHER BYLAWS, PERMITS, AND LICENSES`, `1.14 CALCULATION OF NUMERICAL REQUIREMENTS`, `2.1 FEES FOR PERMITS AND RELATED SERVICES`, `2.9 SITE SPECIFIC ZONING AMENDMENTS`, and `2.11 ELIGIBLE PUBLIC BENEFITS FOR BONUS HEIGHT`; the extractor now merges those title lines before section parsing.
- The source page layout places some right-column text above lower left-column section headings on draft PDF pages 7, 15, and 19; the extractor now applies targeted left-column-before-right-column ordering for those pages.
- Regenerated outputs place `1.6` clauses under `1.6`, keep `REQUIREMENTS`, `SERVICES`, `AMENDMENTS`, and `BONUS HEIGHT` inside section titles rather than clause text, keep `2.11.1(c)(iii)` through `2.11.1(f)(i)` under `2.11`, and keep `2.18.2(a)` through `2.18.4` under `2.18`.

## 2026-04-24 Part 8 Parking Repairs

- Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, bylaw pages 62, 65, 66, 69, and 70.
- Extractors: `scripts/extract-charlottetown-zoning-bylaw.py` and `scripts/regenerate-charlottetown-draft-zoning-bylaw.py`.
- Output: `data/zoning/charlottetown-draft/general-provisions-parking.json`.
- The source places `8.4.4` and `8.4.5` under `8.4 PARKING SPACE DESIGN STANDARDS`; regenerated output now moves those clauses out of `8.3 CASH-IN-LIEU`.
- The source clause `8.5.2(f)` ends with the residential-zone/commercial-zone buffer condition; regenerated output now preserves that tail.
- Figure and table bleed from parking island and accessible-parking graphics was removed from `8.7.1(c)`, `8.8.2`, and `8.8.6`.
- The source has distinct sections `8.12 BICYCLE PARKING`, `8.13 BICYCLE PARKING (CLASS A)`, and `8.14 BICYCLE PARKING (CLASS B)`; regenerated output now creates those sections explicitly instead of preserving title and figure text inside clause bodies.

## 2026-04-28 RN/RH Phase 4 Layout Repairs

- Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, bylaw pages 92, 94, 98, and 99.
- Extractors: `scripts/extract-charlottetown-zoning-bylaw.py` and `scripts/regenerate-charlottetown-draft-zoning-bylaw.py`.
- Outputs: `data/zoning/charlottetown-draft/zones/rn.json` and `data/zoning/charlottetown-draft/zones/rh.json`.
- The RN source table for `10.4.7(g)` gives coverage as `max. 40%`; regenerated output now removes Figure 10.1 side-yard and frontage label bleed from that table cell.
- The RN source clause `10.6.2` ends after the loose gravel or soil prohibition; regenerated output now removes Figure 10.2 labels from the clause text.
- The RH source places the complete `12.3.2` and `12.3.3` dimensional requirement rows before `12.4 PERMITTED WITH CONDITIONS`; regenerated output now stores those requirements as complete `tables_raw`, removes duplicate `12.3.1` clause records, and restores the full `12.4` flaglot clause.

## 2026-04-28 Phase 4 Section-Assignment Repairs

- Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, bylaw pages 17, 37, 43, and 71.
- Extractor: `scripts/extract-charlottetown-draft-zoning-bylaw.py`.
- Outputs: `data/zoning/charlottetown-draft/general-provisions-buildings-structures.json`, `data/zoning/charlottetown-draft/general-provisions-lots-site-design.json`, `data/zoning/charlottetown-draft/design-standards-500-lot-area.json`, and `data/zoning/charlottetown-draft/general-provisions-signage.json`.
- The source places Part 3 `3.1.2(d)` through `(g)` in the right column before the `3.1` heading in pypdf text order; regenerated output now assigns those clauses under section `3.1`.
- The Part 5 and Part 6 unassigned text consisted only of running header/footer artifacts; regenerated output now drops those artifacts instead of preserving them as section-assignment content.
- The Part 9 source places the `9.1 PURPOSE` heading between the purpose paragraph and the tail of `9.2.5`; regenerated output now assigns the purpose paragraph under `9.1` and returns the liability tail to `9.2.5`.
- The four explicit section-assignment files now have zero raw `content_blocks` and zero `section_assignment_review` flags.

## 2026-04-29 Part 9 Signage Table Repairs

- Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, bylaw pages 77 and 78.
- Extractor: `scripts/extract-charlottetown-zoning-bylaw.py` through `scripts/regenerate-charlottetown-draft-zoning-bylaw.py`.
- Output: `data/zoning/charlottetown-draft/general-provisions-signage.json`.
- Section `9.10` now keeps only the development-agreement clause under `doc-general-provisions-clause-9-10-1`; the duplicate `9.10.1` row containing awning/canopy text was removed.
- Section `9.11` now restores clause `9.11.1` as the awning/canopy table intro and stores Table 9.1 as two rows with columns `Zone`, `Dimensions`, and `General Provisions`; the shared third-column text is duplicated into both rows.
- Section `9.12` now restores clause `9.12.1` as the projecting-sign table intro and stores Table 9.2 as three rows with columns `Zone`, `Dimensions`, and `General Provisions`; the shared third-column text is duplicated into all three rows.

## 2026-04-29 General Wrapped Section-Title Repair

- Source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf`, two-column section-heading layout across the draft bylaw.
- Extractors: `scripts/extract-charlottetown-draft-zoning-bylaw.py`, `scripts/extract-charlottetown-zoning-bylaw.py`, and `scripts/regenerate-charlottetown-draft-zoning-bylaw.py`.
- Output family: `data/zoning/charlottetown-draft`.
- The draft extractor now applies wrapped uppercase section-title merging on all pages instead of a fixed page allowlist.
- The Part 9 signage repair no longer injects a synthetic `section` clause for `9.10 DEVELOPMENT AGREEMENTS`; regenerated section `9.10` keeps `SIGN PROVISIONS FOR DEVELOPMENT AGREEMENTS` as the section title and `9.10.1` as the first clause.
- Targeted controls after regeneration confirmed `1.6`, `1.14`, `2.1`, `2.9`, `2.11`, `8.13`, `8.14`, `9.3`, and `9.10` retain merged titles and have no uppercase title fragments stored as `clause_label_raw: "section"` clauses.

## Open Limits

- This note covers only the named Part 1, Part 2, Part 3, Part 5, Part 6, Part 8, Part 9, RN, RH, and general wrapped-section-title extraction defects verified on 2026-04-24, 2026-04-28, and 2026-04-29.
