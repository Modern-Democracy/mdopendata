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

## Open Limits

- This note covers only the named Part 1, Part 2, and Part 8 extraction defects verified on 2026-04-24.
