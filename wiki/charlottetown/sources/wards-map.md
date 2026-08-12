---
type: source
tags:
  - charlottetown
  - electoral-wards
  - polling-divisions
  - gis
updated: 2026-08-06
---

This page records the vector extraction and PostGIS registration of the Charlottetown ward map PDF.

## Source

`maps/Chtown_All_Wards.pdf` is a one-page Esri ArcMap 10.2.2.3552 PDF created on 2018-02-05. The GDAL PDF driver exposes the `Map_Information_Tool_Specific_Calculation_Edit_ElectoralDistricts` layer in a NAD83(CSRS) UTM 20N coordinate system (`EPSG:2961`). The page contains 69 printed district-area labels from `1-1` through `10-7`.

The first component of a printed code is retained as `ward_code`; the second component is retained as `polling_division_number`. Electoral ward 2 has six polling divisions, and each of electoral wards 1 and 3 through 10 has seven polling divisions.

## Generated spatial outputs

`scripts/extract-charlottetown-wards.py` reads the vector PDF through the system GDAL PDF driver, matches printed labels to the filled source polygons using the PDF text positions and fill colors, transforms to `EPSG:2954`, and clips to `maps/pei/CHTWN_Municipal_Boundary.geojson`.

The base GeoPackage `data/spatial/charlottetown/charlottetown-wards-municipal-fit.gpkg` contains separate layers:

- `polling_divisions_municipal_fit`: 69 `MULTIPOLYGON` features keyed by `polling_division_code`, with `ward_code`, `polling_division_number`, source feature FID, fill color, and label-match distance.
- `electoral_wards_municipal_fit`: 10 dissolved `MULTIPOLYGON` features keyed by `ward_code`, retaining `polling_division_count` and source fill color.
- `municipal_boundary_reference`: the official Charlottetown boundary used for clipping and QA.

The extracted polling divisions and electoral wards are valid and non-empty. The source map coverage is smaller than the full municipal polygon because the printed ward map does not assign every municipal water or cartographic residual area to an electoral ward. The source summary records the measured union-versus-boundary difference.

The district output applies a topology cleanup after dissolve. Interior rings below 1,000 m2 are treated as source-vector slivers and removed without generalizing exterior boundaries. Two larger map-derived holes are retained: district 2 (approximately 86,122 m2) and district 5 (approximately 6,457 m2). The final artifact `data/spatial/charlottetown/charlottetown-wards-municipal-fit-topology-corrected.gpkg` uses a global polygonized coverage partition: every source overlap is assigned to one area, gap faces inside the cleaned ward domain are assigned to one adjacent area, and districts are regenerated as exact unions of their corrected areas.

## PostGIS registration

Migration `schema/sql/036_charlottetown_wards.sql` registers and loads:

- `public."CHTWN_Polling_Divisions"` and `zoning.v_charlottetown_polling_divisions` for the 69 printed polling divisions.
- `public."CHTWN_Electoral_Wards"` and `zoning.v_charlottetown_electoral_wards` for the 10 dissolved electoral wards.

The normalized `zoning.spatial_layer` contracts are `charlottetown_polling_divisions` and `charlottetown_electoral_wards`. Both are loaded with SRID 2954 and zero invalid geometries.

Migration `schema/sql/037_charlottetown_wards_topology_cleanup.sql` records the prior electoral-ward hole cleanup. Migration `schema/sql/038_charlottetown_wards_global_coverage.sql` reloads both public layers from the final artifact. Migration `schema/sql/039_charlottetown_ward_terminology.sql` applies the canonical terminology. The public source tables are `public."CHTWN_Polling_Divisions"` and `public."CHTWN_Electoral_Wards"`; the GIS-facing views are `zoning.v_charlottetown_polling_divisions` and `zoning.v_charlottetown_electoral_wards`.

## QA limits

The corrected output has 69 valid polling divisions with zero pairwise overlaps above 0.01 m2, zero area outside the owning electoral ward, zero ward-union difference, and electoral-ward area-sum residual below 0.00001 m2. Only the two retained water holes remain. Label-to-polygon assignments retain `label_match_distance_m`; five labels exceed 5 metres, with a maximum recorded distance of approximately 68 metres. This is an extraction-audit field, not a claim that the printed labels define surveyed boundary coordinates.

## Sources

- [Charlottetown wiki index](../index.md)
- `maps/Chtown_All_Wards.pdf`
- `maps/pei/CHTWN_Municipal_Boundary.geojson`
- `scripts/extract-charlottetown-wards.py`
- `data/spatial/charlottetown/charlottetown-wards-municipal-fit.gpkg`
- `data/spatial/charlottetown/charlottetown-wards-municipal-fit.summary.json`
- `data/spatial/charlottetown/charlottetown-wards-municipal-fit-clean.gpkg`
- `data/spatial/charlottetown/charlottetown-wards-municipal-fit-clean.summary.json`
- `data/spatial/charlottetown/charlottetown-wards-municipal-fit-topology-corrected.gpkg`
- `data/spatial/charlottetown/charlottetown-wards-municipal-fit-topology-corrected.summary.json`
- `schema/sql/036_charlottetown_wards.sql`
- `schema/sql/037_charlottetown_wards_topology_cleanup.sql`
- `schema/sql/038_charlottetown_wards_global_coverage.sql`
