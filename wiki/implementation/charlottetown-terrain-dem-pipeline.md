---
type: implementation
tags:
  - lidar
  - terrain
  - dem
  - gdal
  - pdal
  - charlottetown
  - gis
updated: 2026-05-08
---

This page designs the first repeatable PDAL/GDAL pipeline for producing a Charlottetown bare-earth terrain DEM from PEI COPC LIDAR source tiles.

# Charlottetown Terrain DEM Pipeline

## Objective

Build a first bare-earth DEM for Charlottetown parcel 3D terrain work from `maps/pei/lidar/*.copc.laz`.

The first product is a processing artifact for validation and later browser-terrain derivation. It is not yet an authoritative flood, tidal, or storm-surge surface because the LIDAR vertical datum is unresolved.

## Inputs and Outputs

Inputs:

- Raw LIDAR: `maps/pei/lidar/*.copc.laz`
- Municipal clipping boundary: `maps/pei/CHTWN_Municipal_Boundary.geojson`
- Existing LIDAR-derived context: building height script and parcel metric script under `scripts/`

First outputs:

- `data/spatial/charlottetown/lidar-terrain-dem/charlottetown-dem-epsg2961-1m.tif`
- `data/spatial/charlottetown/lidar-terrain-dem/charlottetown-dem-epsg2961-1m-hillshade.tif`
- `data/spatial/charlottetown/lidar-terrain-dem/charlottetown-dem-epsg2961-1m.summary.json`
- Optional quicklook render under the same output directory

Keep the output CRS as EPSG:2961 for the first DEM because the source LIDAR is EPSG:2961 and this avoids unnecessary interpolation before QA. Reproject or resample only for browser products after the source DEM passes checks.

## Pipeline Design

1. Metadata gate:
   - Confirm `pdal` and `gdalinfo` are callable.
   - Record PDAL version, GDAL version, source file count, source point count, aggregate bounds, source CRS, and vertical CRS status.
   - Fail the pipeline if source CRS is not EPSG:2961 or if no ground classification is present.
   - Warn, but do not fail, when vertical CRS is absent. Mark the DEM as visualization-only.

2. Tile selection:
   - Use the Charlottetown municipal boundary transformed to EPSG:2961.
   - Select COPC files whose bounds intersect the boundary plus a 100 m buffer.
   - Write the selected file list into the summary JSON for provenance.

3. Ground filtering:
   - Read only classification `2` ground points.
   - Exclude withheld, synthetic, keypoint-only, overlap, noise classification `7`, and high-noise classification `18` points where present.
   - Preserve source Z values exactly; do not apply vertical transformation in v1.

4. Raster interpolation:
   - Use PDAL `writers.gdal` with 1 m resolution in EPSG:2961.
   - Use inverse-distance interpolation as the v1 default.
   - Emit Float32 GeoTIFF with explicit NoData.
   - Clip final raster to the municipal boundary plus 100 m buffer using GDAL.

5. Fill and smoothing:
   - Do not smooth the v1 DEM by default.
   - Fill only small NoData holes after QA identifies them, and record the fill method in summary JSON.
   - Keep a future option for a separate hydro-flattened DEM; do not silently modify shoreline or water surfaces in v1.

6. Derivative products:
   - Generate hillshade for visual QA.
   - Generate summary JSON with raster extent, pixel size, min/max, NoData count, selected tile count, tool versions, and vertical-datum warning.

## Recommended Commands

Use a generated PDAL pipeline JSON rather than a long shell command once implementation begins. The core PDAL shape should be:

```json
[
  "maps/pei/lidar/selected-tile.copc.laz",
  {
    "type": "filters.range",
    "limits": "Classification[2:2]"
  },
  {
    "type": "writers.gdal",
    "filename": "data/spatial/charlottetown/lidar-terrain-dem/charlottetown-dem-epsg2961-1m-raw.tif",
    "resolution": 1.0,
    "output_type": "idw",
    "gdaldriver": "GTiff",
    "nodata": -9999
  }
]
```

Implementation should generate one pipeline that contains all selected COPC inputs or process tiles into intermediate rasters and mosaic them with GDAL if memory pressure appears. Use tile-by-tile intermediates if the full selected set exceeds available memory.

Post-processing should use GDAL:

```powershell
gdalwarp -t_srs EPSG:2961 -cutline maps/pei/CHTWN_Municipal_Boundary.geojson -crop_to_cutline -dstnodata -9999 raw.tif clipped.tif
gdaldem hillshade clipped.tif hillshade.tif
gdalinfo -stats clipped.tif
```

The implementation should replace placeholder filenames with the output paths listed in this page.

## QA and Acceptance Checks

Required checks:

- `gdalinfo` reports EPSG:2961, metre units, 1 m pixels, Float32 band type, and expected NoData.
- DEM bounds cover the Charlottetown municipal boundary plus the chosen buffer.
- DEM min, max, p50, and p95 are plausible against the observed LIDAR Z range and existing parcel metric summary.
- NoData ratio is reported and inspected; unexpected holes in developed areas block acceptance.
- Hillshade visually aligns with roads, parcels, and known shoreline areas in QGIS.
- A sample of parcels compares DEM ground values against existing `terrain_ground_p50_m` parcel metrics with residuals reported.

Acceptance threshold for v1:

- At least 99% of land area inside the municipal boundary has valid DEM cells unless NoData is explained by water, source coverage gaps, or classification gaps.
- Median absolute residual between sampled DEM values and existing parcel ground median metrics is under 0.75 m for parcels with high or medium LIDAR metric confidence.
- Output summary JSON records that vertical datum is unresolved and that the DEM is visualization-only until confirmed.

## Demo Acceptance Decision

For the first parcel-3D and storm-surge feature demos, the current DEM can proceed as a demo-only terrain surface even though it does not meet the earlier 99% land-coverage target.

The latest refined QA pass reported:

- refined land coverage: 97.4905%
- excluded water or shoreline artifact parcels: 71
- excluded wetland or water cells: 662,418
- median absolute parcel residual: 0.1019 m
- p95 absolute parcel residual: 0.6068 m

This is acceptable for feature demonstration because the residual checks pass and the remaining coverage gap can be handled with flat-terrain or no-data fallback behavior in the viewer. Do not present the output as authoritative terrain, flood, tidal, storm-surge, engineering, regulatory, or property-specific risk data.

Backlog item: revisit interpolation, masking, and hydro-flattening if the demo visuals are not satisfactory. Raising refined land coverage to at least 99% is deferred future work, not a blocker for the current demo.

## Integration Path

After the DEM passes QA, derive parcel-3D terrain patches from the EPSG:2961 DEM rather than from raw COPC files. The API should clip or sample around `/api/parcels/:pid/3d-context` parcel contexts and send compact mesh-ready elevation arrays to the browser.

Do not use this v1 DEM for storm surge or tidal modeling until the LIDAR vertical datum is resolved and a transformation path to bathymetry ChartDatum is documented.

## Sources

- [PEI LIDAR and bathymetry metadata](../sources/pei-lidar-bathymetry-metadata.md)
- [Parcel 3D LIDAR terrain plan](./parcel-3d-lidar-terrain-plan.md)
- [PEI LIDAR source directory](../../maps/pei/lidar)
- [Charlottetown municipal boundary](../../maps/pei/CHTWN_Municipal_Boundary.geojson)
- [Building LIDAR height script](../../scripts/build-charlottetown-lidar-buildings.py)
- [Parcel LIDAR metric script](../../scripts/build-charlottetown-parcel-lidar-metrics.py)
