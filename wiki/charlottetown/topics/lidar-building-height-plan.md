---
type: topic
tags:
  - charlottetown
  - lidar
  - buildings
  - spatial
  - planning
updated: 2026-05-06
---

This page records the implemented workflow for deriving Charlottetown building heights from PEI 2020 LiDAR and attaching the results to a derived `public."CHTWN_Buildings"` layer.

# LiDAR Building Height Plan

## Objective

Populate building-height attributes for every feature in a derived `public."CHTWN_Buildings"` layer using the COPC LAZ tiles in `maps/pei/lidar`, while preserving `public."CHTWN_OSM_Buildings"` as the unmodified source layer.

## Implementation Status

Implemented on 2026-05-06 by `scripts/build-charlottetown-lidar-buildings.py`.

The script exports source footprints from `public."CHTWN_OSM_Buildings"`, transforms them to EPSG:2961 for LiDAR sampling, reads the COPC LAZ tiles with `laspy`, derives robust roof and ground elevations, writes a reproducible CSV/summary under `data/spatial/charlottetown/lidar-building-heights`, and rebuilds `public."CHTWN_Buildings"` from the source layer plus LiDAR fields.

QA evidence from the initial full run:

| Check | Result |
| --- | --- |
| Source rows | 13,144 in `public."CHTWN_OSM_Buildings"`. |
| Derived rows | 13,144 in `public."CHTWN_Buildings"`. |
| Derived height coverage | 13,144 with `height_lidar_m`; 0 null. |
| Confidence distribution | 12,462 high, 17 medium, 5 low, 660 needs_review. |
| Height distribution | min 0.05 m, median 7.01 m, p95 13.53 m, max 38.42 m. |
| Geometry QA | 0 invalid geometries, 0 empty geometries. |
| Source preservation QA | 0 mismatches for copied source attributes or geometry. |
| OSM height-tag comparison | 30 comparable OSM height tags; median absolute delta 3.99 m. |

## Current Inputs

| Input | Current known state | Use |
| --- | --- | --- |
| `maps/pei/lidar/*.copc.laz` | 68 PEI 2020 COPC LAZ tiles whose filenames encode 1 km tile origins. | Source point cloud for roof and ground elevations. |
| `public."CHTWN_OSM_Buildings"` | 13,144 valid `MULTIPOLYGON` features, SRID 4326, clipped to `public."CHTWN_Municipal_Boundary"`. | Source building footprint layer. |
| Existing OSM attributes | 30 features have a non-empty OSM `height` tag and 263 have `levels`; 264 have either height or levels. | QA comparison and fallback context, not the primary LiDAR result. |

## Output Contract

The derived `public."CHTWN_Buildings"` layer receives LiDAR-derived attributes with explicit provenance and confidence fields. Do not collapse them into the OSM tag fields.

Proposed fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `height_lidar_m` | numeric | Recommended building height in metres. |
| `height_lidar_method` | text | Method identifier, for example `roof_p95_minus_ground_p05_v1`. |
| `height_lidar_confidence` | text | `high`, `medium`, `low`, or `needs_review`. |
| `height_lidar_source_tiles` | text[] | COPC LAZ tile names used for the feature. |
| `height_lidar_point_count` | integer | Count of LiDAR points used inside or near the building footprint. |
| `height_lidar_ground_m` | numeric | Estimated ground elevation used as the base. |
| `height_lidar_roof_m` | numeric | Estimated roof elevation used as the top. |
| `height_lidar_status` | text | Derivation status, currently `derived` for every initial row. |
| `height_lidar_updated_at` | timestamptz | Derivation timestamp. |
| `height_lidar_provenance` | jsonb | Detailed derivation metadata and secondary quantiles. |

## Orchestration Plan

1. Confirm source metadata.
   - Use `pdal info` or equivalent GDAL/PDAL tooling to record CRS, bounds, classification availability, vertical units, and point dimensions for representative COPC tiles.
   - Verify whether the tiles contain classified ground and building points. If classes are absent or unreliable, route to a DSM/DTM raster workflow instead of direct class filtering.

2. Normalize working geometry.
   - Create a staging table or temporary extract of `public."CHTWN_OSM_Buildings"` transformed from SRID 4326 to the LiDAR CRS.
   - Preserve `id`, `osm_type`, `osm_id`, `building`, `name`, `levels`, `source_tags`, and source geometry.
   - Validate invalid, empty, very small, and multipart footprints before sampling.

3. Build reusable LiDAR derivatives.
   - Preferred path: rasterize LiDAR to local DSM and DTM surfaces at a documented resolution, then compute normalized height as DSM minus DTM.
   - Alternative path: for each footprint, crop COPC points by footprint plus a small buffer, derive ground from classified ground points or local neighbourhood low quantiles, and derive roof from high non-ground quantiles.
   - Keep derivatives under a generated spatial-data path, not in `maps/pei/lidar`, because the LAZ files are raw inputs.

4. Derive per-building metrics.
   - For each footprint, calculate roof elevation using robust upper quantiles such as p90, p95, and p98 rather than the absolute maximum.
   - Estimate ground elevation using classified ground points within the footprint buffer or the DTM surface under the footprint.
   - Store supporting metrics: area, sampled point count, tile count, ground/roof quantiles, raw height candidates, and selected recommended height.

5. Assign confidence and review flags.
   - Mark `high` when point count is sufficient, footprint coverage is good, ground and roof estimates are stable, and height is plausible.
   - Mark `medium` when estimates are plausible but sparse, multipart, or affected by edge coverage.
   - Mark `low` or `needs_review` for tiny footprints, missing ground, missing roof returns, extreme heights, negative heights, bridges, tanks, construction artifacts, or poor tile coverage.
   - Compare LiDAR-derived heights against the 30 OSM height tags and the 263 `levels` values as QA controls, allowing that OSM levels are storeys rather than metres.

6. Write results through a repeatable script.
   - Rebuild `public."CHTWN_Buildings"` from `public."CHTWN_OSM_Buildings"` plus LiDAR-derived fields.
   - Keep `public."CHTWN_OSM_Buildings"` unchanged as the source layer.
   - Keep a CSV and JSON summary output so results can be audited before or after database creation.

7. QA the database result.
   - Verify all 13,144 buildings receive either `height_lidar_m` or a non-null confidence/status explaining why no height was derived.
   - Verify no source OSM tags or geometries changed.
   - Sample controls across downtown, waterfront, industrial, residential, small accessory buildings, and tile boundaries.
   - Report residuals against OSM height tags, distributions by confidence, null counts, outlier counts, and representative map screenshots or QGIS inspection notes.

## Implementation Notes

- Use explicit schema-qualified names for all database references.
- Treat `public."CHTWN_OSM_Buildings"` as a public spatial source layer; the implemented derived layer is `public."CHTWN_Buildings"`.
- The Postgres MCP path is read-only. Any database mutation should be done by a script using the repository's normal `psycopg` connection pattern or by an explicit migration runner.
- Do not use existing OSM height or level fields as replacement data for LiDAR heights. Use them only as independent comparison controls and optional fallback display metadata.
- Keep raw LAZ files immutable. Generated rasters, staging tables, reports, and QA summaries should be reproducible from the raw tiles and building footprints.

## Open Decisions

| Decision | Default for first implementation | Why it matters |
| --- | --- | --- |
| Height definition | Roof p95 minus ground p05/DTM median under footprint. | Avoids chimneys, antennas, and isolated outlier returns. |
| DTM source | Build from LiDAR ground class if available; otherwise derive local ground from neighbourhood low quantiles. | Building height requires a base elevation, not just roof elevation. |
| Storage location | Rebuild `public."CHTWN_Buildings"` from `public."CHTWN_OSM_Buildings"` plus generated staging output. | Keeps the OSM source table unchanged while providing a GIS-ready derived layer. |
| Existing height handling | Preserve OSM tags and add separate LiDAR fields. | Prevents source conflation. |
| Review artifact | CSV or GeoPackage with all low-confidence and outlier buildings. | Enables QGIS/manual QA before accepting the backfill. |

## Completion Criteria

- LiDAR CRS, vertical units, classification availability, and bounds are documented.
- Every target building has a derived height or explicit non-derived status.
- Existing OSM tags, levels, ids, and geometries are unchanged.
- The derivation is rerunnable from raw COPC LAZ tiles and the current building table.
- QA reports counts by confidence, null status, outliers, and OSM comparison residuals.

## Sources

- [Charlottetown wiki guide](../README.md)
- [Charlottetown workstream context](./workstream-context.md)
- [Zoning data-layer conventions](./data-layer-conventions.md)
- `maps/pei/lidar`
- `public."CHTWN_OSM_Buildings"`
- `public."CHTWN_Buildings"`
- `public."CHTWN_Municipal_Boundary"`
- `scripts/build-charlottetown-lidar-buildings.py`
- `data/spatial/charlottetown/lidar-building-heights/chtwn-building-lidar-heights-full.summary.json`
