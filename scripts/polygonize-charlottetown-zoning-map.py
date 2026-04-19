from __future__ import annotations

from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio
from PIL import Image
from pypdf import PdfReader
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "maps" / "Charlottetown Zoning Map - March 9, 2026.pdf"
WORK_DIR = ROOT / "tmp" / "charlottetown_zoning_pdf"
OUT_DIR = ROOT / "data" / "spatial" / "charlottetown"
OUT_GPKG = OUT_DIR / "charlottetown-zoning-map-2026-draft.gpkg"

VIEWPORT_CROP = (75, 75, 7125, 5325)
MAIN_ROI = (1500, 0, 7050, 5100)
DOWNSAMPLE = 8
MIN_AREA_M2 = 700
SIMPLIFY_M = 4

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

ZONE_CLASSES = [
    ("C1", "Business Office Commercial", (255, 51, 154), 75, "solid"),
    ("C2", "Highway Commercial", (205, 121, 51), 75, "solid"),
    ("C3", "Shopping Centre Commercial", (255, 119, 51), 75, "solid"),
    ("CDA", "Comprehensive Development Area", (192, 194, 218), 50, "hatched"),
    ("DC", "Downtown Core", (214, 88, 91), 75, "solid"),
    ("DMS", "Downtown Main Street", (185, 134, 133), 65, "solid"),
    ("DMUN", "Downtown Mixed-Use Neighbourhood", (162, 161, 105), 60, "solid"),
    ("DN", "Downtown Neighbourhood", (222, 169, 185), 65, "solid"),
    ("I/P", "Institutional or Parking; same legend fill color", (143, 193, 254), 70, "solid"),
    ("M1", "Light Industrial", (214, 214, 214), 28, "solid"),
    ("M2", "Heavy Industrial", (134, 134, 134), 45, "solid"),
    ("M3", "Business Park Industrial", (210, 159, 192), 65, "solid"),
    ("DMU/MHR", "Downtown Mixed-Use or Manufactured Housing Residential; similar hatch color", (190, 140, 135), 60, "hatched"),
    ("MUC", "Mixed-Use Corridor", (255, 187, 52), 75, "solid"),
    ("MUR", "Mixed-Use Residential", (235, 173, 52), 70, "solid"),
    ("ERMUVC", "East Royalty Mixed-Use Village Centre", (185, 51, 50), 70, "solid"),
    ("NA", "Zoning Not Assigned", (208, 51, 254), 75, "solid"),
    ("OS", "Open Space", (111, 235, 51), 75, "solid"),
    ("PC", "Park/Culture", (131, 171, 136), 60, "solid"),
    ("PZ", "Port Zone", (190, 79, 238), 70, "hatched"),
    ("R1L", "Single Detached Residential (Large)", (255, 255, 143), 70, "solid"),
    ("R1N", "Single Detached Residential (Narrow)", (253, 219, 235), 35, "solid"),
    ("R1S", "Single Detached Residential (Small)", (221, 255, 161), 65, "solid"),
    ("R2", "Low Density Residential", (240, 208, 125), 65, "solid"),
    ("R3", "Medium Density Residential", (185, 185, 51), 65, "solid"),
    ("R3T", "Medium Density Residential Townhouse", (142, 81, 52), 60, "solid"),
    ("R4A", "Apartment Residential A", (185, 141, 52), 60, "solid"),
    ("R4B", "Apartment Residential B", (93, 93, 93), 55, "solid"),
    ("WF", "Waterfront", (250, 191, 74), 70, "hatched"),
    ("WLC", "Water Lot Commercial", (204, 237, 255), 60, "solid"),
    ("WLOS", "Water Lot Open Space", (51, 114, 185), 70, "solid"),
]


def extract_mosaic() -> Image.Image:
    reader = PdfReader(str(PDF_PATH))
    page = reader.pages[0]
    form = page["/Resources"]["/XObject"]["/Group_6"].get_object()
    xobjects = form["/Resources"]["/XObject"]
    placements = {
        "/Image_11": (0, 0),
        "/Image_15": (4096, 0),
        "/Image_17": (0, 4096),
        "/Image_19": (4096, 4096),
    }
    canvas = Image.new("RGB", (7200, 5400), "white")
    for name, xy in placements.items():
        image = Image.open(BytesIO(xobjects[name].get_object().get_data())).convert("RGB")
        canvas.paste(image, xy)
    return canvas


def projected_corners() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    crs = CRS.from_wkt(CRS_WKT)
    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    # GPTS order in the PDF for the main viewport is SW, NW, NE, SE.
    sw = transformer.transform(-63.2345, 46.2266)
    nw = transformer.transform(-63.2349, 46.3066)
    ne = transformer.transform(-63.0799, 46.3068)
    se = transformer.transform(-63.0798, 46.2268)
    return tuple(np.array(p, dtype=float) for p in (nw, ne, se, sw))


TL, TR, BR, BL = projected_corners()


def pixel_to_xy(x: float, y: float) -> tuple[float, float]:
    xf = x / (VIEWPORT_CROP[2] - VIEWPORT_CROP[0])
    yf = y / (VIEWPORT_CROP[3] - VIEWPORT_CROP[1])
    pt = TL * (1 - xf) * (1 - yf) + TR * xf * (1 - yf) + BR * xf * yf + BL * (1 - xf) * yf
    return float(pt[0]), float(pt[1])


def classify(img: Image.Image) -> tuple[np.ndarray, Counter]:
    roi = img.crop(MAIN_ROI)
    small_size = (roi.width // DOWNSAMPLE, roi.height // DOWNSAMPLE)
    small = roi.resize(small_size, Image.Resampling.BOX).convert("RGB")
    small.save(WORK_DIR / "classification_input_downsampled.png")
    arr = np.asarray(small, dtype=np.int32)
    colors = np.array([item[2] for item in ZONE_CLASSES], dtype=np.int32)
    thresholds = np.array([item[3] for item in ZONE_CLASSES], dtype=float)
    dist = np.sqrt(((arr[:, :, None, :] - colors[None, None, :, :]) ** 2).sum(axis=3))
    nearest = dist.argmin(axis=2)
    nearest_dist = dist.min(axis=2)
    classes = np.where(nearest_dist <= thresholds[nearest], nearest + 1, 0).astype(np.uint8)

    yy, xx = np.indices(classes.shape)
    global_x = MAIN_ROI[0] + xx * DOWNSAMPLE
    global_y = MAIN_ROI[1] + yy * DOWNSAMPLE
    title_and_scale_area = (global_x < 3350) & (global_y > 3850)
    downtown_inset_area = (global_x < 2250) & (global_y > 2900)
    classes[title_and_scale_area | downtown_inset_area] = 0
    return classes, Counter(classes.ravel().tolist())


def run_polygons(mask: np.ndarray, class_id: int) -> list[Polygon]:
    polygons: list[Polygon] = []
    height, width = mask.shape
    for row in range(height):
        col = 0
        while col < width:
            while col < width and mask[row, col] != class_id:
                col += 1
            start = col
            while col < width and mask[row, col] == class_id:
                col += 1
            if start == col:
                continue
            x0 = MAIN_ROI[0] + start * DOWNSAMPLE
            x1 = MAIN_ROI[0] + col * DOWNSAMPLE
            y0 = MAIN_ROI[1] + row * DOWNSAMPLE
            y1 = MAIN_ROI[1] + (row + 1) * DOWNSAMPLE
            polygons.append(
                Polygon(
                    [
                        pixel_to_xy(x0, y0),
                        pixel_to_xy(x1, y0),
                        pixel_to_xy(x1, y1),
                        pixel_to_xy(x0, y1),
                    ]
                )
            )
    return polygons


def write_preview(classes: np.ndarray) -> None:
    palette = np.zeros((len(ZONE_CLASSES) + 1, 3), dtype=np.uint8)
    palette[0] = (255, 255, 255)
    for idx, item in enumerate(ZONE_CLASSES, start=1):
        palette[idx] = item[2]
    image = Image.fromarray(palette[classes], mode="RGB")
    image.save(WORK_DIR / "classified_zones_downsampled.png")


def build_features(classes: np.ndarray) -> pd.DataFrame:
    rows = []
    counts = Counter(classes.ravel().tolist())
    for class_id, (code, name, color, threshold, style) in enumerate(ZONE_CLASSES, start=1):
        if counts[class_id] == 0:
            continue
        pieces = run_polygons(classes, class_id)
        if not pieces:
            continue
        geom = unary_union(pieces).buffer(0)
        if geom.is_empty:
            continue
        if SIMPLIFY_M:
            geom = geom.simplify(SIMPLIFY_M, preserve_topology=True).buffer(0)
        geoms = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        kept = [g for g in geoms if g.area >= MIN_AREA_M2]
        if not kept:
            continue
        merged = unary_union(kept).buffer(0)
        rows.append(
            {
                "zone_code": code,
                "zone_name": name,
                "legend_rgb": "#{:02x}{:02x}{:02x}".format(*color),
                "legend_style": style,
                "pixel_count": int(counts[class_id]),
                "area_m2": float(merged.area),
                "confidence": "low" if style == "hatched" else "medium",
                "source_pdf": str(PDF_PATH.relative_to(ROOT)).replace("\\", "/"),
                "method": "raster color segmentation from geospatial PDF; draft QA required",
                "geometry": merged,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mosaic = extract_mosaic()
    mosaic.save(WORK_DIR / "mosaic.png")
    viewport = mosaic.crop(VIEWPORT_CROP)
    viewport.save(WORK_DIR / "main_viewport_crop.png")
    classes, counts = classify(viewport)
    write_preview(classes)
    features = gpd.GeoDataFrame(build_features(classes), geometry="geometry", crs="EPSG:2954")
    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    pyogrio.write_dataframe(
        features,
        OUT_GPKG,
        layer="zoning_areas_draft",
        driver="GPKG",
        geometry_type="MultiPolygon",
        promote_to_multi=True,
    )
    summary = features.drop(columns=["geometry"]).sort_values("zone_code")
    summary.to_csv(WORK_DIR / "zoning_areas_draft_summary.csv", index=False)
    print(f"wrote {OUT_GPKG}")
    print(f"features {len(features)}")
    print(f"pixel classes {dict(sorted(counts.items()))}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
