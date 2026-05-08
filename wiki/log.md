---
type: log
tags:
  - wiki
  - log
updated: 2026-05-08
---

This page is the append-only chronological record for root wiki changes, ingests, substantive queries, and lint passes.

Append new entries in reverse chronological order. Use this heading format:

```text
## [YYYY-MM-DD] type | Short title
```

## [2026-05-08] implementation | Charlottetown terrain DEM pipeline

Added [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) describing the first PDAL/GDAL bare-earth DEM workflow for PEI COPC LIDAR, including metadata gates, tile selection, ground filtering, 1 m EPSG:2961 output products, QA thresholds, and parcel 3D integration path. Updated [Root index](./index.md) with the new implementation page.

## [2026-05-08] source | PEI LIDAR and bathymetry metadata

Added [PEI LIDAR and bathymetry metadata](./sources/pei-lidar-bathymetry-metadata.md) summarizing local PDAL and GDAL inspection results for `maps/pei/lidar` and `maps/pei/bathymetry`, including LIDAR EPSG:2961 horizontal metadata, unresolved LIDAR vertical CRS, NONNA BAG ChartDatum metadata, GeoTIFF depth ranges, and backscatter intensity caveats. Updated [Root index](./index.md) with the new source page.

## [2026-05-08] implementation | Parcel 3D LIDAR terrain plan

Added [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) documenting the preprocessing path for PEI COPC LAZ source data, terrain and building-height derivation, `/api/parcels/:pid/3d-context` integration, browser fallback behavior, and CRS and vertical datum verification gates. Updated [Root index](./index.md) with the new implementation page.

## [2026-05-03] implementation | Provisions comparison page

Added `/provisions-comparison` and `/api/provisions-comparison` for draft Part 1 through Part 9 non-zone comparisons, with raw current-versus-draft part text and structured accepted section pairs filtered by selected draft part. The provisions UI now uses title-only part menu labels, lists structured matches in ascending order without a secondary menu, and supports collapsible structured pair cards from the pair header. Added a `Compare provisions` top-navigation link immediately after `Compare bylaws`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with endpoint behavior and scope limits.

## [2026-05-01] implementation | Web demo phase 8

Implemented phase 8 of the web demo design-kit plan by removing remaining mock-only lookup result code and inactive navigation from active demo routes, hardening disabled city-view parcel actions, and adding `npm run web:smoke` for route and API-contract checks. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and verification notes.

## [2026-05-01] implementation | Web demo phase 7

Implemented phase 7 of the web demo design-kit plan by adding `/api/zoning-comparison/:pid` and wiring `web/public/ui_kits/zoning-comparison/index.html` to live parcel zone comparison data with current and draft zone-section citations or explicit pending states. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and behavior notes.

## [2026-05-01] implementation | Web demo phase 5

Implemented phase 5 of the web demo design-kit plan by replacing the static map explorer mockup with a Leaflet parcel-centered map backed by `/api/parcels/:pid`, `/api/parcels.geojson`, `/api/zoning/current.geojson`, and `/api/zoning/draft.geojson`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and behavior notes.

## [2026-05-01] implementation | Web demo phase 4

Implemented phase 4 of the web demo design-kit plan by wiring `web/public/ui_kits/parcel-lookup/index.html` to `/api/addresses` for autocomplete and selected-PID redirects to `/map-explorer`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with completed phase status and behavior notes.

## [2026-05-01] implementation | Web demo phase 3

Implemented phase 3 of the web demo design-kit plan by adding bbox-filtered GeoJSON APIs for parcel candidates, current zoning boundaries, and draft zoning boundaries in `web/server.js`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with endpoint behavior, source SRID handling, and feature limits.

## [2026-05-08] implementation | Parcel 3D browser visualization

Added the parcel-specific `/parcel-3d?pid=PID` browser visualization to the web demo plan. The new page uses `/api/parcels/:pid/3d-context` for selected and adjacent parcel buildings, road context, parcel boundaries, and a 250 m default radius with seasonal shadow controls.

## [2026-05-01] implementation | Web demo phase 2

Implemented phase 2 of the web demo design-kit plan by adding civic address autocomplete and PID-based parcel resolution APIs in `web/server.js`. Updated [Web demo design kit plan](./implementation/web-demo-design-kit-plan.md) with the completed phase status and the provisional parcel identity constraint.

## [2026-05-01] implementation | Web demo phase 1

Completed phase 1 of the web demo design-kit plan by adding route entry points for parcel lookup, map explorer, city-view map, and zoning comparison, and promoting the selected `Island as needle` logo to `web/public/assets`.

## [2026-05-01] implementation | Web demo design kit plan

Added `implementation/web-demo-design-kit-plan.md` documenting the design-kit replacement plan, database API connection steps, UI cleanup tasks, demo acceptance criteria, timeline, risks, and open decisions.

## [2026-04-29] implementation | Web UI stack decision

Added `implementation/web-ui-stack.md` documenting the initial Docker-hosted Node web UI stack and first Charlottetown section-equivalence review page.

## [2026-04-28] maintenance | Wiki-first role workflows

Applied the wiki-first setup pattern across role skills so Business Analyst, Coding Architect, Data Quality Analyst, Debugger, GIS Specialist, and QA Reviewer read `Project Management` identified wiki pages and use `wiki/index.md` for additional context during normal task setup.

## [2026-04-28] maintenance | Wiki lookup as normal role workflow

Removed the clause-specific lookup pointer from the `Data Engineer` skill and moved wiki discovery into the normal `Project Management` classification and `Data Engineer` setup workflow.

## [2026-04-28] maintenance | Clause-label guidance relocation

Moved task-specific by-law clause label handling guidance from the `Data Engineer` skill into `domain/bylaw-clause-labels.md`.

## [2026-04-28] maintenance | Root instruction streamlining

Moved non-universal startup instructions out of root `AGENTS.md`: role gates and implementation protocol moved to the `Project Management` skill, by-law clause label handling moved to data extraction and quality skills, and Charlottetown workstream context moved to the Charlottetown wiki.

## [2026-04-28] setup | Root wiki schema scaffold

Created the root wiki schema, catalog, log, and top-level page areas for source summaries, domain concepts, platform notes, and implementation notes. Linked the existing Charlottetown wiki as the active project wiki.

## Sources

- [Wiki schema](./AGENTS.md)
