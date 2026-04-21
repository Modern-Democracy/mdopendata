from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

import fitz
import geopandas as gpd
import pandas as pd
import pyogrio
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, shape
from shapely.ops import polygonize, unary_union


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "docs" / "charlottetown" / "charlottetown-zoning-bylaw-draft_2026-04-09.pdf"
OUT_DIR = ROOT / "data" / "spatial" / "charlottetown"
OUT_GPKG = OUT_DIR / "charlottetown-draft-map-layers-2026-04-09-municipal-fit.gpkg"
SUMMARY_PATH = OUT_DIR / "charlottetown-draft-map-layers-2026-04-09-municipal-fit.summary.json"

SCHEDULE_A_PAGE_INDEX = 196
SCHEDULE_C_PAGE_INDEX = 198
TARGET_CRS = "EPSG:2954"

# Bboxes of the municipal map envelopes in PDF drawing coordinates. Each
# schedule has its own page placement; fitting Schedule C with the Schedule A
# envelope produces a small north-shift in the internal linework.
SCHEDULE_A_MAP_FIT_BOUNDS = (126.04969787597656, 37.92487716674805, 841.349609375, 751.2247924804688)
SCHEDULE_C_TO_A_PDF_AFFINE = {
    "sx": 1.0,
    "sy": 1.0,
    "tx": 0.019,
    "ty": 1.235,
}

ZONE_LEGEND = [
    ("RN", "Neighbourhood", (251, 248, 191)),
    ("RM", "Medium Density Residential", (242, 220, 127)),
    ("RH", "High Order Residential", (236, 192, 0)),
    ("DC", "Downtown Core", (112, 15, 16)),
    ("DMS", "Downtown Main Street", (250, 118, 118)),
    ("DMU", "Downtown Mixed Use", (171, 30, 34)),
    ("DN", "Downtown Neighbourhood", (225, 79, 32)),
    ("DW", "Downtown Waterfront", (223, 93, 114)),
    ("BP", "Business Park", (182, 151, 197)),
    ("AP", "Airport Periphery", (226, 206, 236)),
    ("HI", "Heavy Industrial", (171, 70, 157)),
    ("P", "Port", (120, 80, 139)),
    ("GC", "Growth Corridor", (241, 180, 161)),
    ("GN", "Growth Node", (231, 116, 90)),
    ("I", "Institutional", (70, 140, 159)),
    ("PPS", "Parks and Public Spaces", (109, 165, 123)),
    ("POS", "Privately-owned Open Spaces", (138, 206, 145)),
    ("C", "Conservation", (73, 88, 39)),
    ("EG", "Eastern Gateway", (78, 78, 79)),
    ("UE", "Urban Expansion", (179, 179, 179)),
]

ZONE_BY_RGB = {rgb: (code, name) for code, name, rgb in ZONE_LEGEND}
ZONE_RGBS = set(ZONE_BY_RGB)
WETLAND_RGB = (225, 225, 225)


def fetch_municipal_boundary() -> gpd.GeoDataFrame:
    sql = """
select st_asgeojson(geom, 9)
from public."PEI_Municipal_Zones"
where "MUNICIPAL1" = 'City of Charlottetown';
"""
    proc = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "mdopendata-postgis",
            "psql",
            "-U",
            "mdopendata",
            "-d",
            "mdopendata",
            "-t",
            "-A",
        ],
        input=sql,
        text=True,
        capture_output=True,
        check=True,
    )
    text = proc.stdout.strip()
    if not text:
        raise RuntimeError("City of Charlottetown boundary was not returned from PEI_Municipal_Zones.")
    boundary = gpd.GeoDataFrame(
        [{"source_layer": "PEI_Municipal_Zones", "municipal_attribute": "MUNICIPAL1", "municipal_name": "City of Charlottetown", "geometry": shape(json.loads(text))}],
        geometry="geometry",
        crs="EPSG:4326",
    )
    return boundary.to_crs(TARGET_CRS)


def rgb(value) -> tuple[int, int, int] | None:
    if value is None:
        return None
    return tuple(int(round(component * 255)) for component in value)


def cubic(p0, p1, p2, p3, steps: int = 8) -> list[tuple[float, float]]:
    points = []
    for index in range(1, steps + 1):
        t = index / steps
        mt = 1 - t
        x = mt**3 * p0.x + 3 * mt**2 * t * p1.x + 3 * mt * t**2 * p2.x + t**3 * p3.x
        y = mt**3 * p0.y + 3 * mt**2 * t * p1.y + 3 * mt * t**2 * p2.y + t**3 * p3.y
        points.append((x, y))
    return points


def drawing_paths(items) -> list[list[tuple[float, float]]]:
    paths: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []

    def append_point(point) -> None:
        xy = (float(point.x), float(point.y))
        if not current or current[-1] != xy:
            current.append(xy)

    def flush() -> None:
        nonlocal current
        if len(current) >= 2:
            paths.append(current)
        current = []

    for item in items:
        kind = item[0]
        if kind == "re":
            flush()
            rect = item[1]
            paths.append(
                [
                    (rect.x0, rect.y0),
                    (rect.x1, rect.y0),
                    (rect.x1, rect.y1),
                    (rect.x0, rect.y1),
                    (rect.x0, rect.y0),
                ]
            )
        elif kind == "l":
            if current and current[-1] != (float(item[1].x), float(item[1].y)):
                flush()
            append_point(item[1])
            append_point(item[2])
        elif kind == "c":
            if current and current[-1] != (float(item[1].x), float(item[1].y)):
                flush()
            append_point(item[1])
            current.extend(cubic(item[1], item[2], item[3], item[4]))
        elif kind == "qu":
            flush()
            quad = item[1]
            paths.append(
                [
                    (quad.ul.x, quad.ul.y),
                    (quad.ur.x, quad.ur.y),
                    (quad.lr.x, quad.lr.y),
                    (quad.ll.x, quad.ll.y),
                    (quad.ul.x, quad.ul.y),
                ]
            )
    flush()
    return paths


def path_polygon(path: list[tuple[float, float]]):
    if len(path) < 3:
        return None
    if path[0] != path[-1]:
        path = [*path, path[0]]
    geom = Polygon(path)
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom if not geom.is_empty and geom.area > 0 else None


def build_transform(boundary: gpd.GeoDataFrame, fit_bounds: tuple[float, float, float, float]):
    min_x, min_y, max_x, max_y = boundary.total_bounds
    pdf_min_x, pdf_min_y, pdf_max_x, pdf_max_y = fit_bounds
    scale_x = (max_x - min_x) / (pdf_max_x - pdf_min_x)
    scale_y = (max_y - min_y) / (pdf_max_y - pdf_min_y)

    def project_point(point: tuple[float, float]) -> tuple[float, float]:
        x, y = point
        projected_x = min_x + (x - pdf_min_x) * scale_x
        projected_y = max_y - (y - pdf_min_y) * scale_y
        return projected_x, projected_y

    return project_point


def schedule_c_to_schedule_a_pdf_point(point: tuple[float, float]) -> tuple[float, float]:
    x, y = point
    return (
        SCHEDULE_C_TO_A_PDF_AFFINE["sx"] * x + SCHEDULE_C_TO_A_PDF_AFFINE["tx"],
        SCHEDULE_C_TO_A_PDF_AFFINE["sy"] * y + SCHEDULE_C_TO_A_PDF_AFFINE["ty"],
    )


def compose_point_transforms(first, second):
    def project_point(point: tuple[float, float]) -> tuple[float, float]:
        return second(first(point))

    return project_point


def transform_geom(geom, project_point):
    if geom.geom_type == "Polygon":
        exterior = [project_point(point) for point in geom.exterior.coords]
        interiors = [[project_point(point) for point in ring.coords] for ring in geom.interiors]
        return Polygon(exterior, interiors)
    if geom.geom_type == "LineString":
        return LineString([project_point(point) for point in geom.coords])
    if geom.geom_type == "MultiPolygon":
        return MultiPolygon([transform_geom(part, project_point) for part in geom.geoms])
    if geom.geom_type == "MultiLineString":
        return MultiLineString([transform_geom(part, project_point) for part in geom.geoms])
    raise TypeError(f"Unsupported geometry type {geom.geom_type}")


def in_map_area(rect) -> bool:
    return rect is not None and rect.x0 < 946.5 and rect.x1 > 0 and rect.y0 < 775.8 and rect.y1 > 18.0


def extract_zone_areas(page, project_point, boundary_geom) -> gpd.GeoDataFrame:
    grouped = defaultdict(list)
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        fill = rgb(drawing.get("fill"))
        if fill not in ZONE_RGBS or not in_map_area(rect):
            continue
        for path in drawing_paths(drawing["items"]):
            geom = path_polygon(path)
            if geom is None:
                continue
            projected = transform_geom(geom, project_point).buffer(0)
            clipped = projected.intersection(boundary_geom)
            if not clipped.is_empty and clipped.area >= 10:
                grouped[fill].append(clipped)

    rows = []
    for legend_rgb, pieces in grouped.items():
        code, name = ZONE_BY_RGB[legend_rgb]
        geom = unary_union(pieces).buffer(0).intersection(boundary_geom).buffer(0)
        if geom.is_empty:
            continue
        rows.append(
            {
                "zone_code": code,
                "zone_name": name,
                "legend_rgb": "#{:02x}{:02x}{:02x}".format(*legend_rgb),
                "source_pdf": str(PDF_PATH.relative_to(ROOT)).replace("\\", "/"),
                "source_page": 197,
                "registration": "PDF Schedule A zoning colour envelope fitted to City of Charlottetown municipal boundary from PEI_Municipal_Zones.MUNICIPAL1",
                "method": "direct extraction of filled PDF vector paths; clipped to official municipal boundary; draft QA required",
                "area_m2": float(geom.area),
                "geometry": geom,
            }
        )
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=TARGET_CRS)


def extract_wetlands(page, project_point, boundary_geom) -> gpd.GeoDataFrame:
    rows = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rgb(drawing.get("fill")) != WETLAND_RGB or not in_map_area(rect):
            continue
        for path in drawing_paths(drawing["items"]):
            geom = path_polygon(path)
            if geom is None:
                continue
            projected = transform_geom(geom, project_point).buffer(0)
            clipped = projected.intersection(boundary_geom)
            if not clipped.is_empty and clipped.area >= 25:
                rows.append(
                    {
                        "feature_type": "wetland_or_waterbody_cartographic_fill",
                        "source_page": 197,
                        "method": "light grey non-angular fill extracted from Schedule A; excluded from parcel candidate polygonization",
                        "area_m2": float(clipped.area),
                        "geometry": clipped,
                    }
                )
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=TARGET_CRS)


def extract_linework(page, project_point, boundary_geom, source_page: int) -> gpd.GeoDataFrame:
    rows = []

    def line_parts(geom):
        if geom.geom_type == "LineString":
            return [geom]
        if geom.geom_type == "MultiLineString":
            return list(geom.geoms)
        if geom.geom_type == "GeometryCollection":
            parts = []
            for part in geom.geoms:
                parts.extend(line_parts(part))
            return parts
        return []

    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rgb(drawing.get("color")) != (0, 0, 0) or not in_map_area(rect):
            continue
        if round(float(drawing.get("width") or 0), 3) not in {0.1, 0.25}:
            continue
        for path in drawing_paths(drawing["items"]):
            if len(path) < 2:
                continue
            line = LineString(path)
            if line.length <= 0:
                continue
            projected = transform_geom(line, project_point)
            clipped = projected.intersection(boundary_geom)
            if clipped.is_empty:
                continue
            clipped = clipped.simplify(0.25, preserve_topology=False)
            for part in line_parts(clipped):
                if part.length >= 12:
                    rows.append(
                        {
                            "source_page": source_page,
                            "stroke_width_pdf": float(drawing.get("width") or 0),
                            "method": "black vector stroke extracted from PDF and clipped to municipal boundary",
                            "length_m": float(part.length),
                            "geometry": part,
                        }
                    )
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=TARGET_CRS)


def parcel_candidates(
    linework: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame | None,
    source: str,
) -> gpd.GeoDataFrame:
    boundary_geom = boundary.geometry.iloc[0]
    lines = [shapely.set_precision(boundary_geom.boundary, 0.05)]
    if not linework.empty:
        lines.extend(shapely.set_precision(geom, 0.05) for geom in linework.geometry)
    if zones is not None and not zones.empty:
        lines.extend(shapely.set_precision(geom, 0.05) for geom in zones.boundary)

    noded_lines = unary_union(lines)
    polygons = []
    for geom in polygonize(noded_lines):
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty:
            continue
        try:
            clipped = geom.intersection(boundary_geom).buffer(0)
        except Exception:
            continue
        if clipped.is_empty or clipped.area < 50:
            continue
        polygons.append(clipped)

    rows = []
    conservation = None
    if zones is not None and not zones.empty and "zone_code" in zones:
        conservation_geoms = list(zones[zones["zone_code"] == "C"].geometry)
        if conservation_geoms:
            conservation = unary_union(conservation_geoms).buffer(0)

    if conservation is not None and source == "schedule_a_zoning":
        retained = []
        for geom in polygons:
            if conservation.contains(geom.representative_point()):
                continue
            retained.append(geom.difference(conservation).buffer(0))
        polygons = [geom for geom in retained if not geom.is_empty and geom.area >= 50]
        c_parts = list(conservation.geoms) if conservation.geom_type == "MultiPolygon" else [conservation]
        polygons.extend([part for part in c_parts if not part.is_empty and part.area >= 50])

    for idx, geom in enumerate(polygons, start=1):
        rows.append(
            {
                "parcel_candidate_id": idx,
                "source_map": source,
                "method": "polygonized municipal boundary, zoning boundaries, and internal linework; draft QA required",
                "area_m2": float(geom.area),
                "geometry": geom,
            }
        )
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=TARGET_CRS)


def write_layer(gdf: gpd.GeoDataFrame, layer: str, append: bool = True) -> None:
    pyogrio.write_dataframe(
        gdf,
        OUT_GPKG,
        layer=layer,
        driver="GPKG",
        promote_to_multi=True,
        append=append,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_GPKG.exists():
        OUT_GPKG.unlink()

    boundary = fetch_municipal_boundary()
    boundary_geom = boundary.geometry.iloc[0]
    project_schedule_a_point = build_transform(boundary, SCHEDULE_A_MAP_FIT_BOUNDS)
    project_schedule_c_point = compose_point_transforms(
        schedule_c_to_schedule_a_pdf_point,
        project_schedule_a_point,
    )
    doc = fitz.open(PDF_PATH)

    schedule_a = doc[SCHEDULE_A_PAGE_INDEX]
    schedule_c = doc[SCHEDULE_C_PAGE_INDEX]

    zones = extract_zone_areas(schedule_a, project_schedule_a_point, boundary_geom)
    wetlands = extract_wetlands(schedule_a, project_schedule_a_point, boundary_geom)
    linework_a = extract_linework(schedule_a, project_schedule_a_point, boundary_geom, 197)
    linework_c = extract_linework(schedule_c, project_schedule_c_point, boundary_geom, 199)
    parcels_a = parcel_candidates(linework_a, boundary, zones, "schedule_a_zoning")
    parcels_c = parcel_candidates(linework_c, boundary, None, "schedule_c_street_hierarchy")

    write_layer(zones, "schedule_a_zoning_areas_municipal_fit", append=False)
    write_layer(parcels_a, "schedule_a_parcel_candidates_municipal_fit")
    write_layer(linework_a, "schedule_a_linework_municipal_fit")
    write_layer(parcels_c, "schedule_c_parcel_candidates_municipal_fit")
    write_layer(linework_c, "schedule_c_linework_municipal_fit")
    write_layer(wetlands, "schedule_a_wetlands_excluded_from_parcels")
    write_layer(boundary, "municipal_boundary_reference")

    summary = {
        "output": str(OUT_GPKG.relative_to(ROOT)).replace("\\", "/"),
        "target_crs": TARGET_CRS,
        "source_pdf": str(PDF_PATH.relative_to(ROOT)).replace("\\", "/"),
        "municipal_boundary_layer": "PEI_Municipal_Zones",
        "municipal_boundary_attribute": "MUNICIPAL1",
        "municipal_boundary_value": "City of Charlottetown",
        "map_fit_bounds_pdf": {
            "schedule_a": SCHEDULE_A_MAP_FIT_BOUNDS,
        },
        "schedule_c_to_schedule_a_pdf_affine": {
            **SCHEDULE_C_TO_A_PDF_AFFINE,
            "basis": "distance-transform fit of Schedule C black parcel-line vectors onto Schedule A black parcel-line vectors in PDF coordinates",
        },
        "layers": {
            "schedule_a_zoning_areas_municipal_fit": len(zones),
            "schedule_a_parcel_candidates_municipal_fit": len(parcels_a),
            "schedule_a_linework_municipal_fit": len(linework_a),
            "schedule_c_parcel_candidates_municipal_fit": len(parcels_c),
            "schedule_c_linework_municipal_fit": len(linework_c),
            "schedule_a_wetlands_excluded_from_parcels": len(wetlands),
            "municipal_boundary_reference": len(boundary),
        },
        "zone_area_m2": {
            row.zone_code: float(row.area_m2) for row in zones.sort_values("zone_code").itertuples()
        },
        "qa_notes": [
            "Schedule A parcel candidates dissolve Conservation zones instead of subdividing by internal lines.",
            "Light grey wetland/waterbody cartographic fills are written as a reference layer and excluded from parcel candidates.",
            "Schedule C parcel candidates are derived from internal black linework and municipal boundary only; road arrows and street names may still obscure local parcel detail.",
        ],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
