from __future__ import annotations

from pathlib import Path
import importlib.util

import numpy as np
import rasterio
from rasterio.transform import from_bounds


ROOT = Path(__file__).resolve().parents[1]
POLYGONIZE_SCRIPT = ROOT / "scripts" / "polygonize-charlottetown-zoning-map.py"
OUT_DIR = ROOT / "data" / "spatial" / "charlottetown"
OUT_GPKG = OUT_DIR / "charlottetown-zoning-map-2026-raster.gpkg"
OUT_PNG = ROOT / "tmp" / "charlottetown_zoning_pdf" / "zoning_map_raster_source.png"
LAYER_NAME = "charlottetown_zoning_map_2026_raster"

CRS_WKT = (
    'PROJCS["NAD_1983_CSRS_Prince_Edward_Island",'
    'GEOGCS["GCS_North_American_1983_CSRS",'
    'DATUM["D_North_American_1983_CSRS",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Double_Stereographic"],'
    'PARAMETER["False_Easting",400000.0],'
    'PARAMETER["False_Northing",800000.0],'
    'PARAMETER["Central_Meridian",-63.0],'
    'PARAMETER["Scale_Factor",0.999912],'
    'PARAMETER["Latitude_Of_Origin",47.25],UNIT["Meter",1.0]]'
)

spec = importlib.util.spec_from_file_location("polygonize_charlottetown_zoning_map", POLYGONIZE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load {POLYGONIZE_SCRIPT}")
polygonize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(polygonize)

BL = polygonize.BL
TL = polygonize.TL
TR = polygonize.TR
VIEWPORT_CROP = polygonize.VIEWPORT_CROP
extract_mosaic = polygonize.extract_mosaic


def viewport_transform(width: int, height: int):
    west = min(float(TL[0]), float(BL[0]))
    east = float(TR[0])
    north = max(float(TL[1]), float(TR[1]))
    south = float(BL[1])
    return from_bounds(west, south, east, north, width, height)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    mosaic = extract_mosaic()
    viewport = mosaic.crop(VIEWPORT_CROP).convert("RGB")
    viewport.save(OUT_PNG)

    arr = np.asarray(viewport, dtype=np.uint8)
    height, width, bands = arr.shape
    if bands != 3:
        raise RuntimeError(f"Expected RGB image, got {bands} bands.")

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()

    profile = {
        "driver": "GPKG",
        "raster_table": LAYER_NAME,
        "height": height,
        "width": width,
        "count": 3,
        "dtype": "uint8",
        "crs": CRS_WKT,
        "transform": viewport_transform(width, height),
        "photometric": "RGB",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }

    with rasterio.open(OUT_GPKG, "w", **profile) as dst:
        dst.write(np.moveaxis(arr, 2, 0))
        dst.update_tags(
            source_pdf="maps/Charlottetown Zoning Map - March 9, 2026.pdf",
            source_png=str(OUT_PNG.relative_to(ROOT)).replace("\\", "/"),
            method="PDF embedded image tiles extracted and written as a georeferenced raster GeoPackage.",
        )

    print(f"wrote {OUT_GPKG}")
    print(f"layer {LAYER_NAME}")
    print(f"source_png {OUT_PNG}")
    print(f"size {width}x{height}")
    print(f"crs EPSG:2954 equivalent")


if __name__ == "__main__":
    main()
