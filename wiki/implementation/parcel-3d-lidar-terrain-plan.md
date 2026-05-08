---
type: implementation
tags:
  - web-ui
  - parcel-3d
  - lidar
  - terrain
  - charlottetown
  - postgis
updated: 2026-05-08
---

This page plans the preprocessing and integration path for using PEI LIDAR data as terrain and building-height inputs in the Charlottetown parcel 3D viewer.

# Parcel 3D LIDAR Terrain Plan

## Current Baseline

The `/parcel-3d?pid=PID` route uses `web/public/ui_kits/parcel-3d/index.html` and reads context from `/api/parcels/:pid/3d-context` in `web/server.js`.

The current API response contains the selected parcel, surrounding parcel boundaries, roads, and building footprints. Building properties already include `heightLidarM`, `heightLidarConfidence`, and `heightLidarStatus` where available. The browser viewer uses `heightLidarM` first, then estimated floor levels, then an 8 m fallback.

The current Three.js scene uses a flat ground plane. It does not render terrain elevation, slope, or parcel-relative ground height variation.

## Source Data

The raw LIDAR source is the COPC LAZ tile set in `maps/pei/lidar/*.copc.laz`. These files are preserved source data and must not be streamed directly to the browser.

Before any derived product is generated, inspect the source metadata for CRS, bounds, point classes, point density, vertical datum, units, and tile coverage. Use PDAL, GDAL, QGIS, or equivalent geospatial tooling. During initial shell inspection, `pdal` and `gdalinfo` were not available, so installing or exposing those tools is a prerequisite for implementation.

CRS and vertical datum verification is blocking. No elevation, building-height, shadow, or inundation-sensitive product should be accepted until horizontal and vertical references are known and documented.

## Preprocessing Pipeline

Generate derived products outside the browser:

1. Build a bare-earth DEM from ground-classified LIDAR points after metadata validation.
2. Build a DSM or per-building roof-height statistics from first-return or non-ground points.
3. Join building footprints to LIDAR-derived ground and roof elevations.
4. Populate or refresh building height fields with measured height, confidence, method, and status.
5. Generate browser-friendly terrain products as either clipped parcel-context patches or prebuilt terrain tiles.

Recommended first implementation is clipped terrain patches for the existing 250 m parcel context radius. City-scale terrain tiles can be added later if the viewer expands beyond parcel-focused scenes.

## Database and API Integration

Keep `web/server.js` as the database and file-serving boundary. The browser should not connect directly to PostGIS, raw LIDAR files, or local geospatial tooling.

Extend `/api/parcels/:pid/3d-context` to include terrain metadata and either a compact terrain mesh payload for the requested radius or a URL to a prebuilt terrain tile or patch.

Return geometries in WGS84 for browser compatibility, matching the current 3D context API pattern. Return elevation values in meters relative to the verified source vertical datum, and include metadata that identifies the vertical datum, generation method, source tiles, and fallback state.

Building height output should continue to support the existing `heightLidarM` client property. Add or preserve supporting status fields so the UI can distinguish measured LIDAR heights from level-derived or default fallback heights.

## Browser Rendering Changes

Replace the flat ground plane with a terrain mesh when valid terrain data is available. Keep the flat plane fallback when terrain is missing, unavailable for the selected parcel, or blocked by metadata validation failure.

Render buildings relative to terrain-adjusted ground elevation rather than assuming zero-height ground. Preserve existing orbit controls, parcel boundaries, roads, and shadow controls.

Display source and status metadata in the parcel 3D panel so users can distinguish measured terrain and building heights from fallback visualization values.

Raw LAZ files must never be fetched by the browser. Browser payloads should remain bounded to the selected parcel context radius unless a later terrain tile strategy is approved.

## Implementation Status

The first demo integration is implemented in `web/server.js` and `web/public/ui_kits/parcel-3d/index.html`.

The `/api/parcels/:pid/3d-context` response now includes a `terrain` object sampled from `data/spatial/charlottetown/lidar-terrain-dem/charlottetown-dem-epsg2961-1m.tif` with GDAL. The payload is a compact 41 by 41 elevation grid around the selected parcel context, not raw LAZ or a raw DEM stream. It includes `status`, `usage`, horizontal CRS, unresolved vertical datum, patch valid-cell ratio, base elevation, and the refined DEM QA coverage ratio.

The browser renders the DEM patch as a Three.js terrain mesh when `terrain.available` is true. Parcel boundaries, roads, and building bases sample the terrain height. If sampling fails or the patch has no valid cells, the viewer keeps the flat ground fallback and displays the fallback status.

This first implementation is demo-only. It depends on local GDAL availability through `GDAL_TRANSLATE_PATH` or the default `C:\Program Files\GDAL\gdal_translate.exe`, and it retains the unresolved vertical datum and non-authoritative terrain caveats.

## QA and Acceptance Checks

Metadata checks:

- CRS, bounds, units, point classes, density, and vertical datum are recorded before derived outputs are accepted.
- Source tile coverage overlaps the selected Charlottetown parcel test area.
- Tooling prerequisites are documented when PDAL, GDAL, or QGIS are required.

Derived data checks:

- DEM and DSM outputs preserve source provenance and generation parameters.
- Sample building footprints have ground, roof, and computed height values with method and confidence fields.
- Building height outliers are flagged instead of silently accepted.

API and UI checks:

- `/api/parcels/:pid/3d-context` remains the integration point for parcel 3D.
- The response includes terrain metadata and preserves existing parcel, building, and road behavior.
- The viewer renders a terrain mesh when terrain data exists and falls back to the flat plane when it does not.
- The UI identifies whether building heights are LIDAR-measured, level-derived, or default fallback.

## Open Decisions

- Exact derived terrain storage format: PostGIS raster, static terrain patch files, quantized mesh, or another compact format.
- Exact building-height refresh workflow and whether it updates existing PostGIS views, source tables, or a dedicated derived table.
- Tile or patch resolution for the first browser payload.
- Whether later tidal or storm-surge work should reuse the same DEM products or require a separate vertical-datum-normalized elevation surface with bathymetry.

## Sources

- [PEI LIDAR source directory](../../maps/pei/lidar)
- [Web server](../../web/server.js)
- [Parcel 3D UI](../../web/public/ui_kits/parcel-3d/index.html)
- [Web demo design kit plan](./web-demo-design-kit-plan.md)
- [Web UI stack](./web-ui-stack.md)
- [Root wiki index](../index.md)
