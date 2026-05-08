from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path

import fitz
import numpy as np
import psycopg
import rasterio
from affine import Affine
from PIL import Image
from pyproj import CRS, Transformer


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "docs" / "charlottetown" / "ocp" / "Future Land Use Map - October 24 2025.pdf"
OUT_DIR = ROOT / "data" / "spatial" / "charlottetown"
OUT_TIF = OUT_DIR / "charlottetown-future-land-use-map-2025-10-24-raster.tif"
OUT_PNG = ROOT / "tmp" / "charlottetown_future_land_use_pdf" / "future_land_use_map_viewport.png"

TABLE_NAME = "CHTWN_Future_Land_Use_Map_Raster"
VIEWPORT_BBOX_POINTS = (36.0, 36.0, 3420.0, 2556.0)
RENDER_DPI = 150

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

# PDF /VP /Measure /GPTS order for the main viewport is SW, NW, NE, SE.
GPTS_LAT_LON = [
    (46.22657, -63.23491),
    (46.30655, -63.23526),
    (46.30676, -63.08028),
    (46.22679, -63.08017),
]


def database_url() -> str:
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "54329")
    database = os.environ.get("PGDATABASE", "mdopendata")
    user = os.environ.get("PGUSER", "mdopendata")
    password = os.environ.get("PGPASSWORD", "mdopendata_dev")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def projected_control_points() -> tuple[tuple[float, float], ...]:
    crs = CRS.from_wkt(CRS_WKT)
    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    sw, nw, ne, se = [
        transformer.transform(lon, lat)
        for lat, lon in GPTS_LAT_LON
    ]
    return nw, ne, se, sw


def viewport_transform(width: int, height: int) -> Affine:
    nw, ne, _se, sw = projected_control_points()
    a = (ne[0] - nw[0]) / width
    d = (ne[1] - nw[1]) / width
    b = (sw[0] - nw[0]) / height
    e = (sw[1] - nw[1]) / height
    return Affine(a, b, nw[0], d, e, nw[1])


def render_viewport() -> Image.Image:
    doc = fitz.open(PDF_PATH)
    page = doc[0]
    scale = RENDER_DPI / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    page_height = float(page.rect.height)
    left, bottom, right, top = VIEWPORT_BBOX_POINTS
    crop = (
        round(left * scale),
        round((page_height - top) * scale),
        round(right * scale),
        round((page_height - bottom) * scale),
    )
    return image.crop(crop)


def write_geotiff() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    viewport = render_viewport()
    viewport.save(OUT_PNG)
    arr = np.asarray(viewport.convert("RGB"), dtype=np.uint8)
    height, width, bands = arr.shape
    if bands != 3:
        raise RuntimeError(f"Expected RGB viewport, got {bands} bands.")

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 3,
        "dtype": "uint8",
        "crs": CRS.from_wkt(CRS_WKT),
        "transform": viewport_transform(width, height),
        "photometric": "RGB",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "predictor": 2,
    }
    with rasterio.open(OUT_TIF, "w", **profile) as dst:
        dst.write(np.moveaxis(arr, 2, 0))
        dst.update_tags(
            source_pdf=str(PDF_PATH.relative_to(ROOT)).replace("\\", "/"),
            source_png=str(OUT_PNG.relative_to(ROOT)).replace("\\", "/"),
            source_viewport_bbox_points="36,36,3420,2556",
            source_gpts_order="SW,NW,NE,SE",
            method="PDF main geospatial viewport rendered at 150 DPI and written as georeferenced RGB GeoTIFF.",
        )


def load_to_postgis() -> None:
    with OUT_TIF.open("rb") as fh:
        raster_bytes = fh.read()

    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis_raster")
            cur.execute("SET postgis.gdal_enabled_drivers = 'ENABLE_ALL'")
            cur.execute(f'DROP TABLE IF EXISTS public."{TABLE_NAME}"')
            cur.execute(
                f'''
                CREATE TABLE public."{TABLE_NAME}" (
                  rid integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                  rast raster NOT NULL,
                  source_path text NOT NULL,
                  source_pdf text NOT NULL,
                  source_viewport_bbox_points text NOT NULL,
                  source_gpts_lat_lon jsonb NOT NULL,
                  render_dpi integer NOT NULL,
                  loaded_at timestamptz NOT NULL DEFAULT now()
                )
                '''
            )
            cur.execute(
                f'''
                INSERT INTO public."{TABLE_NAME}" (
                  rast, source_path, source_pdf, source_viewport_bbox_points,
                  source_gpts_lat_lon, render_dpi
                )
                VALUES (
                  ST_SetSRID(ST_FromGDALRaster(%s), 2954),
                  %s,
                  %s,
                  %s,
                  %s::jsonb,
                  %s
                )
                ''',
                (
                    psycopg.Binary(raster_bytes),
                    str(OUT_TIF.relative_to(ROOT)).replace("\\", "/"),
                    str(PDF_PATH.relative_to(ROOT)).replace("\\", "/"),
                    "36,36,3420,2556",
                    psycopg.types.json.Json(GPTS_LAT_LON),
                    RENDER_DPI,
                ),
            )
            cur.execute(f'CREATE INDEX "{TABLE_NAME}_rast_gist" ON public."{TABLE_NAME}" USING gist (ST_ConvexHull(rast))')
        conn.commit()


def main() -> None:
    write_geotiff()
    load_to_postgis()
    with rasterio.open(OUT_TIF) as src:
        print(f"wrote {OUT_TIF}")
        print(f"loaded public.\"{TABLE_NAME}\"")
        print(f"size {src.width}x{src.height}")
        print(f"bands {src.count}")
        print(f"crs {src.crs}")
        print(f"bounds {src.bounds}")


if __name__ == "__main__":
    main()
