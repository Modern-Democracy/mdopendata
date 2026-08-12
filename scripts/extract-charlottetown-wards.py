from __future__ import annotations

import argparse
import itertools
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import fitz
import geopandas as gpd
import pandas as pd
import pyogrio
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "maps" / "Chtown_All_Wards.pdf"
DEFAULT_BOUNDARY = ROOT / "maps" / "pei" / "CHTWN_Municipal_Boundary.geojson"
DEFAULT_GPKG = ROOT / "data" / "spatial" / "charlottetown" / "charlottetown-wards-municipal-fit.gpkg"
DEFAULT_SUMMARY = ROOT / "data" / "spatial" / "charlottetown" / "charlottetown-wards-municipal-fit.summary.json"
TARGET_CRS = "EPSG:2954"
PDF_SOURCE_LAYER = "Map_Information_Tool_Specific_Calculation_Edit_ElectoralDistricts"
PAGE_WIDTH_PT = 3456.0
PAGE_HEIGHT_PT = 2592.0
PDF_NEATLINE = (483894.51962561, 5119289.3362954, 495729.322166039, 5128026.13584662)
DEFAULT_MIN_RETAINED_HOLE_AREA_M2 = 1000.0

FILL_COLOR_BY_DISTRICT = {
    "1": "#97DBF2",
    "2": "#CEFCB3",
    "3": "#FCB6EA",
    "4": "#D2FCD9",
    "5": "#FCC0C3",
    "6": "#FCD2F0",
    "7": "#CFE6FC",
    "8": "#B3FCDA",
    "9": "#D8C2FC",
    "10": "#FCB6D2",
}


def ogrinfo_path() -> str:
    configured = shutil.which("ogrinfo")
    return configured or r"C:\Program Files\GDAL\ogrinfo.exe"


def ogr2ogr_path() -> str:
    configured = shutil.which("ogr2ogr")
    return configured or r"C:\Program Files\GDAL\ogr2ogr.exe"


def extract_pdf_layer(pdf_path: Path) -> gpd.GeoDataFrame:
    temp_root = ROOT / "tmp" / "pdfs"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="charlottetown-wards-", dir=temp_root) as temp_dir:
        raw_gpkg = Path(temp_dir) / "source.gpkg"
        subprocess.run(
            [ogr2ogr_path(), "-f", "GPKG", str(raw_gpkg), str(pdf_path), PDF_SOURCE_LAYER, "-nln", "source_features", "-nlt", "PROMOTE_TO_MULTI"],
            check=True,
            capture_output=True,
        )
        return gpd.read_file(raw_gpkg, layer="source_features")


def read_source_styles(pdf_path: Path) -> dict[int, str]:
    result = subprocess.run(
        [ogrinfo_path(), str(pdf_path), PDF_SOURCE_LAYER, "-al", "-geom=SUMMARY"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8", errors="replace")
    styles: dict[int, str] = {}
    current_fid: int | None = None
    for line in text.splitlines():
        feature_match = re.search(r"OGRFeature\([^)]*\):(\d+)", line)
        if feature_match:
            current_fid = int(feature_match.group(1))
            continue
        style_match = re.search(r"Style = (.+)$", line)
        if style_match and current_fid is not None:
            styles[current_fid] = style_match.group(1).strip()
    if not styles:
        raise RuntimeError("Could not read PDF feature styles from the GDAL PDF driver.")
    return styles


def fill_color(style: str | None) -> str | None:
    if not style:
        return None
    match = re.search(r"BRUSH\(fc:(#[0-9A-Fa-f]{6})\)", style)
    return match.group(1).upper() if match else None


def source_point_to_target(point: tuple[float, float], source_crs, target_crs: str = TARGET_CRS) -> tuple[float, float]:
    x_pdf, y_pdf = point
    min_x, min_y, max_x, max_y = PDF_NEATLINE
    source_x = min_x + (x_pdf / PAGE_WIDTH_PT) * (max_x - min_x)
    source_y = max_y - (y_pdf / PAGE_HEIGHT_PT) * (max_y - min_y)
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transformer.transform(source_x, source_y)


def parse_labels(pdf_path: Path, source_crs) -> list[dict]:
    document = fitz.open(pdf_path)
    if len(document) != 1:
        raise RuntimeError(f"Expected one ward-map page, found {len(document)} pages.")
    labels = []
    for word in document[0].get_text("words"):
        raw = str(word[4]).strip()
        if not re.fullmatch(r"\d{1,2}-\d+", raw):
            continue
        ward, division = raw.split("-", 1)
        x = (float(word[0]) + float(word[2])) / 2.0
        y = (float(word[1]) + float(word[3])) / 2.0
        target_x, target_y = source_point_to_target((x, y), source_crs)
        labels.append(
            {
                "polling_division_code": raw,
                "ward_code": ward,
                "ward_number": int(ward),
                "polling_division_number": int(division),
                "label_point": Point(target_x, target_y),
                "pdf_x": x,
                "pdf_y": y,
            }
        )
    labels.sort(key=lambda row: (row["ward_number"], row["polling_division_number"]))
    return labels


def choose_color_groups(labels: list[dict], polygons: gpd.GeoDataFrame, styles: dict[int, str]) -> dict[str, str]:
    colors = sorted({fill_color(styles.get(int(fid))) for fid in polygons.index} - {None})
    if set(colors) != set(FILL_COLOR_BY_DISTRICT.values()):
        raise RuntimeError(f"Unexpected PDF fill colors: {colors}")
    selected: dict[str, str] = {}
    for ward in sorted({row["ward_code"] for row in labels}, key=int):
        ward_labels = [row["label_point"] for row in labels if row["ward_code"] == ward]
        scores = []
        for color in colors:
            candidates = [polygons.loc[fid].geometry for fid in polygons.index if fill_color(styles.get(int(fid))) == color]
            distances = [min(point.distance(geom) for geom in candidates) for point in ward_labels]
            scores.append((sum(distance == 0 for distance in distances), -sum(distances), color))
        selected[ward] = max(scores)[2]
    expected = {ward: color for ward, color in FILL_COLOR_BY_DISTRICT.items()}
    if selected != expected:
        raise RuntimeError(f"Could not map PDF fill colors to electoral-ward labels: {selected}")
    return selected


def minimum_centroid_assignment(labels: list[dict], polygons: gpd.GeoDataFrame, styles: dict[int, str], color: str) -> dict[str, tuple[int, float]]:
    label_rows = [row for row in labels if row["ward_code"] in {ward for ward, expected in FILL_COLOR_BY_DISTRICT.items() if expected == color}]
    polygon_ids = [int(fid) for fid in polygons.index if fill_color(styles.get(int(fid))) == color]
    if len(label_rows) != len(polygon_ids):
        raise RuntimeError(f"District color {color} has {len(label_rows)} labels and {len(polygon_ids)} polygons.")
    best_cost = float("inf")
    best: tuple[int, ...] | None = None
    costs = [[row["label_point"].distance(polygons.loc[fid].geometry.centroid) for fid in polygon_ids] for row in label_rows]
    for permutation in itertools.permutations(range(len(polygon_ids))):
        cost = sum(costs[row_index][polygon_index] for row_index, polygon_index in enumerate(permutation))
        if cost < best_cost:
            best_cost = cost
            best = permutation
    assert best is not None
    return {
        row["polling_division_code"]: (
            polygon_ids[polygon_index],
            row["label_point"].distance(polygons.loc[polygon_ids[polygon_index]].geometry),
        )
        for row, polygon_index in zip(label_rows, best)
    }


def boundary_geometry(boundary_path: Path):
    boundary = gpd.read_file(boundary_path)
    if boundary.empty:
        raise RuntimeError(f"Municipal boundary file is empty: {boundary_path}")
    if boundary.crs is None:
        boundary = boundary.set_crs("EPSG:4326")
    return unary_union(boundary.to_crs(TARGET_CRS).geometry).buffer(0)


def clean_electoral_ward_holes(geometry, min_retained_hole_area_m2: float):
    """Remove tiny interior rings created by small source-area gaps/overlaps.

    The two map-derived open-water holes are substantially larger than the
    cartographic slivers. A conservative area threshold retains those holes
    while removing the narrow orphaned line segments from the dissolved
    electoral-ward geometries. Polygon parts and their exterior boundaries are not
    otherwise generalized.
    """
    parts = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    cleaned_parts = []
    removed_count = 0
    removed_area_m2 = 0.0
    retained_count = 0
    retained_area_m2 = 0.0
    for part in parts:
        retained_interiors = []
        for ring in part.interiors:
            hole_area_m2 = float(Polygon(ring).area)
            if hole_area_m2 >= min_retained_hole_area_m2:
                retained_interiors.append(ring)
                retained_count += 1
                retained_area_m2 += hole_area_m2
            else:
                removed_count += 1
                removed_area_m2 += hole_area_m2
        cleaned_parts.append(Polygon(part.exterior, retained_interiors))
    cleaned = unary_union(cleaned_parts).buffer(0)
    return cleaned, {
        "removed_hole_count": removed_count,
        "removed_hole_area_m2": removed_area_m2,
        "retained_hole_count": retained_count,
        "retained_hole_area_m2": retained_area_m2,
    }


def partition_polling_divisions(area_rows: list[dict], ward_domain, owner_domains: dict[str, object] | None = None):
    """Build a deterministic, gap-free polling-division partition inside the ward domain.

    The PDF polygons contain small overlaps and boundary gaps. Polygonizing
    all source and ward-domain boundaries creates atomic faces. Each face
    is assigned to exactly one source polling division by maximum source overlap, with a
    shared-boundary-length tie break for uncovered gap faces. The result is a
    coverage of the supplied ward domain with no area overlap.
    """
    source_geometries = [row["geometry"] for row in area_rows]
    source_codes = [row["polling_division_code"] for row in area_rows]
    linework = unary_union([geometry.boundary for geometry in source_geometries] + [ward_domain.boundary])
    faces = []
    for face in polygonize(linework):
        if face.is_empty or face.area <= 0:
            continue
        clipped = face.intersection(ward_domain)
        if clipped.is_empty:
            continue
        if clipped.geom_type == "GeometryCollection":
            clipped_parts = [part for part in clipped.geoms if part.geom_type in {"Polygon", "MultiPolygon"}]
        elif clipped.geom_type == "MultiPolygon":
            clipped_parts = list(clipped.geoms)
        else:
            clipped_parts = [clipped]
        faces.extend(part for part in clipped_parts if not part.is_empty and part.area > 0)
    if not faces:
        raise RuntimeError("Could not polygonize the polling-division boundaries inside an electoral ward domain.")

    tree = STRtree(source_geometries)
    assigned: dict[str, list] = {code: [] for code in source_codes}
    assignment_counts = {code: 0 for code in source_codes}
    for face in faces:
        candidate_indices = tree.query(face, predicate="intersects").tolist()
        overlap_scores = []
        for index in candidate_indices:
            overlap = face.intersection(source_geometries[index]).area
            if overlap > 1e-8:
                overlap_scores.append((float(overlap), source_codes[index], index))
        if overlap_scores:
            _, code, _ = max(overlap_scores, key=lambda item: (item[0], item[1]))
        else:
            boundary_scores = []
            for index in candidate_indices:
                shared_boundary = face.boundary.intersection(source_geometries[index].boundary).length
                boundary_scores.append((float(shared_boundary), source_codes[index], index))
            if not boundary_scores:
                representative_point = face.representative_point()
                eligible = [
                    (index, code, geometry)
                    for index, (code, geometry) in enumerate(zip(source_codes, source_geometries))
                    if owner_domains is None or owner_domains[code].covers(representative_point)
                ]
                if not eligible:
                    eligible = list(zip(range(len(source_codes)), source_codes, source_geometries))
                distances = [(representative_point.distance(geometry), code, index) for index, code, geometry in eligible]
                _, code, _ = min(distances, key=lambda item: (item[0], item[1]))
            else:
                _, code, _ = max(boundary_scores, key=lambda item: (item[0], item[1]))
        assigned[code].append(face)
        assignment_counts[code] += 1

    corrected = {}
    for code, original_geometry in zip(source_codes, source_geometries):
        pieces = assigned[code]
        if not pieces:
            raise RuntimeError(f"Polling division {code} received no partition faces.")
        corrected_geometry = unary_union(pieces).buffer(0)
        if corrected_geometry.is_empty or corrected_geometry.area <= 0:
            raise RuntimeError(f"Polling division {code} has no geometry after topology correction.")
        corrected[code] = corrected_geometry

    corrected_union = unary_union(list(corrected.values())).buffer(0)
    domain_difference_m2 = float(corrected_union.symmetric_difference(ward_domain).area)
    if domain_difference_m2 > 0.01:
        raise RuntimeError(
            f"Corrected polling divisions do not cover the electoral-ward domain; residual difference is {domain_difference_m2:.6f} m2."
        )

    metrics = {
        "face_count": len(faces),
        "assigned_face_count_by_area": assignment_counts,
        "source_area_sum_m2": float(sum(geometry.area for geometry in source_geometries)),
        "source_union_area_m2": float(unary_union(source_geometries).area),
        "corrected_area_sum_m2": float(sum(geometry.area for geometry in corrected.values())),
        "corrected_union_area_m2": float(corrected_union.area),
        "domain_area_m2": float(ward_domain.area),
        "domain_difference_m2": domain_difference_m2,
        "overlap_excess_m2": float(sum(geometry.area for geometry in source_geometries) - unary_union(source_geometries).area),
        "gap_fill_m2": float(ward_domain.area - unary_union(source_geometries).area),
    }
    return corrected, metrics


def write_layer(gdf: gpd.GeoDataFrame, output: Path, layer: str, append: bool) -> None:
    pyogrio.write_dataframe(gdf, output, layer=layer, driver="GPKG", append=append, promote_to_multi=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Charlottetown polling divisions and electoral ward geometries from the ward PDF.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--out-gpkg", type=Path, default=DEFAULT_GPKG)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--min-retained-hole-area-m2",
        type=float,
        default=DEFAULT_MIN_RETAINED_HOLE_AREA_M2,
        help="Retain electoral-ward interior holes at or above this area; smaller rings are treated as source slivers.",
    )
    args = parser.parse_args()
    pdf_path = args.pdf.resolve()
    boundary_path = args.boundary.resolve()
    output = args.out_gpkg.resolve()
    summary_path = args.summary.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    polygons = extract_pdf_layer(pdf_path)
    source_crs = polygons.crs
    if source_crs is None:
        raise RuntimeError("The PDF vector layer has no CRS.")
    polygons = polygons[polygons.geometry.geom_type.str.contains("Polygon")].copy()
    styles = read_source_styles(pdf_path)
    labels = parse_labels(pdf_path, source_crs)
    if len(labels) != 69 or len(polygons) != 69:
        raise RuntimeError(f"Expected 69 labels and 69 polygons, found {len(labels)} and {len(polygons)}.")
    polygons = polygons.to_crs(TARGET_CRS)
    color_by_ward = choose_color_groups(labels, polygons, styles)
    boundary = boundary_geometry(boundary_path)

    assignments: dict[str, tuple[int, float]] = {}
    for color in color_by_ward.values():
        assignments.update(minimum_centroid_assignment(labels, polygons, styles, color))
    if set(assignments) != {row["polling_division_code"] for row in labels}:
        raise RuntimeError("Polling-division label assignment was not one-to-one.")

    area_rows = []
    for label in labels:
        source_fid, label_distance = assignments[label["polling_division_code"]]
        geometry = polygons.loc[source_fid].geometry.buffer(0).intersection(boundary).buffer(0)
        if geometry.is_empty or geometry.area <= 0:
            raise RuntimeError(f"Polling division {label['polling_division_code']} has no geometry after municipal clipping.")
        color = color_by_ward[label["ward_code"]]
        area_rows.append(
            {
                "polling_division_code": label["polling_division_code"],
                "ward_code": label["ward_code"],
                "ward_number": label["ward_number"],
                "polling_division_number": label["polling_division_number"],
                "source_pdf": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
                "source_page": 1,
                "source_layer": PDF_SOURCE_LAYER,
                "source_feature_fid": source_fid,
                "source_fill_rgb": color,
                "label_match_distance_m": float(label_distance),
                "method": "GDAL PDF vector polygon matched to the printed polling-division label and clipped to the official municipal boundary",
                "topology_removed_m2": 0.0,
                "topology_added_m2": 0.0,
                "topology_symmetric_difference_m2": 0.0,
                "topology_partition_face_count": 0,
                "area_m2": float(geometry.area),
                "geometry": geometry,
            }
        )
    areas = gpd.GeoDataFrame(area_rows, geometry="geometry", crs=TARGET_CRS).sort_values("polling_division_code").reset_index(drop=True)

    if args.min_retained_hole_area_m2 < 0:
        raise RuntimeError("--min-retained-hole-area-m2 must be non-negative.")
    ward_cleanup = {}
    ward_domains = {}
    for ward, group in areas.groupby("ward_code", sort=True, observed=True):
        raw_geometry = unary_union(group.geometry).buffer(0).intersection(boundary).buffer(0)
        ward_domains[str(ward)], ward_cleanup[str(ward)] = clean_electoral_ward_holes(
            raw_geometry, args.min_retained_hole_area_m2
        )

    global_domain = unary_union(list(ward_domains.values())).buffer(0)
    source_rows = [{"polling_division_code": row.polling_division_code, "geometry": row.geometry, "ward_code": row.ward_code} for row in areas.itertuples()]
    corrected_by_code, global_topology = partition_polling_divisions(
        source_rows,
        global_domain,
        owner_domains={str(row.polling_division_code): ward_domains[str(row.ward_code)] for row in areas.itertuples()},
    )
    for row_index in areas.index:
        code = str(areas.at[row_index, "polling_division_code"])
        original_geometry = areas.at[row_index, "geometry"]
        corrected_geometry = corrected_by_code[code]
        areas.at[row_index, "geometry"] = corrected_geometry
        areas.at[row_index, "topology_removed_m2"] = float(original_geometry.difference(corrected_geometry).area)
        areas.at[row_index, "topology_added_m2"] = float(corrected_geometry.difference(original_geometry).area)
        areas.at[row_index, "topology_symmetric_difference_m2"] = float(original_geometry.symmetric_difference(corrected_geometry).area)
        areas.at[row_index, "topology_partition_face_count"] = int(global_topology["assigned_face_count_by_area"][code])
        areas.at[row_index, "method"] = (
            "GDAL PDF vector polygon matched to the printed polling-division label, clipped to the official municipal boundary, "
            "and corrected into a global non-overlapping coverage partition"
        )
        areas.at[row_index, "area_m2"] = float(corrected_geometry.area)

    ward_rows = []
    ward_topology = {}
    for ward, group in areas.groupby("ward_code", sort=True, observed=True):
        geometry = unary_union(group.geometry).buffer(0)
        source_group = [row for row in source_rows if str(row["ward_code"]) == str(ward)]
        source_union = unary_union([row["geometry"] for row in source_group])
        ward_topology[str(ward)] = {
            "source_area_sum_m2": float(sum(row["geometry"].area for row in source_group)),
            "source_union_area_m2": float(source_union.area),
            "corrected_area_sum_m2": float(sum(row.geometry.area for row in group.itertuples())),
            "corrected_union_area_m2": float(geometry.area),
            "domain_area_m2": float(ward_domains[str(ward)].area),
            "domain_difference_m2": float(geometry.symmetric_difference(ward_domains[str(ward)]).area),
            "overlap_excess_m2": float(sum(row["geometry"].area for row in source_group) - source_union.area),
            "gap_fill_m2": float(ward_domains[str(ward)].area - source_union.area),
        }
        ward_rows.append(
            {
                "ward_code": ward,
                "ward_number": int(ward),
                "polling_division_count": int(len(group)),
                "source_pdf": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
                "source_page": 1,
                "source_layer": PDF_SOURCE_LAYER,
                "source_fill_rgb": color_by_ward[ward],
                "method": (
                    "Dissolve of globally topology-corrected polling-division polygons by electoral-ward code; clipped to the official municipal boundary; "
                    f"interior rings below {args.min_retained_hole_area_m2:g} m2 removed as source slivers"
                ),
                "area_m2": float(geometry.area),
                "geometry": geometry,
            }
        )
    wards = gpd.GeoDataFrame(ward_rows, geometry="geometry", crs=TARGET_CRS).sort_values("ward_number").reset_index(drop=True)
    boundary_gdf = gpd.GeoDataFrame(
        [{"source_layer": boundary_path.name, "municipal_name": "City of Charlottetown", "source_pdf": str(pdf_path.relative_to(ROOT)).replace("\\", "/"), "geometry": boundary}],
        geometry="geometry",
        crs=TARGET_CRS,
    )

    ward_geometry_by_code = {str(row.ward_code): row.geometry for row in wards.itertuples()}
    area_overlap_pairs = []
    area_outside_m2 = 0.0
    district_area_delta_m2 = 0.0
    all_area_rows = list(areas.itertuples())
    for ward, group in areas.groupby("ward_code", sort=True, observed=True):
        ward_geometry = ward_geometry_by_code[str(ward)]
        for row in group.itertuples():
            area_outside_m2 += float(row.geometry.difference(ward_geometry).area)
        district_area_delta_m2 += abs(float(ward_geometry.area) - float(sum(group.geometry.area)))
    for left_index, left in enumerate(all_area_rows):
        for right in all_area_rows[left_index + 1 :]:
            overlap_m2 = float(left.geometry.intersection(right.geometry).area)
            if overlap_m2 > 0.01:
                area_overlap_pairs.append(
                    {
                        "left_code": left.polling_division_code,
                        "right_code": right.polling_division_code,
                        "left_ward_code": str(left.ward_code),
                        "right_ward_code": str(right.ward_code),
                        "overlap_m2": overlap_m2,
                    }
                )

    write_layer(areas, output, "polling_divisions_municipal_fit", append=False)
    write_layer(wards, output, "electoral_wards_municipal_fit", append=True)
    write_layer(boundary_gdf, output, "municipal_boundary_reference", append=True)

    union_geometry = unary_union(areas.geometry).buffer(0)
    summary = {
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "source_pdf": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
        "source_layer": PDF_SOURCE_LAYER,
        "source_crs": source_crs.to_string(),
        "target_crs": TARGET_CRS,
        "municipal_boundary": str(boundary_path.relative_to(ROOT)).replace("\\", "/"),
        "feature_counts": {"polling_divisions": len(areas), "electoral_wards": len(wards)},
        "ward_polling_division_counts": {str(row.ward_code): int(row.polling_division_count) for row in wards.itertuples()},
        "geometry_qa": {
            "polling_division_invalid_count": int((~areas.geometry.is_valid).sum()),
            "electoral_ward_invalid_count": int((~wards.geometry.is_valid).sum()),
            "polling_division_empty_count": int(areas.geometry.is_empty.sum()),
            "electoral_ward_empty_count": int(wards.geometry.is_empty.sum()),
            "area_union_m2": float(union_geometry.area),
            "municipal_boundary_m2": float(boundary.area),
            "union_boundary_difference_m2": float(boundary.symmetric_difference(union_geometry).area),
            "max_label_match_distance_m": float(areas.label_match_distance_m.max()),
            "label_match_review_count_over_5m": int((areas.label_match_distance_m > 5).sum()),
        },
        "polling_division_topology": {
            "overlap_pair_count_over_0_01m2": len(area_overlap_pairs),
            "total_overlap_m2_over_0_01m2": float(sum(item["overlap_m2"] for item in area_overlap_pairs)),
            "max_overlap_m2_over_0_01m2": float(max((item["overlap_m2"] for item in area_overlap_pairs), default=0.0)),
            "polling_division_outside_owning_ward_m2": float(area_outside_m2),
            "electoral_ward_area_sum_delta_m2": float(district_area_delta_m2),
            "electoral_ward_domain_difference_m2": float(sum(item["domain_difference_m2"] for item in ward_topology.values())),
            "global_domain_difference_m2": float(global_topology["domain_difference_m2"]),
            "electoral_wards_with_partition_faces": len(ward_topology),
        },
        "electoral_ward_topology": ward_topology,
        "electoral_ward_hole_cleanup": {
            "min_retained_hole_area_m2": float(args.min_retained_hole_area_m2),
            "per_ward": ward_cleanup,
            "removed_hole_count": int(sum(item["removed_hole_count"] for item in ward_cleanup.values())),
            "removed_hole_area_m2": float(sum(item["removed_hole_area_m2"] for item in ward_cleanup.values())),
            "retained_hole_count": int(sum(item["retained_hole_count"] for item in ward_cleanup.values())),
            "retained_hole_area_m2": float(sum(item["retained_hole_area_m2"] for item in ward_cleanup.values())),
        },
        "fill_rgb_by_ward": color_by_ward,
        "notes": [
            "The PDF is an Esri ArcMap vector export and was read through the GDAL PDF driver.",
            "The 69 printed labels use ward-division codes such as 1-1 and 10-7; the first component is the electoral ward and the second is the polling division.",
            "Electoral wards are dissolved from polling divisions and both layers are clipped to maps/pei/CHTWN_Municipal_Boundary.geojson.",
            "Electoral-ward interior rings below the configured area threshold are removed to clean source slivers; larger map-derived open-water holes are retained.",
            "All polling-division and electoral-ward boundaries are polygonized into one global partition; each face is assigned to exactly one polling division and electoral wards are regenerated as exact unions of those corrected areas.",
            "Small label-to-polygon distances occur where PDF text placement overlaps a shared boundary; source feature and match distance are retained for audit.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
