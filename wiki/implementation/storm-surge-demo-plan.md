---
type: implementation
tags:
  - web-ui
  - storm-surge
  - tidal
  - lidar
  - bathymetry
  - charlottetown
updated: 2026-05-08
---

This page records the initial demo-only Charlottetown tidal and storm-surge visualization added to the web UI.

# Storm Surge Demo Plan

## Scope

The first implementation is a non-authoritative demo page at `/storm-surge`.

It reuses `/api/parcels/:pid/3d-context`, the current parcel terrain patch, parcel boundaries, roads, and buildings. It does not create a hydrodynamic model, inundation connectivity model, wave model, drainage model, or regulatory flood map.

The page renders a transparent static water plane against the existing parcel 3D terrain and building context. It is intended to show future potential and scenario composition, not property-specific risk.

## Scenario Controls

The demo exposes:

- Tide presets for full/new moon high tide, full/new moon low tide, half moon high tide, and half moon low tide.
- Storm surge from 0 to 10 m.
- Sea-level-rise horizon from now through 100 years.
- Sea-level-rise scenario options of 0.5 m, 1.0 m, and 1.5 m by 100 years.

The water level is computed as:

```text
tide level above chart datum + storm surge + sea-level-rise increment
```

The rendered water plane then applies a visual datum offset and subtracts the terrain patch `baseElevationM`, because the API normalizes terrain values by subtracting the patch median elevation before sending them to the browser. The default visual datum offset is `-1.8 m`, with a slider range from `-2.8 m` to `-0.8 m`, using the CHS Charlottetown station 01700 CGVD28 offset as a starting point for demo calibration. This is still not a confirmed vertical datum transformation for the LIDAR DEM.

The storm-surge page requests a 350 m parcel context radius. This is the current API terrain-patch cap and gives about 1.96 times the area of the parcel 3D default 250 m radius. DEM NoData cells in the terrain patch render as a lowered water bed at `-14 m`.

## Source Assumptions

Charlottetown tide presets use Canadian Hydrographic Service station 01700 where available. The source reports tide heights relative to chart datum, including Higher High Water Large Tide at 2.97 m and Lower Low Water Large Tide at 0.09 m. The station page also lists a CGVD28 datum conversion offset of `-1.72 m`, which the demo uses as the default visual offset for rendering.

The 1.0 m by 100 years sea-level-rise option follows PEI public guidance that PEI should be prepared for 1 m of sea-level rise by 2100 above 2006 levels. The 0.5 m and 1.5 m options are demo sensitivity controls.

## Data Limitations

The current LIDAR terrain DEM is demo-only. Its vertical datum remains unresolved.

The bathymetry source files under `maps/pei/bathymetry` include NONNA BAG files with ChartDatum vertical metadata. They are not yet combined with the LIDAR terrain because the datum transformation path is unresolved.

Because the water plane is chart-datum-based while terrain vertical datum is unresolved, the page must continue to label outputs as visualization-only. Do not describe the result as authoritative flooding, tidal, storm-surge, engineering, regulatory, emergency-management, or property-specific risk data.

## Future Upgrade Path

Authoritative modeling would require:

- Confirming the LIDAR vertical datum.
- Defining the transformation between LIDAR terrain elevations and bathymetry ChartDatum.
- Building a shoreline-aware terrain and bathymetry surface.
- Adding inundation connectivity rather than pure elevation comparison.
- Adding event definitions from accepted municipal, provincial, federal, or engineering sources.
- Validating against observed water levels, known flood extents, or a reviewed hydrodynamic model.

## Sources

- [PEI LIDAR and bathymetry metadata](../sources/pei-lidar-bathymetry-metadata.md)
- [Charlottetown terrain DEM pipeline](./charlottetown-terrain-dem-pipeline.md)
- [Parcel 3D LIDAR terrain plan](./parcel-3d-lidar-terrain-plan.md)
- [Storm surge UI](../../web/public/ui_kits/storm-surge/index.html)
- [Web server](../../web/server.js)
