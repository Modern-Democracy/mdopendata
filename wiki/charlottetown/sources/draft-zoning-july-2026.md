---
type: source
tags:
  - charlottetown
  - zoning
  - draft
  - pdf-ingestion
  - gis
updated: 2026-08-05
---

This page records the July 30, 2026 Charlottetown draft zoning bylaw extraction, staged PDF review artifacts, and municipal-fit map extraction.

# Charlottetown Draft Zoning Bylaw, July 30, 2026

## Source and extracted artifacts

- Agenda-package source: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-09-05.pdf` (205 pages).
- Extracted bylaw PDF: `docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-07-30.pdf` (agenda pages 5-204, 200 pages).
- Normalized output: `data/zoning/charlottetown-draft-2026-07-30/`.
- Staged review workspace: `data/staged-pdf/charlottetown-draft-2026-07-30/v2/`.
- Local review URL: `http://127.0.0.1:3220/internal/pdf-inventory-review`.

## Normalized structure

The generated output has the same approved file layout as `data/zoning/charlottetown-draft/`: 36 JSON files, 20 zone files, 10 root supporting documents, 4 schedule files, README, and reports. The source manifest records the extracted July 30 PDF and draft date `July 30, 2026`.

The new output contains 9 review flags and 16 structured `confidence: "needs_review"` occurrences. Three use-code candidates are preserved rather than guessed:

- Extracted PDF page 139, bylaw page 135, P Zone clause 21.3.1(a): raw label `Marine Gas Station`; proposed slug `marine_gas_station`; output `zones/p.json`.
- Extracted PDF page 161, bylaw page 157, C Zone clause 27.3.1: raw label `Single-detached dwellings in accordance with the RN Zone requirements`; proposed slug is the generated long slug; output `zones/c.json`.
- Extracted PDF page 157, bylaw page 153, PPS Zone clause 25.3.1(j): raw label `Trail System ZONING & DEVELOPMENT BYL AW`; proposed slug is the generated long slug; output `zones/pps.json`. The spacing and OCR artifact are retained for review.

Additional retained review flags occur in `zones/eg.json` (`zone_boundary_review`, `permitted_use_extraction_review`) and `zones/ue.json` (`permitted_use_extraction_review`), with further structured review markers in general provisions and permit-process files.

## Normalization decision ledger

The 25 retained markers were checked against the rendered July PDF and recorded in `data/zoning/charlottetown-draft-2026-07-30/review/normalization-decision-ledger.csv`. All 25 rows are now approved for derived-output correction or closure. RN clause 10.5.8 starts on extracted PDF page 94, is interrupted by the Schedule 10.1 map on page 95, and continues with `facing facade.` at the top of page 96; its approved value is `At least 4 m2 of front porch (covered or uncovered) is required for every street facing facade.`

The July zoning design intentionally removes C as a separate zone and uses an environmental constraints overlay for the target properties. EG is also removed, with the better-defined UE Zone addressing that area. The PDF therefore contains no C or EG zone parts. The extracted C and EG files contain UE material under retired-zone placeholders, while the extracted UE file contains Part 28 Definitions pages. The ledger records no C or EG base-zone normalization. Any Part 27 use decision is assigned to UE only because the source page is UE; this is a file-assignment correction, not a semantic C-to-UE connection. The environmental constraints overlay remains a separate spatial replacement.

## Staged PDF review

Stage 0 contains 200 pages, 3 OCR fallback pages, and 0 blocked pages. Stage 1 contains 506 blocks, 43 financial/table candidates, and 3 review pages. The v2 source, block, and review artifacts pass `scripts/validate-staged-pdf-artifacts.py`; the local server reports canonical validation `valid`, 200 pages, and write-enabled review mode.

## Schedule map extraction

The updated Schedule A and Schedule C maps were extracted into `data/spatial/charlottetown/charlottetown-draft-map-layers-2026-07-30-municipal-fit.gpkg`, using `maps/pei/CHTWN_Municipal_Boundary.geojson` as the boundary reference and EPSG:2954 output. The summary is `data/spatial/charlottetown/charlottetown-draft-map-layers-2026-07-30-municipal-fit.summary.json`.

The output has valid geometries and a single municipal-boundary reference feature. Schedule A produced 18 zoning-area codes: `AP`, `BP`, `DC`, `DMS`, `DMU`, `DN`, `DW`, `GC`, `GN`, `HI`, `I`, `P`, `POS`, `PPS`, `RH`, `RM`, `RN`, and `UE`. Codes `C` and `EG` are not present in the updated Schedule A extracted area polygons and remain unresolved; no synthetic polygons were added. The municipal boundary is the same extent as the prior April map reference, while the new zone-area union is smaller and leaves a larger boundary gap, so parcel overlay use requires further spatial QA.

## Database comparison views

The manually managed public layers were inspected and compared in PostGIS. All four are valid `MULTIPOLYGON` layers in EPSG:2954. The original parcel layer has 13,833 features and the update has 14,327; the original zoning layer has 20 features and the update has 18. `parcel_candidate_id` is not stable across the two parcel extractions, so the comparison does not join parcels by that field.

The reproducible SQL is `schema/sql/033_charlottetown_draft_update_comparison.sql`. It creates:

- `zoning.v_charlottetown_parcel_coverage_changes`, using a 1 m grid dissolved-coverage comparison, plus `zoning.v_charlottetown_parcel_coverage_changes_significant` at the 1000 m² screening threshold.
- `zoning.v_charlottetown_draft_zoning_intersections`, retaining raw and canonical zone-code changes, plus `zoning.v_charlottetown_draft_zoning_intersections_significant` at the 1000 m² screening threshold.
- `zoning.v_charlottetown_draft_update_qa`, containing source validity, coverage, threshold, and zoning-transition metrics.

The parcel coverage difference is 48,448.025 m² after the 1 m grid comparison, but no individual coverage-change component reaches 1000 m²; the largest is 490 m². The zoning comparison has 63 canonical code-change intersections at or above 1000 m², covering 10,571,941.525 m². The original `H` to updated `HI` transition is classified separately as code normalization, not a substantive zone change. Large C/EG-related results require review because C and EG are absent from the updated extracted zoning polygons.

The updated-map-shape zoning comparison is implemented in `schema/sql/034_charlottetown_draft_zoning_shape_comparison.sql` through `zoning.v_charlottetown_draft_zoning_changed_shapes` and its 1000 m² screening view. Original `C` shapes are excluded before intersection. Output rows are grouped by updated feature and original zone code, so multiple original shapes with the same code dissolve into one output geometry while distinct original codes remain separate. The current result has 117 changed rows across 18 updated shapes; one `H` to `HI` row is classified as normalization-only and 116 rows are substantive raw-code changes.

## Published database and web defaults

The July normalized JSON is imported as draft `document_revision_id=13` with source manifest `data/zoning/charlottetown-draft-2026-07-30/source-manifest.json`. Review flags are retained in the imported records; the importer now supports an explicit `--allow-review` option for this reviewed-but-not-fully-cleared set, and removal marking is scoped to the imported revision rather than all draft records.

Migration `schema/sql/035_charlottetown_updated_layers_and_revision.sql` registers `public.CHTWN_Draft_Zoning_Boundaries_Update` as `zoning.charlottetown_draft_zoning_boundaries_update`, replaces the registered parcel source behind `zoning.v_charlottetown_parcel_map` with `public.CHTWN_Parcel_Map_Update`, and rebuilds `zoning.v_charlottetown_parcel_zone_assignment` against the updated zoning layer. Both `zoning.v_charlottetown_draft_zoning_boundaries_update` and the stable April alias `zoning.v_charlottetown_draft_zoning_boundaries_original` are queryable.

The refreshed registered parcel view and assignment contain 14,327 valid features; the source layer and registered view now use the same feature count.

Web zoning APIs use updated parcels and updated draft zoning by default. `/api/zoning/draft-original.geojson` exposes the April map, while `/api/zoning/draft.geojson?variant=original` is an equivalent selector. `/api/zoning-comparison/:pid` defaults to original bylaw versus updated draft; `mode=original-updated` switches to original draft versus updated draft. `/api/provisions-comparison` uses the same mode values. City view and parcel-map pages expose both draft map layers; restriction-stack, parcel 3D, storm-surge, and parcel lookup inherit the updated parcel and updated zoning defaults.

## Sources

- [Extracted July 30 draft PDF](../../../docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-07-30.pdf)
- [Normalized output README](../../../data/zoning/charlottetown-draft-2026-07-30/README.md)
- [Code-table match report](../../../data/zoning/charlottetown-draft-2026-07-30/code-table-match-report.json)
- [Staged source evidence](../../../data/staged-pdf/charlottetown-draft-2026-07-30/v2/stage-0/source-evidence.json)
- [Staged block inventory](../../../data/staged-pdf/charlottetown-draft-2026-07-30/v2/stage-1/block-inventory.json)
- [Municipal-fit map summary](../../../data/spatial/charlottetown/charlottetown-draft-map-layers-2026-07-30-municipal-fit.summary.json)
