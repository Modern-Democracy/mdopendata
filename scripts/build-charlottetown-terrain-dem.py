#!/usr/bin/env python3
"""Build a Charlottetown bare-earth terrain DEM from PEI COPC LiDAR tiles."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union


ROOT = Path(__file__).resolve().parents[1]
LIDAR_DIR = ROOT / "maps" / "pei" / "lidar"
BOUNDARY_PATH = ROOT / "maps" / "pei" / "CHTWN_Municipal_Boundary.geojson"
OUT_DIR = ROOT / "data" / "spatial" / "charlottetown" / "lidar-terrain-dem"
METHOD = "pdal_ground_idw_epsg2961_1m_v1"
SOURCE_SRID = 4326
LIDAR_SRID = 2961
NODATA = -9999.0
GROUND_EXPRESSION = "Classification == 2 && Withheld == 0 && Synthetic == 0 && KeyPoint == 0 && Overlap == 0"


@dataclass(frozen=True)
class Tile:
    path: Path
    bounds: tuple[float, float, float, float]
    point_count: int
    srs_code: int | None
    vertical_srs: str


def tool_env() -> dict[str, str]:
    env = os.environ.copy()
    candidates = [
        Path(r"C:\Program Files\GDAL"),
        Path(r"C:\Program Files\QGIS 4.0.1\bin"),
    ]
    prepend = [str(path) for path in candidates if path.exists()]
    if prepend:
        env["PATH"] = os.pathsep.join(prepend + [env.get("PATH", "")])
    env.setdefault("GDAL_DRIVER_PATH", r"C:\Program Files\GDAL\gdalplugins")
    env.setdefault("GDAL_DATA", r"C:\Program Files\GDAL\gdal-data")
    env.setdefault("PROJ_LIB", r"C:\Program Files\GDAL\projlib")
    return env


def command_env(command: str) -> dict[str, str]:
    env = tool_env()
    if command == "pdal":
        env.pop("GDAL_DRIVER_PATH", None)
    return env


def run(cmd: list[str], *, capture: bool = False) -> str:
    env = command_env(cmd[0])
    executable = shutil.which(cmd[0], path=env.get("PATH"))
    if executable:
        cmd = [executable, *cmd[1:]]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=capture,
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{message}")
    return proc.stdout if capture else ""


def tool_version(command: str) -> str:
    out = run([command, "--version"], capture=True)
    return " ".join(line.strip() for line in out.splitlines() if line.strip())


def load_boundary(buffer_m: float) -> Any:
    payload = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    geoms = [shape(feature["geometry"]) for feature in payload.get("features", []) if feature.get("geometry")]
    if not geoms:
        raise RuntimeError(f"No geometries found in {BOUNDARY_PATH}")
    boundary = unary_union(geoms)
    transformer = Transformer.from_crs(SOURCE_SRID, LIDAR_SRID, always_xy=True)
    projected = transform(transformer.transform, boundary)
    return projected.buffer(buffer_m)


def tile_metadata(path: Path) -> Tile:
    payload = json.loads(run(["pdal", "info", "--summary", str(path)], capture=True))
    summary = payload["summary"]
    dimensions = {name.strip().lower() for name in summary.get("dimensions", "").split(",")}
    if "classification" not in dimensions:
        raise RuntimeError(f"Tile lacks Classification dimension: {path}")
    bounds = summary["bounds"]
    srs_json = summary.get("srs", {}).get("json", {})
    srs_code = srs_json.get("id", {}).get("code")
    return Tile(
        path=path,
        bounds=(float(bounds["minx"]), float(bounds["miny"]), float(bounds["maxx"]), float(bounds["maxy"])),
        point_count=int(summary["num_points"]),
        srs_code=int(srs_code) if srs_code is not None else None,
        vertical_srs=summary.get("srs", {}).get("vertical", "") or "",
    )


def select_tiles(boundary: Any, max_tiles: int | None = None) -> list[Tile]:
    tiles: list[Tile] = []
    for path in sorted(LIDAR_DIR.glob("*.copc.laz")):
        tile = tile_metadata(path)
        if boundary.intersects(box(*tile.bounds)):
            tiles.append(tile)
    if max_tiles is not None:
        tiles = tiles[:max_tiles]
    if not tiles:
        raise RuntimeError(f"No LiDAR tiles intersect {BOUNDARY_PATH}")
    return tiles


def validate_tile_crs(tiles: list[Tile]) -> None:
    invalid = [tile.path.name for tile in tiles if tile.srs_code != LIDAR_SRID]
    if invalid:
        raise RuntimeError(f"Expected EPSG:{LIDAR_SRID}; invalid tile CRS metadata: {invalid[:10]}")


def validate_ground_class(tile: Tile) -> dict[str, Any]:
    stats = json.loads(
        run(
            [
                "pdal",
                "info",
                "--stats",
                "--dimensions",
                "Classification",
                str(tile.path),
            ],
            capture=True,
        )
    )
    stat = stats.get("stats", {}).get("statistic", [{}])[0]
    min_class = int(stat.get("minimum", -1))
    max_class = int(stat.get("maximum", -1))
    if min_class > 2 or max_class < 2:
        raise RuntimeError(f"Classification 2 ground points not present in sampled tile {tile.path.name}")
    return {"tile": tile.path.name, "minimum": min_class, "maximum": max_class, "count": int(stat.get("count", 0))}


def write_pdal_pipeline(tile: Tile, output_tif: Path, pipeline_path: Path, resolution: float) -> None:
    pipeline = [
        {"type": "readers.copc", "filename": str(tile.path)},
        {"type": "filters.expression", "expression": GROUND_EXPRESSION},
        {
            "type": "writers.gdal",
            "filename": str(output_tif),
            "resolution": resolution,
            "output_type": "idw",
            "gdaldriver": "GTiff",
            "nodata": NODATA,
        },
    ]
    pipeline_path.write_text(json.dumps(pipeline, indent=2) + "\n", encoding="utf-8")


def build_tile_dem(tile: Tile, work_dir: Path, resolution: float, dry_run: bool) -> Path:
    output_tif = work_dir / f"{tile.path.stem}.ground-dem.tif"
    pipeline_path = work_dir / f"{tile.path.stem}.ground-dem.pipeline.json"
    write_pdal_pipeline(tile, output_tif, pipeline_path, resolution)
    if not dry_run and not output_tif.exists():
        run(["pdal", "pipeline", str(pipeline_path)])
    return output_tif


def write_tile_list(tile_rasters: list[Path], path: Path) -> None:
    path.write_text("\n".join(str(p) for p in tile_rasters) + "\n", encoding="utf-8")


def raster_stats(path: Path) -> dict[str, Any]:
    with rasterio.open(path) as src:
        band = src.read(1, masked=True)
        valid = int(band.count())
        total = int(band.size)
        bounds = src.bounds
        return {
            "path": str(path.relative_to(ROOT)),
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "pixel_size": [abs(float(src.transform.a)), abs(float(src.transform.e))],
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "nodata": src.nodata,
            "valid_cell_count": valid,
            "total_cell_count": total,
            "nodata_ratio": round(1.0 - (valid / total), 6) if total else None,
            "min": round(float(band.min()), 3) if valid else None,
            "max": round(float(band.max()), 3) if valid else None,
        }


def build_products(tile_rasters: list[Path], output_base: Path, dry_run: bool) -> dict[str, str]:
    vrt = output_base.with_suffix(".vrt")
    raw_tif = output_base.with_name(f"{output_base.stem}-raw.tif")
    clipped_tif = output_base.with_suffix(".tif")
    hillshade_tif = output_base.with_name(f"{output_base.stem}-hillshade.tif")
    tile_list = output_base.with_name("selected-tile-rasters.txt")
    write_tile_list(tile_rasters, tile_list)
    if not dry_run:
        for path in (vrt, raw_tif, clipped_tif, hillshade_tif):
            if path.exists():
                path.unlink()
        run(["gdalbuildvrt", "-input_file_list", str(tile_list), str(vrt)])
        run(["gdal_translate", "-ot", "Float32", "-co", "COMPRESS=DEFLATE", "-co", "TILED=YES", str(vrt), str(raw_tif)])
        run(
            [
                "gdalwarp",
                "-t_srs",
                f"EPSG:{LIDAR_SRID}",
                "-ot",
                "Float32",
                "-cutline",
                str(BOUNDARY_PATH),
                "-crop_to_cutline",
                "-dstnodata",
                str(NODATA),
                "-co",
                "COMPRESS=DEFLATE",
                "-co",
                "TILED=YES",
                str(raw_tif),
                str(clipped_tif),
            ]
        )
        run(["gdaldem", "hillshade", str(clipped_tif), str(hillshade_tif), "-compute_edges"])
    return {
        "vrt": str(vrt.relative_to(ROOT)),
        "raw_dem": str(raw_tif.relative_to(ROOT)),
        "clipped_dem": str(clipped_tif.relative_to(ROOT)),
        "hillshade": str(hillshade_tif.relative_to(ROOT)),
        "tile_list": str(tile_list.relative_to(ROOT)),
    }


def write_summary(
    path: Path,
    *,
    tiles: list[Tile],
    ground_check: dict[str, Any],
    outputs: dict[str, str],
    resolution: float,
    buffer_m: float,
    dry_run: bool,
) -> None:
    aggregate_bounds = [
        min(tile.bounds[0] for tile in tiles),
        min(tile.bounds[1] for tile in tiles),
        max(tile.bounds[2] for tile in tiles),
        max(tile.bounds[3] for tile in tiles),
    ]
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": METHOD,
        "dry_run": dry_run,
        "pdal_version": tool_version("pdal"),
        "gdal_version": tool_version("gdalinfo"),
        "source_lidar_dir": str(LIDAR_DIR.relative_to(ROOT)),
        "boundary": str(BOUNDARY_PATH.relative_to(ROOT)),
        "source_srid": LIDAR_SRID,
        "vertical_crs": None,
        "vertical_crs_status": "not_declared_in_lidar_metadata",
        "usage_status": "visualization_only_until_vertical_datum_confirmed",
        "ground_filter": GROUND_EXPRESSION,
        "resolution_m": resolution,
        "boundary_buffer_m": buffer_m,
        "selected_tile_count": len(tiles),
        "selected_point_count": sum(tile.point_count for tile in tiles),
        "selected_bounds_epsg2961": aggregate_bounds,
        "selected_tiles": [tile.path.name for tile in tiles],
        "ground_classification_check": ground_check,
        "outputs": outputs,
    }
    clipped = ROOT / outputs["clipped_dem"]
    if clipped.exists():
        summary["raster"] = raster_stats(clipped)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=float, default=1.0, help="DEM pixel size in metres.")
    parser.add_argument("--buffer-m", type=float, default=100.0, help="Municipal boundary buffer for tile selection.")
    parser.add_argument("--max-tiles", type=int, default=None, help="Limit selected tiles for smoke tests.")
    parser.add_argument("--dry-run", action="store_true", help="Write pipelines and summary without running PDAL/GDAL raster generation.")
    parser.add_argument("--clean", action="store_true", help="Remove prior generated DEM outputs before running.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = OUT_DIR / "work"
    if args.clean and work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    for tool in ("pdal", "gdalinfo", "gdalbuildvrt", "gdal_translate", "gdalwarp", "gdaldem"):
        if not shutil.which(tool, path=tool_env().get("PATH")):
            raise RuntimeError(f"Required tool not found on PATH: {tool}")

    boundary = load_boundary(args.buffer_m)
    tiles = select_tiles(boundary, args.max_tiles)
    validate_tile_crs(tiles)
    ground_check = validate_ground_class(tiles[0])

    print(f"Selected {len(tiles)} LiDAR tiles", flush=True)
    tile_rasters = [build_tile_dem(tile, work_dir, args.resolution, args.dry_run) for tile in tiles]

    output_base = OUT_DIR / "charlottetown-dem-epsg2961-1m"
    outputs = build_products(tile_rasters, output_base, args.dry_run)
    summary_path = OUT_DIR / "charlottetown-dem-epsg2961-1m.summary.json"
    write_summary(
        summary_path,
        tiles=tiles,
        ground_check=ground_check,
        outputs=outputs,
        resolution=args.resolution,
        buffer_m=args.buffer_m,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
