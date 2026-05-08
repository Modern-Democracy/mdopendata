---
type: topic
tags:
  - charlottetown
  - lidar
  - parcels
  - spatial
  - planning
updated: 2026-05-06
---

This page records the implemented parcel-level LiDAR-derived metrics workflow for Charlottetown parcels using the existing parcel, building, and PEI 2020 LiDAR inputs.

# Parcel LiDAR Metrics Plan

## Objective

Create a derived parcel layer or table that summarizes terrain, building, canopy, and confidence metrics for every feature in `public."CHTWN_Parcel_Map"` without mutating the source parcel layer.

## Implementation Status

Implemented on 2026-05-06 by `scripts/build-charlottetown-parcel-lidar-metrics.py`.

The first implementation creates `public."CHTWN_Parcel_LiDAR_Metrics"` with one row per source parcel. Building metrics are assigned from `public."CHTWN_Buildings"` by largest parcel overlap. Terrain metrics use sampled classified ground returns inside parcels. Canopy metrics are candidate non-ground height-above-ground summaries from sampled returns and are flagged as classification-limited because v1 does not use a full DTM/CHM raster workflow.

Initial QA evidence:

| Check | Result |
| --- | --- |
| Source parcel rows | 13,833 in `public."CHTWN_Parcel_Map"`. |
| Derived parcel rows | 13,833 in `public."CHTWN_Parcel_LiDAR_Metrics"`. |
| Source preservation | 0 mismatches for copied parcel fields or geometry. |
| Geometry QA | 0 invalid derived geometries, 0 empty derived geometries. |
| Building assignment | 13,144 assigned buildings, matching `public."CHTWN_Buildings"`. |
| Parcels with buildings | 11,108. |
| Parcels with sampled terrain points | 13,152. |
| Confidence distribution | 51 high, 13,101 medium, 681 needs_review. |
| Main review flags | 13,750 canopy classification-limited, 1,374 building split-overlap, 681 no ground points, 28 no LiDAR points. |
| QGIS styles | Building height, building coverage, ground relief, canopy cover, and confidence styles written under `data/spatial/charlottetown/lidar-parcel-metrics`. |

## Current Inputs

| Input | Current known state | Use |
| --- | --- | --- |
| `public."CHTWN_Parcel_Map"` | 13,833 valid `MULTIPOLYGON` parcels, SRID 2954. | Source parcel geometry and parcel candidate identifiers. |
| `public."CHTWN_Buildings"` | 13,144 building features with `height_lidar_m` populated for all rows. | Building-height and built-form summaries by parcel. |
| `maps/pei/lidar/*.copc.laz` | PEI 2020 COPC LAZ tiles in EPSG:2961 with classified ground points observed. | Raw source for sampled terrain and candidate canopy metrics. |
| `public."CHTWN_Municipal_Boundary"` | Municipal boundary used for Charlottetown clipping. | Spatial extent and QA boundary control. |

## Proposed Output

The implemented output is a derived layer named `public."CHTWN_Parcel_LiDAR_Metrics"` keyed to `public."CHTWN_Parcel_Map".fid`.

Core source fields to carry forward:

| Field | Meaning |
| --- | --- |
| `source_parcel_fid` | Source parcel `fid`. |
| `parcel_candidate_id` | Existing parcel candidate id. |
| `source_map` | Existing source map value. |
| `method` | Existing parcel generation method. |
| `parcel_area_m2` | Parcel area in square metres. |
| `geom` | Source parcel geometry. |

## Metric Families

### Building Metrics

Use `public."CHTWN_Buildings"` intersected with parcels. Assign buildings to parcels by largest intersection area, with a review flag when a building significantly overlaps multiple parcels.

| Metric | Meaning |
| --- | --- |
| `building_count` | Count of assigned buildings. |
| `building_coverage_m2` | Sum of assigned building footprint areas clipped or assigned to the parcel. |
| `building_coverage_ratio` | Building coverage divided by parcel area. |
| `building_height_max_m` | Maximum `height_lidar_m` on assigned buildings. |
| `building_height_p50_m` | Median assigned building height. |
| `building_height_p95_m` | 95th percentile assigned building height. |
| `building_volume_proxy_m3` | Sum of footprint area multiplied by LiDAR height. |
| `building_height_confidence_min` | Lowest confidence among assigned buildings. |
| `building_height_needs_review_count` | Count of assigned buildings with `height_lidar_confidence='needs_review'`. |

### Terrain Metrics

Derive parcel terrain from ground-class LiDAR points or a generated DTM. Use EPSG:2961 for LiDAR processing and transform parcel geometries as needed.

| Metric | Meaning |
| --- | --- |
| `ground_elev_min_m` | Minimum ground elevation in parcel. |
| `ground_elev_p50_m` | Median ground elevation. |
| `ground_elev_max_m` | Maximum ground elevation. |
| `ground_relief_m` | Max minus min ground elevation. |
| `slope_p50_deg` | Median terrain slope from DTM. |
| `slope_p95_deg` | 95th percentile terrain slope. |
| `low_point_elev_m` | Low elevation control for drainage screening. |
| `terrain_point_count` | Ground points or DTM cells contributing to metrics. |

### Canopy And Vegetation Metrics

Use normalized height above ground from non-ground returns. The first implementation marks canopy metrics as classification-limited because it samples non-ground candidate returns directly and does not yet use a full building-masked CHM raster.

| Metric | Meaning |
| --- | --- |
| `canopy_cover_ratio_2m` | Share of parcel area or sampled cells with vegetation-like height above 2 m. |
| `canopy_height_p50_m` | Median canopy height where canopy exists. |
| `canopy_height_p95_m` | 95th percentile canopy height. |
| `tall_canopy_cover_ratio_8m` | Share of parcel with canopy above 8 m. |
| `vegetation_point_count` | Count of candidate vegetation returns used. |

### QA And Provenance Metrics

| Metric | Meaning |
| --- | --- |
| `lidar_source_tiles` | COPC LAZ tiles contributing to the parcel. |
| `lidar_metric_method` | Method version, for example `parcel_lidar_metrics_v1`. |
| `lidar_metric_confidence` | `high`, `medium`, `low`, or `needs_review`. |
| `lidar_metric_flags` | Array or jsonb list of review flags. |
| `lidar_metric_updated_at` | Derivation timestamp. |
| `lidar_metric_provenance` | jsonb with thresholds, CRS, source tables, and summary counts. |

## Orchestration Plan

1. Confirm source controls.
   - Verify parcel count, geometry validity, SRID, and area ranges in `public."CHTWN_Parcel_Map"`.
   - Verify `public."CHTWN_Buildings"` still has complete `height_lidar_m` coverage.
   - Confirm LiDAR tile CRS, vertical units, classification dimensions, and ground-class availability.

2. Create working geometries.
   - Transform parcels from SRID 2954 to LiDAR SRID 2961 for point-cloud sampling.
   - Preserve source parcel ids and geometry.
   - Build spatial indexes for parcel and building joins.

3. Assign buildings to parcels.
   - Intersect `public."CHTWN_Buildings"` with `public."CHTWN_Parcel_Map"`.
   - Assign each building to the parcel with the largest overlap area.
   - Flag buildings with no parcel, tiny overlap, or split overlap above a selected threshold.
   - Aggregate building counts, coverage, height percentiles, confidence counts, and volume proxy by parcel.

4. Build terrain derivatives.
   - Preferred path: generate DTM tiles from ground-class points, then sample DTM cells by parcel.
   - Lightweight path: directly sample classified ground points inside each parcel and compute elevation quantiles.
   - For slope metrics, use a DTM raster rather than raw irregular points.

5. Build canopy derivatives.
   - Create normalized height above local ground using DTM or nearby ground quantiles.
   - Exclude points inside assigned building footprints when estimating vegetation metrics.
   - Apply height thresholds such as 2 m for canopy and 8 m for tall canopy.

6. Create derived parcel layer.
   - Create `public."CHTWN_Parcel_LiDAR_Metrics"` from source parcel fields plus metric fields.
   - Keep `public."CHTWN_Parcel_Map"` unchanged.
   - Write generated CSV/GeoPackage or JSON summaries under `data/spatial/charlottetown/lidar-parcel-metrics`.

7. Add QGIS styling.
   - Add styles for `building_height_max_m`, `building_coverage_ratio`, `ground_relief_m`, `slope_p95_deg`, and `canopy_cover_ratio_2m`.
   - Keep at least one QA style for `lidar_metric_confidence` or `lidar_metric_flags`.

8. QA the result.
   - Verify output row count equals 13,833 parcels.
   - Verify source parcel fields and geometries are preserved.
   - Verify all parcels receive either metrics or explicit no-data/status flags.
   - Check building assignment totals against `public."CHTWN_Buildings"` count.
   - Report distributions, null counts, confidence counts, split-building counts, no-building parcel counts, terrain no-data parcels, and canopy no-data parcels.

## Review Flags

Use explicit flags instead of silently accepting weak metrics:

| Flag | Meaning |
| --- | --- |
| `no_lidar_points` | No LiDAR points or raster cells intersected the parcel. |
| `no_ground_points` | Terrain metric could not use ground returns. |
| `low_terrain_sample` | Ground or DTM sample count below threshold. |
| `building_split_overlap` | One or more buildings overlapped multiple parcels materially. |
| `building_no_parcel_match` | A nearby building could not be assigned to a parcel. |
| `canopy_building_overlap_uncertain` | Canopy returns could not be separated cleanly from structures. |
| `tiny_parcel` | Parcel area is too small for stable parcel-level LiDAR metrics. |

## Completion Criteria

- `public."CHTWN_Parcel_LiDAR_Metrics"` exists with one row per source parcel.
- `public."CHTWN_Parcel_Map"` remains unchanged.
- Building assignment accounts for every `public."CHTWN_Buildings"` row or records why it was excluded.
- Terrain and canopy metrics carry confidence/status fields.
- Generated reports summarize row counts, null counts, confidence, review flags, and metric distributions.
- QGIS styles exist for at least one building, one terrain, one canopy, and one QA metric.

## Sources

- [LiDAR building height plan](./lidar-building-height-plan.md)
- [Charlottetown workstream context](./workstream-context.md)
- `public."CHTWN_Parcel_Map"`
- `public."CHTWN_Buildings"`
- `public."CHTWN_Municipal_Boundary"`
- `maps/pei/lidar`
- `scripts/build-charlottetown-parcel-lidar-metrics.py`
- `data/spatial/charlottetown/lidar-parcel-metrics/chtwn-parcel-lidar-metrics-full.summary.json`
