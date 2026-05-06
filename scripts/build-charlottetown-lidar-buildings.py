#!/usr/bin/env python3
"""Build public."CHTWN_Buildings" with LiDAR-derived height attributes."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import laspy
import numpy as np
from shapely import contains_xy, from_wkb
from shapely.geometry import box
from shapely.ops import transform


ROOT = Path(__file__).resolve().parents[1]
LIDAR_DIR = ROOT / "maps" / "pei" / "lidar"
REPORT_DIR = ROOT / "data" / "spatial" / "charlottetown" / "lidar-building-heights"
METHOD = "roof_p95_minus_ground_p05_v1"
SOURCE_SRID = 4326
LIDAR_SRID = 2961
PSQL_CONTAINER = os.environ.get("POSTGIS_CONTAINER", "mdopendata-postgis")
PSQL_USER = os.environ.get("PGUSER", "mdopendata")
PSQL_DB = os.environ.get("PGDATABASE", "mdopendata")


@dataclass
class Building:
    source_id: int
    geom: object
    geom_ground_buffer_3m: object
    geom_ground_buffer_10m: object
    bounds: tuple[float, float, float, float]
    area_m2: float
    roof_z: list[np.ndarray] = field(default_factory=list)
    ground_z: list[np.ndarray] = field(default_factory=list)
    ground_z_fallback: list[np.ndarray] = field(default_factory=list)
    source_tiles: set[str] = field(default_factory=set)
    roof_point_count: int = 0
    ground_point_count: int = 0


def run_psql(sql: str, *, capture: bool = False) -> str:
    cmd = [
        "docker",
        "exec",
        "-i",
        PSQL_CONTAINER,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        PSQL_USER,
        "-d",
        PSQL_DB,
    ]
    proc = subprocess.run(
        cmd,
        input=sql,
        text=True,
        capture_output=capture,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"psql failed: {message}")
    return proc.stdout if capture else ""


def export_buildings(limit: int | None = None) -> list[Building]:
    limit_clause = f"limit {int(limit)}" if limit else ""
    query = (
        "select id, "
        f"encode(st_asewkb(st_transform(geom, {LIDAR_SRID})), 'hex') as geom_wkb, "
        f"st_area(st_transform(geom, {LIDAR_SRID})) as area_m2 "
        'from public."CHTWN_OSM_Buildings" '
        f"order by id {limit_clause}"
    )
    sql = f"\\copy ({query}) to stdout with csv header\n"
    rows = run_psql(sql, capture=True)
    buildings: list[Building] = []
    reader = csv.DictReader(rows.splitlines())
    for row in reader:
        geom = from_wkb(bytes.fromhex(row["geom_wkb"]))
        if geom.is_empty:
            continue
        buildings.append(
            Building(
                source_id=int(row["id"]),
                geom=geom,
                geom_ground_buffer_3m=geom.buffer(3.0),
                geom_ground_buffer_10m=geom.buffer(10.0),
                bounds=geom.bounds,
                area_m2=float(row["area_m2"]),
            )
        )
    return buildings


def tile_origin(path: Path) -> tuple[float, float] | None:
    match = re.match(r"pei_2020_(\d+)_(\d+)\.copc\.laz$", path.name)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def candidate_buildings_for_tile(buildings: list[Building], path: Path) -> list[Building]:
    with laspy.open(path) as reader:
        mins = reader.header.mins
        maxs = reader.header.maxs
    tile_box = box(float(mins[0]), float(mins[1]), float(maxs[0]), float(maxs[1]))
    return [b for b in buildings if tile_box.intersects(box(*b.bounds))]


def sorted_points_for_tile(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with laspy.open(path) as reader:
        las = reader.read()
    x = np.asarray(las.x)
    y = np.asarray(las.y)
    z = np.asarray(las.z)
    classification = np.asarray(las.classification)
    order = np.argsort(x, kind="mergesort")
    return x[order], y[order], z[order], classification[order]


def range_by_bbox(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    classification: np.ndarray,
    bounds: tuple[float, float, float, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    minx, miny, maxx, maxy = bounds
    lo = int(np.searchsorted(x, minx, side="left"))
    hi = int(np.searchsorted(x, maxx, side="right"))
    if hi <= lo:
        empty = np.array([], dtype=float)
        empty_i = np.array([], dtype=classification.dtype)
        return empty, empty, empty, empty_i
    yy = y[lo:hi]
    mask = (yy >= miny) & (yy <= maxy)
    return x[lo:hi][mask], yy[mask], z[lo:hi][mask], classification[lo:hi][mask]


def sample_tile(path: Path, buildings: list[Building]) -> None:
    candidates = candidate_buildings_for_tile(buildings, path)
    if not candidates:
        return

    print(f"{path.name}: {len(candidates)} candidate buildings", flush=True)
    x, y, z, classification = sorted_points_for_tile(path)

    for building in candidates:
        bx, by, bz, bc = range_by_bbox(x, y, z, classification, building.bounds)
        if bx.size:
            inside = contains_xy(building.geom, bx, by)
            if np.any(inside):
                roof_mask = inside & (bc != 2) & (bc != 7) & (bc != 18)
                if np.any(roof_mask):
                    roof = bz[roof_mask]
                    building.roof_z.append(roof)
                    building.roof_point_count += int(roof.size)
                    building.source_tiles.add(path.name)

        gx, gy, gz, gc = range_by_bbox(x, y, z, classification, building.geom_ground_buffer_3m.bounds)
        if gx.size:
            ground_mask = (gc == 2) & contains_xy(building.geom_ground_buffer_3m, gx, gy)
            if np.any(ground_mask):
                ground = gz[ground_mask]
                building.ground_z.append(ground)
                building.ground_point_count += int(ground.size)
                building.source_tiles.add(path.name)
                continue

        gx, gy, gz, gc = range_by_bbox(x, y, z, classification, building.geom_ground_buffer_10m.bounds)
        if gx.size:
            ground_mask = (gc == 2) & contains_xy(building.geom_ground_buffer_10m, gx, gy)
            if np.any(ground_mask):
                ground = gz[ground_mask]
                building.ground_z_fallback.append(ground)
                building.ground_point_count += int(ground.size)
                building.source_tiles.add(path.name)


def q(values: Iterable[np.ndarray], percentile: float) -> float | None:
    arrays = [a for a in values if a.size]
    if not arrays:
        return None
    merged = np.concatenate(arrays)
    if not merged.size:
        return None
    return float(np.percentile(merged, percentile))


def confidence(building: Building, height: float | None, fallback_ground: bool) -> str:
    if height is None:
        return "needs_review"
    if height < 1.5 or height > 80:
        return "needs_review"
    if building.roof_point_count < 12 or building.ground_point_count < 5:
        return "low"
    if fallback_ground or building.roof_point_count < 40 or building.ground_point_count < 15:
        return "medium"
    return "high"


def status(building: Building, height: float | None) -> str:
    if height is not None:
        return "derived"
    if building.roof_point_count == 0 and building.ground_point_count == 0:
        return "no_lidar_points"
    if building.roof_point_count == 0:
        return "no_roof_points"
    if building.ground_point_count == 0:
        return "no_ground_points"
    return "invalid_height"


def derived_rows(buildings: list[Building]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for b in buildings:
        roof_p95 = q(b.roof_z, 95)
        roof_p98 = q(b.roof_z, 98)
        roof_p90 = q(b.roof_z, 90)
        ground_sources = b.ground_z if b.ground_z else b.ground_z_fallback
        fallback_ground = not b.ground_z and bool(b.ground_z_fallback)
        ground_p05 = q(ground_sources, 5)
        ground_p50 = q(ground_sources, 50)
        height = None
        if roof_p95 is not None and ground_p05 is not None:
            height = round(max(0.0, roof_p95 - ground_p05), 2)
        provenance = {
            "source_lidar_dir": "maps/pei/lidar",
            "lidar_srid": LIDAR_SRID,
            "source_building_table": 'public."CHTWN_OSM_Buildings"',
            "height_definition": "roof_p95_m - ground_p05_m",
            "roof_p90_m": round(roof_p90, 3) if roof_p90 is not None else None,
            "roof_p98_m": round(roof_p98, 3) if roof_p98 is not None else None,
            "ground_p50_m": round(ground_p50, 3) if ground_p50 is not None else None,
            "ground_buffer_m": 10 if fallback_ground else 3,
            "area_m2": round(b.area_m2, 3),
        }
        rows.append(
            {
                "source_id": b.source_id,
                "height_lidar_m": height,
                "height_lidar_method": METHOD,
                "height_lidar_confidence": confidence(b, height, fallback_ground),
                "height_lidar_status": status(b, height),
                "height_lidar_source_tiles": sorted(b.source_tiles),
                "height_lidar_point_count": b.roof_point_count + b.ground_point_count,
                "height_lidar_roof_m": round(roof_p95, 3) if roof_p95 is not None else None,
                "height_lidar_ground_m": round(ground_p05, 3) if ground_p05 is not None else None,
                "height_lidar_updated_at": datetime.now(timezone.utc).isoformat(),
                "height_lidar_provenance": provenance,
            }
        )
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_id",
        "height_lidar_m",
        "height_lidar_method",
        "height_lidar_confidence",
        "height_lidar_status",
        "height_lidar_source_tiles",
        "height_lidar_point_count",
        "height_lidar_roof_m",
        "height_lidar_ground_m",
        "height_lidar_updated_at",
        "height_lidar_provenance",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            encoded = dict(row)
            encoded["height_lidar_source_tiles"] = "{" + ",".join(row["height_lidar_source_tiles"]) + "}"
            encoded["height_lidar_provenance"] = json.dumps(row["height_lidar_provenance"], sort_keys=True)
            writer.writerow(encoded)


def apply_to_database(csv_path: Path) -> None:
    container_csv = f"/tmp/{csv_path.name}"
    subprocess.run(["docker", "cp", str(csv_path), f"{PSQL_CONTAINER}:{container_csv}"], check=True)
    sql = f"""
drop table if exists public."CHTWN_Buildings";
create table public."CHTWN_Buildings" as
select
  id as source_osm_building_id,
  osm_type,
  osm_id,
  building,
  name,
  levels,
  source_tags,
  extracted_at,
  source_note,
  null::numeric as height_lidar_m,
  null::text as height_lidar_method,
  null::text as height_lidar_confidence,
  null::text as height_lidar_status,
  null::text[] as height_lidar_source_tiles,
  null::integer as height_lidar_point_count,
  null::numeric as height_lidar_ground_m,
  null::numeric as height_lidar_roof_m,
  null::timestamptz as height_lidar_updated_at,
  null::jsonb as height_lidar_provenance,
  geom
from public."CHTWN_OSM_Buildings";

create temporary table chtwn_lidar_height_stage (
  source_id integer primary key,
  height_lidar_m numeric,
  height_lidar_method text,
  height_lidar_confidence text,
  height_lidar_status text,
  height_lidar_source_tiles text[],
  height_lidar_point_count integer,
  height_lidar_roof_m numeric,
  height_lidar_ground_m numeric,
  height_lidar_updated_at timestamptz,
  height_lidar_provenance jsonb
);

\\copy chtwn_lidar_height_stage from '{container_csv}' with csv header

update public."CHTWN_Buildings" b
set
  height_lidar_m = s.height_lidar_m,
  height_lidar_method = s.height_lidar_method,
  height_lidar_confidence = s.height_lidar_confidence,
  height_lidar_status = s.height_lidar_status,
  height_lidar_source_tiles = s.height_lidar_source_tiles,
  height_lidar_point_count = s.height_lidar_point_count,
  height_lidar_ground_m = s.height_lidar_ground_m,
  height_lidar_roof_m = s.height_lidar_roof_m,
  height_lidar_updated_at = s.height_lidar_updated_at,
  height_lidar_provenance = s.height_lidar_provenance
from chtwn_lidar_height_stage s
where b.source_osm_building_id = s.source_id;

alter table public."CHTWN_Buildings"
  add primary key (source_osm_building_id);

create index "CHTWN_Buildings_geom_idx"
  on public."CHTWN_Buildings"
  using gist (geom);

create index "CHTWN_Buildings_height_confidence_idx"
  on public."CHTWN_Buildings" (height_lidar_confidence, height_lidar_status);

analyze public."CHTWN_Buildings";
"""
    run_psql(sql)


def write_summary(rows: list[dict[str, object]], path: Path) -> None:
    def count_where(key: str, value: str) -> int:
        return sum(1 for row in rows if row[key] == value)

    heights = [float(row["height_lidar_m"]) for row in rows if row["height_lidar_m"] is not None]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": METHOD,
        "building_count": len(rows),
        "derived_height_count": len(heights),
        "null_height_count": len(rows) - len(heights),
        "confidence_counts": {
            "high": count_where("height_lidar_confidence", "high"),
            "medium": count_where("height_lidar_confidence", "medium"),
            "low": count_where("height_lidar_confidence", "low"),
            "needs_review": count_where("height_lidar_confidence", "needs_review"),
        },
        "status_counts": {},
        "height_m": {
            "min": round(float(np.min(heights)), 2) if heights else None,
            "p50": round(float(np.percentile(heights, 50)), 2) if heights else None,
            "p95": round(float(np.percentile(heights, 95)), 2) if heights else None,
            "max": round(float(np.max(heights)), 2) if heights else None,
        },
    }
    statuses = sorted({str(row["height_lidar_status"]) for row in rows})
    summary["status_counts"] = {s: count_where("height_lidar_status", s) for s in statuses}
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit buildings for smoke tests.")
    parser.add_argument("--dry-run", action="store_true", help="Generate CSV and summary without creating the database table.")
    parser.add_argument("--max-tiles", type=int, default=None, help="Limit LiDAR tiles for smoke tests.")
    args = parser.parse_args()

    tiles = sorted(LIDAR_DIR.glob("*.copc.laz"))
    if args.max_tiles:
        tiles = tiles[: args.max_tiles]
    if not tiles:
        raise RuntimeError(f"No COPC LAZ tiles found under {LIDAR_DIR}")

    buildings = export_buildings(args.limit)
    print(f"Loaded {len(buildings)} building footprints", flush=True)
    for tile in tiles:
        sample_tile(tile, buildings)

    rows = derived_rows(buildings)
    suffix = "sample" if args.limit or args.max_tiles else "full"
    csv_path = REPORT_DIR / f"chtwn-building-lidar-heights-{suffix}.csv"
    summary_path = REPORT_DIR / f"chtwn-building-lidar-heights-{suffix}.summary.json"
    write_csv(rows, csv_path)
    write_summary(rows, summary_path)
    if args.dry_run:
        print(f"Dry run complete: {csv_path}", flush=True)
        return 0
    apply_to_database(csv_path)
    print('Created public."CHTWN_Buildings"', flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
