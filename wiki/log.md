---
type: log
tags:
  - wiki
  - log
updated: 2026-05-27
---

This page is the append-only chronological record for root wiki changes, ingests, substantive queries, and lint passes.

Append new entries in reverse chronological order. Use this heading format:

```text
## [YYYY-MM-DD] type | Short title
```

## [2026-05-27] implementation | Release help and MCP scaffold

Added [Release help and MCP plan](./implementation/release-help-and-mcp-plan.md) to record the Markdown-source/release-output documentation boundary, `help` schema purpose, web help API boundary, and repo-local `mdopendata-mcp` package role. Implemented the first help schema migration, seed script, web help APIs, `/help` route, and local MCP package scaffold.

## [2026-05-25] source | Local Government in British Columbia ingestion plan

Added [Local Government in British Columbia](./sources/lgbc-local-government-bc.md) as a source summary for `docs/LGBC-All.pdf` and added [Local Government in British Columbia ingestion plan](../plan/lgbc-ingestion-plan.md) for raw-first structure indexing, exhibit extraction, chapter review, benchmark-candidate discovery, and Charlottetown prototype mapping.

## [2026-05-25] source | Local Government in British Columbia source registration

Completed Phase 1 source registration for `docs/LGBC-All.pdf` under `data/sources/lgbc/`, including PDF metadata, full layout text, 250 per-page text files, registration skeletons for structure, exhibits, and chapter review, and extraction notes.

## [2026-05-25] source | Local Government in British Columbia structure extraction

Completed Phase 2 structure extraction for `docs/LGBC-All.pdf`, populating `data/sources/lgbc/structure_index.json` with front matter, 13 chapters, 78 numbered chapter sections, appendix sections, and back matter, and `data/sources/lgbc/exhibit_index.json` with 41 listed exhibits. Recorded that these observed counts supersede the initial plan estimates of 76 sections and 45 exhibits.

## [2026-05-25] source | Local Government in British Columbia chapter review queue

Completed Phase 3 chapter review queue setup for `docs/LGBC-All.pdf`, populating `data/sources/lgbc/chapter_review_queue.json` with 18 pending records for 13 chapters, 1 appendix, and 4 back-matter units. The queue preserves the first-pass review order of Chapter 6, Chapter 1, Chapter 10, Chapter 12, Chapter 7, and Chapter 8.

## [2026-05-25] source | Local Government in British Columbia Chapter 6 review

Completed the Chapter 6 service-delivery review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 6: Service Delivery](./sources/lgbc/chapter-6-service-delivery.md) with source claims, exhibit use, benchmark and process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 1 review

Completed the Chapter 1 introduction review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 1: Introduction](./sources/lgbc/chapter-1-introduction.md) with source claims, fiscal-equivalence framing, collective-problem categories, benchmark and process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 10 review

Completed the Chapter 10 regulatory and development functions review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 10: Regulatory And Development Functions](./sources/lgbc/chapter-10-regulatory-development-functions.md) with source claims, planning/zoning/subdivision/enforcement process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 12 review

Completed the Chapter 12 finance review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 12: Finance](./sources/lgbc/chapter-12-finance.md) with source claims, revenue/tax/fee/transfer/debt/reserve process candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 7 review

Completed the Chapter 7 protective services review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 7: Protective Services](./sources/lgbc/chapter-7-protective-services.md) with source claims, police/fire/emergency performance candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 8 review

Completed the Chapter 8 engineering services review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 8: Engineering Services](./sources/lgbc/chapter-8-engineering-services.md) with source claims, water/wastewater/solid-waste/transportation/transit performance candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 9 review

Completed the Chapter 9 human services review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 9: Human Services](./sources/lgbc/chapter-9-human-services.md) with source claims, parks/recreation/library/museum/public-health/social-housing candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Chapter 11 review

Completed the Chapter 11 labour relations review for `docs/LGBC-All.pdf`, adding [LGBC Chapter 11: Labour Relations](./sources/lgbc/chapter-11-labour-relations.md) with source claims, workforce/unionization/bargaining-unit/service-continuity candidates, Charlottetown prototype implications, required data inventory, and review limits.

## [2026-05-25] source | Local Government in British Columbia Phase 5 candidate catalogue

Started Phase 5 by generating `data/sources/lgbc/benchmark_process_candidate_catalogue.json` and adding [LGBC Benchmark And Process Candidate Catalogue](./sources/lgbc/benchmark-process-candidate-catalogue.md). The initial catalogue contains 86 source-derived candidates from Chapters 1, 6, 7, 8, 9, 10, 11, and 12, all pending Phase 6 Charlottetown source mapping.

## [2026-05-25] source | Local Government in British Columbia Phase 6 Charlottetown mapping

Started Phase 6 by generating `data/sources/lgbc/charlottetown_prototype_mapping.json` and adding [LGBC Charlottetown Prototype Mapping](./sources/lgbc/charlottetown-prototype-mapping.md). The first-pass mapping covers all 86 Phase 5 candidates, classifying 10 as strong source-family matches, 56 as partial source-family matches, and 20 as source gaps, with no candidate ready for public metrics or scoring.

## [2026-05-25] source | Local Government in British Columbia planning land-use dataset review

Continued Phase 6 by generating `data/sources/lgbc/charlottetown_planning_land_use_dataset_review.json` and adding [LGBC Charlottetown Planning And Land-Use Dataset Review](./sources/lgbc/charlottetown-planning-land-use-dataset-review.md). The review covers 10 Chapter 10 candidates and finds 2 ready for source-completeness review, 2 partial, 1 sample-only, and 5 source gaps for required process or outcome datasets.

## [2026-05-20] implementation | Agenda tree component split

Refactored `web/public/ui_kits/shared/agenda-tree.jsx` into a generic `PortalTreeView`, `RolePresetTabs`, and a meeting-specific `buildMeetingAgendaTree` adapter while preserving the existing `window.CouncilAgendaTree.AgendaTree`, `allItems`, and `buildAgendaTree` API used by `/council-meetings`. Updated [Municipal portal UI component architecture](./product/municipal-portal-ui-component-architecture.md) with the agenda tree contract.

## [2026-05-20] implementation | Municipal portal component architecture

Added [Municipal portal UI component architecture](./product/municipal-portal-ui-component-architecture.md) to define the reusable view-component contract, dependency posture, page-context expectations, first component families, and implementation-independence rules. Updated [Municipal portal UI architecture](./product/municipal-portal-ui-architecture.md) to reframe the basic-HTML feasibility study around component contracts rather than a blanket rewrite.

## [2026-05-20] product | Municipal portal 1.0 shell

Added the municipal portal product wiki area with product purpose, 1.0 roadmap, role model, UI architecture, and domain inventory pages. Added a React/Babel portal shell at `/`, route stubs for meetings, business items, documents, planning, budgets, maps, validation, and lab tools, a Charlottetown theme stylesheet, and `/api/portal/context` for the stable page-context contract. Updated [Root index](./index.md) and [Web UI stack](./implementation/web-ui-stack.md) to record the retained React/Babel stack and the basic-HTML feasibility-study gate before new reusable component coding.

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

## [2026-05-08] implementation | Terrain DEM demo acceptance

Updated [Charlottetown terrain DEM pipeline](./implementation/charlottetown-terrain-dem-pipeline.md) to record that the current 97.4905% refined land coverage DEM is acceptable for demo-only parcel 3D and storm-surge visualization, while deferring the 99% refined coverage target to backlog work if demo results are not satisfactory.

## [2026-05-08] implementation | Parcel 3D demo terrain integration

Implemented the first demo terrain integration for `/parcel-3d`: `/api/parcels/:pid/3d-context` now returns a compact GDAL-sampled DEM patch with demo-status metadata and fallback state, and the Three.js viewer renders the terrain mesh when available while preserving flat terrain fallback. Updated [Parcel 3D LIDAR terrain plan](./implementation/parcel-3d-lidar-terrain-plan.md) with the implemented API/UI behavior and local GDAL dependency.

## [2026-05-08] deployment | Parcel 3D terrain Docker redeploy

Rebuilt and redeployed the Docker `web` service for parcel 3D terrain support. The web image now installs GDAL tools, and the normal app port returns `demo_terrain` metadata for `/api/parcels/358960/3d-context?radiusM=250`.

## [2026-05-08] implementation | Storm surge demo page

Added the demo-only `/storm-surge` web page, reusing `/api/parcels/:pid/3d-context` to render the existing parcel 3D terrain, parcels, roads, and buildings with a transparent static water plane. Added controls for Charlottetown tide presets, 0-10 m storm surge, storm/category 1/category 2 wind labels, and 0-100 year sea-level-rise scenarios. Added [Storm surge demo plan](./implementation/storm-surge-demo-plan.md) and updated [Root index](./index.md) with the new implementation page.

## [2026-05-08] deployment | Storm surge navigation Docker redeploy

Added the storm-surge top-navigation link across the web UI kit pages and rebuilt/redeployed the Docker `web` service. Verified deployed HTTP 200 responses on port 3000 for `/parcel-lookup`, `/city-view`, `/map-explorer`, `/zoning-comparison`, `/restriction-stack`, `/provisions-comparison`, `/parcel-3d`, and `/storm-surge`, each containing the Storm surge navigation text.

## [2026-05-08] implementation | Storm surge visual datum offset

Adjusted the `/storm-surge` demo water rendering to apply a configurable visual datum offset after composing chart-datum tide height, surge, and sea-level rise. The default offset is `-1.72 m`, matching the CHS Charlottetown station 01700 CGVD28 offset, so the default full/new moon high tide renders at 1.25 m in the current terrain display space rather than 2.97 m. Updated [Storm surge demo plan](./implementation/storm-surge-demo-plan.md) with the offset behavior and continued non-authoritative caveat.

## [2026-05-08] implementation | Storm surge context and water-bed rendering

Expanded the `/storm-surge` demo context radius from 250 m to 350 m, which is the current API terrain-patch cap and gives about 1.96 times the rendered area. Renamed neap-tide controls to half/quarter moon high and low tide. Adjusted terrain rendering so DEM NoData cells in the patch render as a lowered `-4 m` water bed, allowing known water and shoreline gaps to appear immersed under the water plane instead of flat at zero elevation.

## [2026-05-08] fix | Storm surge terrain base normalization

Fixed the `/storm-surge` water plane rendering frame by subtracting the terrain patch `baseElevationM` from the composed water level after the visual datum offset. This matches the API terrain normalization, where DEM elevations are sent to the browser relative to the patch median. Removed the quarter-moon wording from the half-moon tide controls and lowered the NoData water bed from `-4 m` to `-14 m`.

## [2026-05-08] fix | Storm surge datum range and NoData holes

Changed the `/storm-surge` visual datum offset default to `-1.8 m` and narrowed the slider to `-2.8 m` through `-0.8 m` for calibration around the observed plausible baseline. Clarified the wind event control as informational only because surge remains manually controlled by the surge slider. Removed the lowered NoData water bed behavior so terrain gaps no longer fill as isolated water holes before the outer water plane reaches them.

## [2026-05-08] fix | Storm surge wind removal and water-bed restore

Removed the `/storm-surge` wind event control and wind references. Restored lowered NoData terrain rendering at `-14 m` so DEM gaps again appear as submerged water-bed areas.

## [2026-05-08] implementation | Parcel 3D building terrain seating

Adjusted the parcel 3D terrain renderer so building bases use bilinear terrain sampling across each footprint and add a short foundation skirt to reduce visible floating and ground intersection on sloped DEM terrain. Rebuilt and redeployed the Docker `web` service after the rendering fix.

## [2026-05-12] implementation | Council meeting prototype wiki and extraction

Added the [Council and committee meetings](./council-committee-meetings/README.md) wiki area for meeting-preparation workflows. Added the first JSON-first Charlottetown regular council meeting extraction branch for the May 12, 2026 agenda/package and documented the public, council/committee, and municipal staff workflow model.

## [2026-05-12] implementation | Council meeting audience tabs

Expanded `/council-meetings` from a public-first view to functional public, council, and staff tabs using the same JSON-backed meeting API.

## [2026-05-12] implementation | Agenda tree and rezoning endpoint copies

Reworked `/council-meetings` into a three-pane workspace with an agenda-order left tree, audience-specific general pages, selected-item package text panes, and rezoning tool panels. Added copied meeting-specific rezoning routes for parcel lookup, zoning comparison, spatial restrictions, and storm surge.

## [2026-05-12] implementation | Council package ToC and agenda outputs

Extended the May 12 Charlottetown council extraction to emit `agenda.json` and `toc.json` beside `meeting.json`. The ToC covers all 256 package pages as logical documents with page counts, summaries, boundary observations, template categories where known, and non-PDF page reproduction options; full package content extraction remains deferred except for the two rezoning items used by the web endpoints.

## [2026-05-13] project | Council meeting database cleanup backlog

Added a council-meetings backlog item to clean up agenda-related blank tables in the PostGIS `public` schema, including confirmation of empty tables, provenance checks, and removal or quarantine without affecting JSON-first meeting outputs.

## [2026-05-13] implementation | Council meeting database importer and schema backlog

Added the council meeting database importer and database-preferred `/council-meetings` API read path. Updated the council-meetings wiki backlog to table the broader city-portal subject-schema decision until source documents and endpoint requirements are clearer.

## [2026-05-13] implementation | Document import agenda tree and taxonomy

Extracted the shared council agenda tree for `/council-meetings` and `/document-import`, with Planning & Heritage and New Business child items nested under their standing-committee parents. Added the agenda/package document taxonomy page for document-import source classes, attachment types, and reusable workflow templates.

## [2026-05-14] implementation | Document import agenda and business bindings

Updated `/document-import` so the document panel groups package documents by agenda-item set and exposes editable agenda-item and item-of-business bindings. Added `business_items` to `meeting.json`, `agenda_item_id` and `business_item_id` to `toc.json`, and `council.package_document` persistence linked to `council.agenda_item` and `council.business_item`.

## Sources

- [Wiki schema](./AGENTS.md)
Implemented the first durable business-item identity layer for council-meeting ingestion: added evidence, relationship, and candidate-link tables; added Charlottetown identity configuration plus a deterministic evidence builder; exposed identity graph payload fields through the web API and document-import UI; and documented immutable-ID plus conservative-review behavior in the council-meetings wiki.
Extended `/document-import` with agenda-hierarchy, business-item-hierarchy, and candidate-link review modes. Agenda mode now lists documents linked to the selected agenda item, business mode lists meeting-local appearances and linked documents for the selected durable item, and queue mode records accept/reject decisions in QA feedback.
