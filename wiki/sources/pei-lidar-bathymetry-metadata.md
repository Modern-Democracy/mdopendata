---
type: source
tags:
  - pei
  - lidar
  - bathymetry
  - metadata
  - gis
  - charlottetown
updated: 2026-05-08
---

This page summarizes observed metadata from local PDAL and GDAL inspection of PEI LIDAR and Charlottetown harbour bathymetry source files.

# PEI LIDAR and Bathymetry Metadata

## Tooling

PDAL and GDAL are available through local Windows installs after path configuration:

| Tool | Version | Source |
| --- | --- | --- |
| PDAL | 2.10.0 | `C:\Program Files\QGIS 4.0.1\bin\pdal.exe` |
| GDAL | 3.12.1 | `C:\Program Files\GDAL\gdalinfo.exe` |

The user-level environment was configured with `C:\Program Files\GDAL` before `C:\Program Files\QGIS 4.0.1\bin`, plus `GDAL_DRIVER_PATH`, `GDAL_DATA`, and `PROJ_LIB` pointing at the GISInternals GDAL install. This ordering allows `gdalinfo` to read BAG bathymetry while keeping `pdal` available from QGIS.

## LIDAR Source

The LIDAR source directory contains 69 COPC LAZ files under `maps/pei/lidar`.

Observed aggregate metadata from `pdal info --summary` over all COPC files:

| Property | Value |
| --- | --- |
| File count | 69 |
| Point count | 571,585,193 |
| Reader | `readers.copc` |
| Horizontal CRS | NAD83(CSRS) / UTM zone 20N |
| EPSG | 2961 |
| Horizontal unit | metre |
| UTM extent | X 484006.1311 to 494002.3082; Y 5118984.87 to 5128981.024 |
| Approximate WGS84 extent | -63.207390, 46.224262 to -63.077897, 46.314388 |
| Z range | -86.804 to 84.648 |
| Vertical CRS | Not declared in PDAL metadata |

Representative sample file: `maps/pei/lidar/pei_2020_386000_690000.copc.laz`.

| Property | Value |
| --- | --- |
| File size | 50,451,039 bytes |
| Point count | 8,629,475 |
| Bounds | X 486005.3849 to 487005.0139; Y 5122983.231 to 5123982.861; Z -1.398 to 71.24 |
| Dimensions | X, Y, Z, Intensity, ReturnNumber, NumberOfReturns, Classification, GPS time, and related LAS flags |
| Classification stats | Classification values range from 1 to 18 in the sampled tile |

The LIDAR horizontal reference is usable for Charlottetown terrain processing after reprojection as needed. The vertical reference remains unresolved and must be confirmed before terrain, building height, flood, tidal, or storm-surge products are accepted.

## Bathymetry Source

The bathymetry source directory contains NONNA BAG, GeoTIFF, text, CSAR, and related files under `maps/pei/bathymetry`.

### BAG Files

Representative BAG file: `maps/pei/bathymetry/NONNA10_4610N06320W.bag`.

| Property | Value |
| --- | --- |
| Driver | BAG/Bathymetry Attributed Grid |
| Size | 1001 x 1001 |
| CRS | WGS 84 + ChartDatum |
| Vertical CRS | ChartDatum |
| Vertical axis | depth down |
| Vertical unit | metre |
| Pixel size | 0.0001 degrees |
| Bounds | -63.200050, 46.200050 to -63.099950, 46.099950 |
| Band 1 | elevation |
| Band 1 range | -46.490 to 3.890 |
| Band 2 | uncertainty |
| NoData | 1e+06 |
| Warning | `cornerPoints not consistent with resolution given in metadata` |

Other inspected NONNA10 BAG tiles:

| File | Bounds | Elevation range |
| --- | --- | --- |
| `NONNA10_4610N06330W.bag` | -63.300050, 46.200050 to -63.199950, 46.099950 | -16.469 to 3.890 |
| `NONNA10_4620N06320W.bag` | -63.200050, 46.300050 to -63.099950, 46.199950 | -26.132 to 3.890 |
| `NONNA10_4620N06330W.bag` | -63.300050, 46.300050 to -63.199950, 46.199950 | -1.360 to 3.890 |

All inspected BAG files report WGS 84 plus ChartDatum and carry an uncertainty band. The ChartDatum reference does not directly match the unresolved LIDAR vertical reference.

### GeoTIFF Files

The NONNA GeoTIFF bathymetry files are WGS84 rasters with a depth band in metres.

| File | Pixel size | Bounds | Range |
| --- | --- | --- | --- |
| `NONNA100_4600N06400W.tiff` | 0.001 degrees | -64.000500, 47.000500 to -62.999500, 45.999500 | -63.208 to 4.435 |
| `NONNA10_4610N06320W.tiff` | 0.0001 degrees | -63.200050, 46.200050 to -63.099950, 46.099950 | -46.490 to 3.890 |
| `NONNA10_4610N06330W.tiff` | 0.0001 degrees | -63.300050, 46.200050 to -63.199950, 46.099950 | -16.469 to 3.890 |
| `NONNA10_4620N06310W.tiff` | 0.0001 degrees | -63.100050, 46.300050 to -62.999950, 46.199950 | -18.740 to 3.990 |
| `NONNA10_4620N06320W.tiff` | 0.0001 degrees | -63.200050, 46.300050 to -63.099950, 46.199950 | -26.132 to 3.890 |
| `NONNA10_4620N06330W.tiff` | 0.0001 degrees | -63.300050, 46.300050 to -63.199950, 46.199950 | -1.360 to 3.890 |

The GeoTIFFs expose depth units but do not carry the same explicit compound vertical CRS observed in the BAG files.

### Backscatter Intensity

`maps/pei/bathymetry/1001690_Intensity.tiff` is an intensity/backscatter raster, not a bathymetric depth grid.

| Property | Value |
| --- | --- |
| Pixel size | 10 m |
| Bounds | 472625, 5120485 to 497935, 5085265 |
| Displayed WGS84 extent | about -63.355, 46.237 to -63.027, 45.921 |
| Band | Intensity |
| Unit | dB |
| Range | -128.160 to -40.548 |

`maps/pei/bathymetry/1001690_Intensity.gpkg` contains a `source_bck` layer with 3 features and WGS84 extent -63.348500, 45.928000 to -63.041600, 46.234000.

## Interpretation

The LIDAR data is horizontally suitable for Charlottetown terrain and parcel 3D preprocessing because it is in EPSG:2961, uses metres, and covers the city area. It is not yet vertically suitable for authoritative elevation products because PDAL did not report a vertical CRS.

The BAG bathymetry data is horizontally WGS84 and vertically ChartDatum in metres. It is suitable as a bathymetry source, but not directly combinable with LIDAR terrain until both datasets are transformed or normalized to a documented common vertical reference.

The NONNA GeoTIFFs are useful for raster processing and quick inspection, but BAG files are preferable as source-of-record bathymetry where uncertainty and vertical CRS metadata are needed.

The backscatter intensity products should not be used as depth rasters for tidal or storm-surge modeling.

## Open Checks

- Confirm the LIDAR vertical datum from source documentation or provider metadata.
- Confirm whether the LIDAR Z values are orthometric heights and whether they use CGVD2013, CGVD28, ellipsoidal height, or another reference.
- Define the vertical transformation path between LIDAR terrain and ChartDatum bathymetry before any storm-surge or inundation modeling.
- Investigate the BAG `cornerPoints not consistent with resolution given in metadata` warning before mosaicking or clipping BAG tiles.

## Sources

- [PEI LIDAR source directory](../../maps/pei/lidar)
- [PEI bathymetry source directory](../../maps/pei/bathymetry)
- [Parcel 3D LIDAR terrain plan](../implementation/parcel-3d-lidar-terrain-plan.md)
- [Root wiki index](../index.md)
