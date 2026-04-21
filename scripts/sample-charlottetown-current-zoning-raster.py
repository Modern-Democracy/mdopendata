from __future__ import annotations

import json
import math
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import psycopg
import rasterio
from shapely.geometry import Point
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[1]
REVIEW_TABLE = "CHTWN_Current_Zoning_Parcel_Review"
RASTER_PATH = ROOT / "data" / "spatial" / "charlottetown" / "charlottetown-zoning-map-2026-raster.gpkg"
LEGEND_PATH = ROOT / "data" / "spatial" / "charlottetown" / "current-zoning-map-legend-2026-03-09.json"

MAX_GRID_AXIS = 7
MIN_GRID_AXIS = 3
MAX_SAMPLES = 49
NEAR_WHITE_THRESHOLD = 242
NEAR_BLACK_THRESHOLD = 28


@dataclass(frozen=True)
class RasterClass:
    map_legend_code: str
    rgb: tuple[int, int, int]
    threshold: float
    style: str
    ambiguous_group: str | None = None


# Colours are sampled from the March 9, 2026 map legend and the extracted PDF
# image. Hatched classes are useful as review hints, not automatic assignments.
RASTER_CLASSES = [
    RasterClass("C1", (255, 51, 154), 75, "solid"),
    RasterClass("C2", (205, 121, 51), 75, "solid"),
    RasterClass("C3", (255, 119, 51), 75, "solid"),
    RasterClass("CDA", (192, 194, 218), 55, "pattern"),
    RasterClass("DC", (214, 88, 91), 75, "solid"),
    RasterClass("DMS", (185, 134, 133), 70, "solid"),
    RasterClass("DMU", (190, 140, 135), 65, "pattern", "DMU_OR_MHR"),
    RasterClass("DMUN", (162, 161, 105), 70, "solid"),
    RasterClass("DN", (222, 169, 185), 70, "solid"),
    RasterClass("FDA", (92, 92, 92), 70, "pattern"),
    RasterClass("I", (143, 193, 254), 75, "solid", "I_OR_P"),
    RasterClass("P", (143, 193, 254), 75, "solid", "I_OR_P"),
    RasterClass("M1", (214, 214, 214), 34, "solid"),
    RasterClass("M2", (134, 134, 134), 48, "solid"),
    RasterClass("M3", (210, 159, 192), 70, "solid"),
    RasterClass("MH", (164, 164, 164), 60, "pattern"),
    RasterClass("MHR", (190, 140, 135), 65, "pattern", "DMU_OR_MHR"),
    RasterClass("MUC", (255, 187, 52), 75, "solid"),
    RasterClass("MUR", (235, 173, 52), 75, "solid"),
    RasterClass("ERMUVC", (185, 51, 50), 75, "solid"),
    RasterClass("NA", (208, 51, 254), 75, "solid"),
    RasterClass("OS", (111, 235, 51), 75, "solid"),
    RasterClass("PC", (131, 171, 136), 65, "solid"),
    RasterClass("PZ", (190, 79, 238), 75, "pattern"),
    RasterClass("R1L", (255, 255, 143), 72, "solid"),
    RasterClass("R1N", (253, 219, 235), 40, "solid"),
    RasterClass("R1S", (221, 255, 161), 68, "solid"),
    RasterClass("R2", (240, 208, 125), 68, "solid", "R2_OR_R2S"),
    RasterClass("R2S", (240, 208, 125), 68, "pattern", "R2_OR_R2S"),
    RasterClass("R3", (185, 185, 51), 68, "solid", "R3_OR_R4"),
    RasterClass("R4", (185, 185, 51), 68, "solid", "R3_OR_R4"),
    RasterClass("R3T", (142, 81, 52), 65, "solid"),
    RasterClass("R4A", (185, 141, 52), 65, "solid"),
    RasterClass("R4B", (93, 93, 93), 58, "solid"),
    RasterClass("WF", (250, 191, 74), 75, "pattern"),
    RasterClass("WLC", (204, 237, 255), 65, "solid"),
    RasterClass("WLOS", (51, 114, 185), 75, "solid"),
]


def database_url(driver: str = "sqlalchemy") -> str:
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "54329")
    database = os.getenv("PGDATABASE", "mdopendata")
    user = os.getenv("PGUSER", "mdopendata")
    password = os.getenv("PGPASSWORD", "mdopendata_dev")
    if driver == "psycopg":
        return f"host={host} port={port} dbname={database} user={user} password={password}"
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def load_lookup() -> dict[str, dict]:
    with LEGEND_PATH.open() as f:
        data = json.load(f)
    return {zone["map_legend_code"]: zone for zone in data["zones"]}


def point_grid(geom) -> list[tuple[float, float]]:
    minx, miny, maxx, maxy = geom.bounds
    width = maxx - minx
    height = maxy - miny
    area = geom.area
    if width <= 0 or height <= 0 or area <= 0:
        p = geom.representative_point()
        return [(p.x, p.y)]

    inset = min(width, height) * 0.12
    sample_geom = geom.buffer(-inset)
    if sample_geom.is_empty:
        sample_geom = geom.buffer(-min(width, height) * 0.04)
    if sample_geom.is_empty:
        sample_geom = geom

    axis = MIN_GRID_AXIS
    if area > 1000:
        axis = 5
    if area > 8000:
        axis = MAX_GRID_AXIS

    points: list[tuple[float, float]] = []
    rep = sample_geom.representative_point()
    points.append((rep.x, rep.y))

    sx0, sy0, sx1, sy1 = sample_geom.bounds
    for ix in range(axis):
        x = sx0 + (ix + 0.5) * (sx1 - sx0) / axis
        for iy in range(axis):
            y = sy0 + (iy + 0.5) * (sy1 - sy0) / axis
            point = Point(x, y)
            if sample_geom.contains(point):
                points.append((x, y))
            if len(points) >= MAX_SAMPLES:
                return points
    return points


def hex_rgb(rgb: tuple[float, float, float] | tuple[int, int, int]) -> str:
    r, g, b = (int(round(v)) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def usable_rgb(sample: np.ndarray) -> tuple[int, int, int] | None:
    if sample.shape[0] >= 4 and sample[3] == 0:
        return None
    rgb = tuple(int(v) for v in sample[:3])
    if min(rgb) >= NEAR_WHITE_THRESHOLD:
        return None
    if max(rgb) <= NEAR_BLACK_THRESHOLD:
        return None
    return rgb


def nearest_class(rgb: tuple[int, int, int]) -> tuple[RasterClass | None, float]:
    arr = np.array(rgb, dtype=float)
    best_class: RasterClass | None = None
    best_distance = math.inf
    for raster_class in RASTER_CLASSES:
        dist = float(np.linalg.norm(arr - np.array(raster_class.rgb, dtype=float)))
        if dist < best_distance:
            best_class = raster_class
            best_distance = dist
    if best_class is None or best_distance > best_class.threshold:
        return None, best_distance
    return best_class, best_distance


def classify_samples(samples: list[np.ndarray], lookup: dict[str, dict]) -> dict:
    usable: list[tuple[int, int, int]] = []
    class_votes: Counter[str] = Counter()
    distances: dict[str, list[float]] = {}
    ambiguous_groups: Counter[str] = Counter()
    styles: Counter[str] = Counter()

    for sample in samples:
        rgb = usable_rgb(sample)
        if rgb is None:
            continue
        usable.append(rgb)
        raster_class, distance = nearest_class(rgb)
        if raster_class is None:
            continue
        class_votes[raster_class.map_legend_code] += 1
        distances.setdefault(raster_class.map_legend_code, []).append(distance)
        styles[raster_class.style] += 1
        if raster_class.ambiguous_group:
            ambiguous_groups[raster_class.ambiguous_group] += 1

    if not usable or not class_votes:
        return {
            "map_legend_code_guess": None,
            "zoning_code_guess": None,
            "final_class_code_guess": None,
            "zone_name_guess": None,
            "sample_count": len(samples),
            "matched_sample_count": 0,
            "sample_match_fraction": None,
            "mean_rgb": hex_rgb((255, 255, 255)),
            "dominant_rgb": None,
            "rgb_distance": None,
            "pattern_detected": False,
            "ambiguous_group": None,
            "assignment_method": "draft_context_assist",
            "confidence": "low",
            "review_status": "needs_review",
            "review_priority": 10,
        }

    winner, matched = class_votes.most_common(1)[0]
    match_fraction = matched / max(1, len(usable))
    mean_rgb = tuple(float(v) for v in np.array(usable, dtype=float).mean(axis=0))
    dominant_rgb = Counter(usable).most_common(1)[0][0]
    rgb_distance = float(np.mean(distances[winner]))
    winner_class = next(item for item in RASTER_CLASSES if item.map_legend_code == winner)
    pattern_detected = winner_class.style == "pattern" or styles["pattern"] >= styles["solid"]
    ambiguous_group = ambiguous_groups.most_common(1)[0][0] if ambiguous_groups else None

    # Same-colour legend groups cannot be resolved by colour samples alone.
    if ambiguous_group:
        map_legend_code = None
        lookup_row = None
    else:
        map_legend_code = winner
        lookup_row = lookup.get(winner)

    confidence = "low"
    if map_legend_code and not pattern_detected and match_fraction >= 0.72 and rgb_distance <= 45:
        confidence = "high"
    elif map_legend_code and not pattern_detected and match_fraction >= 0.48 and rgb_distance <= 60:
        confidence = "medium"

    review_status = "auto_assigned" if confidence in {"high", "medium"} else "needs_review"
    review_priority = 80
    if review_status == "needs_review":
        review_priority = 20 if ambiguous_group or pattern_detected else 30
    if lookup_row and lookup_row["is_pseudo_zone"]:
        confidence = "low"
        review_status = "needs_review"
        review_priority = 15
        pattern_detected = False
        ambiguous_group = "PSEUDO_ZONE"

    return {
        "map_legend_code_guess": map_legend_code,
        "zoning_code_guess": lookup_row["zoning_code"] if lookup_row else None,
        "final_class_code_guess": lookup_row["final_class_code"] if lookup_row else None,
        "zone_name_guess": lookup_row["zone_name"] if lookup_row else None,
        "sample_count": len(samples),
        "matched_sample_count": matched,
        "sample_match_fraction": match_fraction,
        "mean_rgb": hex_rgb(mean_rgb),
        "dominant_rgb": hex_rgb(dominant_rgb),
        "rgb_distance": rgb_distance,
        "pattern_detected": pattern_detected,
        "ambiguous_group": ambiguous_group,
        "assignment_method": "legacy_or_pseudo_zone" if lookup_row and lookup_row["is_pseudo_zone"] else "pattern_raster_sample" if pattern_detected else "solid_fill_raster_sample",
        "confidence": confidence,
        "review_status": review_status,
        "review_priority": review_priority,
    }


def read_parcels() -> gpd.GeoDataFrame:
    engine = create_engine(database_url())
    sql = f'select fid, geom from public."{REVIEW_TABLE}" order by fid'
    return gpd.read_postgis(sql, engine, geom_col="geom")


def update_rows(rows: list[dict]) -> None:
    sql = f"""
update public."{REVIEW_TABLE}"
set
    map_legend_code_guess = %(map_legend_code_guess)s,
    zoning_code_guess = %(zoning_code_guess)s,
    final_class_code_guess = %(final_class_code_guess)s,
    zone_name_guess = %(zone_name_guess)s,
    sample_count = %(sample_count)s,
    matched_sample_count = %(matched_sample_count)s,
    sample_match_fraction = %(sample_match_fraction)s,
    mean_rgb = %(mean_rgb)s,
    dominant_rgb = %(dominant_rgb)s,
    rgb_distance = %(rgb_distance)s,
    pattern_detected = %(pattern_detected)s,
    ambiguous_group = %(ambiguous_group)s,
    assignment_method = %(assignment_method)s,
    confidence = %(confidence)s,
    review_status = %(review_status)s,
    review_priority = %(review_priority)s,
    updated_at = now()
where fid = %(fid)s;
"""
    with psycopg.connect(database_url("psycopg")) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()


def main() -> None:
    lookup = load_lookup()
    parcels = read_parcels()
    rows: list[dict] = []

    with rasterio.open(RASTER_PATH) as raster:
        for row in parcels.itertuples(index=False):
            points = point_grid(row.geom)
            samples = list(raster.sample(points))
            result = classify_samples(samples, lookup)
            result["fid"] = int(row.fid)
            rows.append(result)

    update_rows(rows)

    counts = Counter((row["review_status"], row["confidence"], row["assignment_method"]) for row in rows)
    print(f"updated {len(rows)} parcels")
    for key, count in sorted(counts.items()):
        print((*key, count))


if __name__ == "__main__":
    main()
