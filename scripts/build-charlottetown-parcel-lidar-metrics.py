#!/usr/bin/env python3
"""Build public."CHTWN_Parcel_LiDAR_Metrics" from parcels, buildings, and LiDAR."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import laspy
import numpy as np
from shapely import STRtree, from_wkb, points
from shapely.geometry import box

csv.field_size_limit(1024 * 1024 * 1024)

ROOT = Path(__file__).resolve().parents[1]
LIDAR_DIR = ROOT / "maps" / "pei" / "lidar"
REPORT_DIR = ROOT / "data" / "spatial" / "charlottetown" / "lidar-parcel-metrics"
METHOD = "parcel_lidar_metrics_direct_points_v1"
LIDAR_SRID = 2961
PSQL_CONTAINER = os.environ.get("POSTGIS_CONTAINER", "mdopendata-postgis")
PSQL_USER = os.environ.get("PGUSER", "mdopendata")
PSQL_DB = os.environ.get("PGDATABASE", "mdopendata")
MAX_SAMPLES_PER_CLASS = 20000
MAX_POINTS_PER_TILE_DEFAULT = 25000


@dataclass
class Parcel:
    fid: int
    geom: object
    bounds: tuple[float, float, float, float]
    area_m2: float
    lidar_source_tiles: set[str] = field(default_factory=set)
    ground_z: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))
    elevated_z: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))
    ground_point_count: int = 0
    elevated_point_count: int = 0


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
    proc = subprocess.run(cmd, input=sql, text=True, capture_output=capture, check=False)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"psql failed: {message}")
    return proc.stdout if capture else ""


def export_parcels(limit: int | None = None) -> list[Parcel]:
    limit_clause = f"limit {int(limit)}" if limit else ""
    query = (
        "select fid, "
        f"encode(st_asewkb(st_transform(geom, {LIDAR_SRID})), 'hex') as geom_wkb, "
        f"st_area(st_transform(geom, {LIDAR_SRID})) as area_m2 "
        'from public."CHTWN_Parcel_Map" '
        f"order by fid {limit_clause}"
    )
    rows = run_psql(f"\\copy ({query}) to stdout with csv header\n", capture=True)
    parcels: list[Parcel] = []
    for row in csv.DictReader(rows.splitlines()):
        geom = from_wkb(bytes.fromhex(row["geom_wkb"]))
        if geom.is_empty:
            continue
        parcels.append(Parcel(fid=int(row["fid"]), geom=geom, bounds=geom.bounds, area_m2=float(row["area_m2"])))
    return parcels


def append_sample(existing: np.ndarray, values: np.ndarray, max_samples: int = MAX_SAMPLES_PER_CLASS) -> np.ndarray:
    if values.size == 0:
        return existing
    values = values.astype(np.float32, copy=False)
    if existing.size == 0 and values.size <= max_samples:
        return values.copy()
    combined = np.concatenate([existing, values])
    if combined.size <= max_samples:
        return combined
    indexes = np.linspace(0, combined.size - 1, max_samples, dtype=np.int64)
    return combined[indexes]


def sorted_points_for_tile(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with laspy.open(path) as reader:
        las = reader.read()
    x = np.asarray(las.x)
    y = np.asarray(las.y)
    z = np.asarray(las.z)
    classification = np.asarray(las.classification)
    order = np.argsort(x, kind="mergesort")
    return x[order], y[order], z[order], classification[order]


def sample_tile(
    path: Path,
    parcels: list[Parcel],
    tree: STRtree,
    parcel_by_tree_index: dict[int, Parcel],
    max_points_per_tile: int,
) -> None:
    with laspy.open(path) as reader:
        point_count = reader.header.point_count
        las = reader.read()
    stride = max(1, int(np.ceil(point_count / max_points_per_tile)))
    x = np.asarray(las.x)[::stride]
    y = np.asarray(las.y)[::stride]
    z = np.asarray(las.z)[::stride]
    classification = np.asarray(las.classification)[::stride]
    if x.size == 0:
        return

    point_geoms = points(x, y)
    pairs = tree.query(point_geoms, predicate="within")
    if pairs.size == 0:
        return
    point_indexes = pairs[0]
    parcel_indexes = pairs[1]
    print(f"{path.name}: {x.size} sampled points, {len(np.unique(parcel_indexes))} parcels hit", flush=True)

    for parcel_index in np.unique(parcel_indexes):
        parcel = parcel_by_tree_index[int(parcel_index)]
        point_mask = point_indexes[parcel_indexes == parcel_index]
        if point_mask.size == 0:
            continue
        parcel.lidar_source_tiles.add(path.name)
        pc = classification[point_mask]
        pz = z[point_mask]
        ground = pz[pc == 2]
        if ground.size:
            parcel.ground_point_count += int(ground.size * stride)
            parcel.ground_z = append_sample(parcel.ground_z, ground)
        elevated = pz[(pc != 2) & (pc != 7) & (pc != 18)]
        if elevated.size:
            parcel.elevated_point_count += int(elevated.size * stride)
            parcel.elevated_z = append_sample(parcel.elevated_z, elevated)


def percentile(values: np.ndarray, p: float) -> float | None:
    if values.size == 0:
        return None
    return float(np.percentile(values, p))


def rounded(value: float | None, places: int = 3) -> float | None:
    return round(float(value), places) if value is not None else None


def confidence(parcel: Parcel, flags: list[str]) -> str:
    if "no_lidar_points" in flags or "no_ground_points" in flags:
        return "needs_review"
    if "tiny_parcel" in flags or "low_terrain_sample" in flags:
        return "low"
    if "canopy_building_overlap_uncertain" in flags:
        return "medium"
    return "high"


def lidar_rows(parcels: list[Parcel], max_points_per_tile: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    now = datetime.now(timezone.utc).isoformat()
    for parcel in parcels:
        flags: list[str] = []
        if parcel.area_m2 < 20:
            flags.append("tiny_parcel")
        if parcel.ground_point_count == 0 and parcel.elevated_point_count == 0:
            flags.append("no_lidar_points")
        if parcel.ground_point_count == 0:
            flags.append("no_ground_points")
        elif parcel.ground_point_count < 20:
            flags.append("low_terrain_sample")

        ground_min = percentile(parcel.ground_z, 0)
        ground_p50 = percentile(parcel.ground_z, 50)
        ground_max = percentile(parcel.ground_z, 100)
        ground_relief = (ground_max - ground_min) if ground_min is not None and ground_max is not None else None

        canopy_heights = np.array([], dtype=np.float32)
        if ground_p50 is not None and parcel.elevated_z.size:
            canopy_heights = parcel.elevated_z - ground_p50
            canopy_heights = canopy_heights[canopy_heights > 0]
        if parcel.elevated_point_count > 0:
            flags.append("canopy_building_overlap_uncertain")

        canopy_cover_ratio_2m = None
        tall_canopy_cover_ratio_8m = None
        if canopy_heights.size:
            canopy_cover_ratio_2m = float(np.count_nonzero(canopy_heights >= 2.0) / canopy_heights.size)
            tall_canopy_cover_ratio_8m = float(np.count_nonzero(canopy_heights >= 8.0) / canopy_heights.size)

        provenance = {
            "source_lidar_dir": "maps/pei/lidar",
            "lidar_srid": LIDAR_SRID,
            "source_parcel_table": 'public."CHTWN_Parcel_Map"',
            "source_building_table": 'public."CHTWN_Buildings"',
            "terrain_method": "classified_ground_points_inside_parcel",
            "canopy_method": "non-ground_candidate_returns_minus_ground_p50; not building-masked in v1",
            "max_samples_per_class": MAX_SAMPLES_PER_CLASS,
            "max_points_per_tile": max_points_per_tile,
        }
        rows.append(
            {
                "source_parcel_fid": parcel.fid,
                "ground_elev_min_m": rounded(ground_min),
                "ground_elev_p50_m": rounded(ground_p50),
                "ground_elev_max_m": rounded(ground_max),
                "ground_relief_m": rounded(ground_relief),
                "slope_p50_deg": None,
                "slope_p95_deg": None,
                "low_point_elev_m": rounded(ground_min),
                "terrain_point_count": parcel.ground_point_count,
                "canopy_cover_ratio_2m": rounded(canopy_cover_ratio_2m, 5),
                "canopy_height_p50_m": rounded(percentile(canopy_heights, 50)),
                "canopy_height_p95_m": rounded(percentile(canopy_heights, 95)),
                "tall_canopy_cover_ratio_8m": rounded(tall_canopy_cover_ratio_8m, 5),
                "vegetation_point_count": parcel.elevated_point_count,
                "lidar_source_tiles": sorted(parcel.lidar_source_tiles),
                "lidar_metric_method": METHOD,
                "lidar_metric_confidence": confidence(parcel, flags),
                "lidar_metric_flags": flags,
                "lidar_metric_updated_at": now,
                "lidar_metric_provenance": provenance,
            }
        )
    return rows


def pg_array(values: list[str]) -> str:
    return "{" + ",".join(v.replace('"', '\\"') for v in values) + "}"


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_parcel_fid",
        "ground_elev_min_m",
        "ground_elev_p50_m",
        "ground_elev_max_m",
        "ground_relief_m",
        "slope_p50_deg",
        "slope_p95_deg",
        "low_point_elev_m",
        "terrain_point_count",
        "canopy_cover_ratio_2m",
        "canopy_height_p50_m",
        "canopy_height_p95_m",
        "tall_canopy_cover_ratio_8m",
        "vegetation_point_count",
        "lidar_source_tiles",
        "lidar_metric_method",
        "lidar_metric_confidence",
        "lidar_metric_flags",
        "lidar_metric_updated_at",
        "lidar_metric_provenance",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            encoded = dict(row)
            encoded["lidar_source_tiles"] = pg_array(row["lidar_source_tiles"])
            encoded["lidar_metric_flags"] = pg_array(row["lidar_metric_flags"])
            encoded["lidar_metric_provenance"] = json.dumps(row["lidar_metric_provenance"], sort_keys=True)
            writer.writerow(encoded)


def apply_to_database(csv_path: Path) -> None:
    container_csv = f"/tmp/{csv_path.name}"
    subprocess.run(["docker", "cp", str(csv_path), f"{PSQL_CONTAINER}:{container_csv}"], check=True)
    sql = f"""
drop table if exists public."CHTWN_Parcel_LiDAR_Metrics";

create temporary table chtwn_parcel_lidar_stage (
  source_parcel_fid bigint primary key,
  ground_elev_min_m numeric,
  ground_elev_p50_m numeric,
  ground_elev_max_m numeric,
  ground_relief_m numeric,
  slope_p50_deg numeric,
  slope_p95_deg numeric,
  low_point_elev_m numeric,
  terrain_point_count integer,
  canopy_cover_ratio_2m numeric,
  canopy_height_p50_m numeric,
  canopy_height_p95_m numeric,
  tall_canopy_cover_ratio_8m numeric,
  vegetation_point_count integer,
  lidar_source_tiles text[],
  lidar_metric_method text,
  lidar_metric_confidence text,
  lidar_metric_flags text[],
  lidar_metric_updated_at timestamptz,
  lidar_metric_provenance jsonb
);

\\copy chtwn_parcel_lidar_stage from '{container_csv}' with csv header

create temporary table chtwn_building_assignment as
with intersections as (
  select
    b.source_osm_building_id,
    p.fid as source_parcel_fid,
    st_area(st_intersection(st_transform(b.geom, 2954), p.geom)) as overlap_m2,
    st_area(st_transform(b.geom, 2954)) as building_area_m2,
    b.height_lidar_m,
    b.height_lidar_confidence
  from public."CHTWN_Buildings" b
  join public."CHTWN_Parcel_Map" p
    on st_intersects(st_transform(b.geom, 2954), p.geom)
  where not st_isempty(st_intersection(st_transform(b.geom, 2954), p.geom))
),
ranked as (
  select
    *,
    row_number() over (partition by source_osm_building_id order by overlap_m2 desc, source_parcel_fid) as rn,
    count(*) filter (where overlap_m2 / nullif(building_area_m2, 0) >= 0.10)
      over (partition by source_osm_building_id) as material_overlap_count
  from intersections
)
select * from ranked where rn = 1;

create temporary table chtwn_building_metrics as
select
  source_parcel_fid,
  count(*)::integer as building_count,
  round(sum(overlap_m2)::numeric, 3) as building_coverage_m2,
  max(height_lidar_m) as building_height_max_m,
  percentile_cont(0.5) within group (order by height_lidar_m)::numeric as building_height_p50_m,
  percentile_cont(0.95) within group (order by height_lidar_m)::numeric as building_height_p95_m,
  round(sum(overlap_m2 * height_lidar_m)::numeric, 3) as building_volume_proxy_m3,
  case
    when bool_or(height_lidar_confidence = 'needs_review') then 'needs_review'
    when bool_or(height_lidar_confidence = 'low') then 'low'
    when bool_or(height_lidar_confidence = 'medium') then 'medium'
    else 'high'
  end as building_height_confidence_min,
  count(*) filter (where height_lidar_confidence = 'needs_review')::integer as building_height_needs_review_count,
  count(*) filter (where material_overlap_count > 1)::integer as building_split_overlap_count
from chtwn_building_assignment
group by source_parcel_fid;

create table public."CHTWN_Parcel_LiDAR_Metrics" as
select
  p.fid as source_parcel_fid,
  p.parcel_candidate_id,
  p.source_map,
  p.method,
  p.area_m2 as parcel_area_m2,
  coalesce(bm.building_count, 0)::integer as building_count,
  coalesce(bm.building_coverage_m2, 0)::numeric as building_coverage_m2,
  case when p.area_m2 > 0 then round((coalesce(bm.building_coverage_m2, 0) / p.area_m2)::numeric, 6) end as building_coverage_ratio,
  bm.building_height_max_m,
  bm.building_height_p50_m,
  bm.building_height_p95_m,
  coalesce(bm.building_volume_proxy_m3, 0)::numeric as building_volume_proxy_m3,
  bm.building_height_confidence_min,
  coalesce(bm.building_height_needs_review_count, 0)::integer as building_height_needs_review_count,
  s.ground_elev_min_m,
  s.ground_elev_p50_m,
  s.ground_elev_max_m,
  s.ground_relief_m,
  s.slope_p50_deg,
  s.slope_p95_deg,
  s.low_point_elev_m,
  s.terrain_point_count,
  s.canopy_cover_ratio_2m,
  s.canopy_height_p50_m,
  s.canopy_height_p95_m,
  s.tall_canopy_cover_ratio_8m,
  s.vegetation_point_count,
  s.lidar_source_tiles,
  s.lidar_metric_method,
  case
    when coalesce(bm.building_split_overlap_count, 0) > 0 and s.lidar_metric_confidence = 'high' then 'medium'
    else s.lidar_metric_confidence
  end as lidar_metric_confidence,
  case
    when coalesce(bm.building_split_overlap_count, 0) > 0
      then array_append(coalesce(s.lidar_metric_flags, array[]::text[]), 'building_split_overlap')
    else s.lidar_metric_flags
  end as lidar_metric_flags,
  s.lidar_metric_updated_at,
  s.lidar_metric_provenance ||
    jsonb_build_object(
      'building_assignment_method', 'largest_parcel_overlap_v1',
      'building_split_overlap_count', coalesce(bm.building_split_overlap_count, 0)
    ) as lidar_metric_provenance,
  p.geom
from public."CHTWN_Parcel_Map" p
left join chtwn_parcel_lidar_stage s on s.source_parcel_fid = p.fid
left join chtwn_building_metrics bm on bm.source_parcel_fid = p.fid;

alter table public."CHTWN_Parcel_LiDAR_Metrics"
  add primary key (source_parcel_fid);

create index "CHTWN_Parcel_LiDAR_Metrics_geom_idx"
  on public."CHTWN_Parcel_LiDAR_Metrics"
  using gist (geom);

create index "CHTWN_Parcel_LiDAR_Metrics_confidence_idx"
  on public."CHTWN_Parcel_LiDAR_Metrics" (lidar_metric_confidence);

analyze public."CHTWN_Parcel_LiDAR_Metrics";
"""
    run_psql(sql)


def write_summary(rows: list[dict[str, object]], path: Path) -> None:
    def count_where(key: str, value: str) -> int:
        return sum(1 for row in rows if row[key] == value)

    ground = [float(row["ground_elev_p50_m"]) for row in rows if row["ground_elev_p50_m"] is not None]
    canopy = [float(row["canopy_cover_ratio_2m"]) for row in rows if row["canopy_cover_ratio_2m"] is not None]
    flags: dict[str, int] = {}
    for row in rows:
        for flag in row["lidar_metric_flags"]:
            flags[flag] = flags.get(flag, 0) + 1
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": METHOD,
        "parcel_count": len(rows),
        "confidence_counts": {
            "high": count_where("lidar_metric_confidence", "high"),
            "medium": count_where("lidar_metric_confidence", "medium"),
            "low": count_where("lidar_metric_confidence", "low"),
            "needs_review": count_where("lidar_metric_confidence", "needs_review"),
        },
        "flag_counts": dict(sorted(flags.items())),
        "terrain_ground_p50_m": {
            "min": round(float(np.min(ground)), 2) if ground else None,
            "p50": round(float(np.percentile(ground, 50)), 2) if ground else None,
            "max": round(float(np.max(ground)), 2) if ground else None,
        },
        "canopy_cover_ratio_2m": {
            "p50": round(float(np.percentile(canopy, 50)), 4) if canopy else None,
            "p95": round(float(np.percentile(canopy, 95)), 4) if canopy else None,
        },
    }
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit parcels for smoke tests.")
    parser.add_argument("--max-tiles", type=int, default=None, help="Limit LiDAR tiles for smoke tests.")
    parser.add_argument("--max-points-per-tile", type=int, default=MAX_POINTS_PER_TILE_DEFAULT, help="Maximum LiDAR points sampled from each tile.")
    parser.add_argument("--dry-run", action="store_true", help="Write CSV/summary without creating database table.")
    args = parser.parse_args()

    parcels = export_parcels(args.limit)
    print(f"Loaded {len(parcels)} parcels", flush=True)
    tree = STRtree([p.geom for p in parcels])
    parcel_by_tree_index = {index: parcel for index, parcel in enumerate(parcels)}

    tiles = sorted(LIDAR_DIR.glob("*.copc.laz"))
    if args.max_tiles:
        tiles = tiles[: args.max_tiles]
    if not tiles:
        raise RuntimeError(f"No COPC LAZ tiles found under {LIDAR_DIR}")

    for tile in tiles:
        sample_tile(tile, parcels, tree, parcel_by_tree_index, args.max_points_per_tile)

    rows = lidar_rows(parcels, args.max_points_per_tile)
    suffix = "sample" if args.limit or args.max_tiles else "full"
    csv_path = REPORT_DIR / f"chtwn-parcel-lidar-metrics-{suffix}.csv"
    summary_path = REPORT_DIR / f"chtwn-parcel-lidar-metrics-{suffix}.summary.json"
    write_csv(rows, csv_path)
    write_summary(rows, summary_path)
    if args.dry_run:
        print(f"Dry run complete: {csv_path}", flush=True)
        return 0
    apply_to_database(csv_path)
    print('Created public."CHTWN_Parcel_LiDAR_Metrics"', flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
