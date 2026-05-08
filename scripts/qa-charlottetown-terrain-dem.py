#!/usr/bin/env python3
"""QA Charlottetown terrain DEM coverage and parcel residuals."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask, rasterize
from rasterio.windows import from_bounds


ROOT = Path(__file__).resolve().parents[1]
DEM_PATH = ROOT / "data" / "spatial" / "charlottetown" / "lidar-terrain-dem" / "charlottetown-dem-epsg2961-1m.tif"
PARCELS_PATH = ROOT / "maps" / "pei" / "CHTWN_Parcel_Map.geojson"
WETLANDS_PATH = ROOT / "maps" / "pei" / "CHTWN_Schedule_A_Wetlands.geojson"
METRICS_PATH = ROOT / "data" / "spatial" / "charlottetown" / "lidar-parcel-metrics" / "chtwn-parcel-lidar-metrics-full.csv"
OUT_DIR = ROOT / "data" / "spatial" / "charlottetown" / "lidar-terrain-dem"
SUMMARY_PATH = OUT_DIR / "charlottetown-dem-epsg2961-1m.qa.summary.json"
RESIDUALS_PATH = OUT_DIR / "charlottetown-dem-epsg2961-1m.parcel-residuals.csv"
NODATA = -9999.0
WATER_SHORELINE_OVERLAP_RATIO = 0.50


def load_metrics() -> dict[int, dict[str, str]]:
    with METRICS_PATH.open(newline="", encoding="utf-8") as f:
        return {int(row["source_parcel_fid"]): row for row in csv.DictReader(f)}


def finite_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if np.isfinite(parsed) else None


def parcel_dem_stats(src: rasterio.io.DatasetReader, geom: Any) -> tuple[int, int, float | None]:
    minx, miny, maxx, maxy = geom.bounds
    window = from_bounds(minx, miny, maxx, maxy, src.transform).round_offsets().round_lengths()
    full_window = window.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
    if full_window.width <= 0 or full_window.height <= 0:
        return 0, 0, None
    data = src.read(1, window=full_window, masked=False)
    transform = src.window_transform(full_window)
    inside = ~geometry_mask([geom], out_shape=data.shape, transform=transform, invert=False)
    land_cells = int(np.count_nonzero(inside))
    if land_cells == 0:
        return 0, 0, None
    valid = inside & np.isfinite(data) & (data != src.nodata)
    valid_cells = int(np.count_nonzero(valid))
    median = float(np.median(data[valid])) if valid_cells else None
    return land_cells, valid_cells, median


def parcel_overlap_ratio(geom: Any, masks: gpd.GeoDataFrame) -> float:
    candidates = masks[masks.intersects(geom)]
    if candidates.empty:
        return 0.0
    area = float(geom.area)
    if area <= 0:
        return 0.0
    overlap = float(candidates.intersection(geom).area.sum())
    return min(1.0, max(0.0, overlap / area))


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    return round(float(np.percentile(np.asarray(values, dtype=np.float64), p)), 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-parcels", type=int, default=None, help="Limit parcels for smoke tests.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics()
    parcels = gpd.read_file(PARCELS_PATH)
    wetlands = gpd.read_file(WETLANDS_PATH)
    with rasterio.open(DEM_PATH) as src:
        parcels = parcels.to_crs(src.crs)
        wetlands = wetlands.to_crs(src.crs)
        if args.max_parcels:
            parcels = parcels.head(args.max_parcels)

        wetland_shapes = [(geom, 1) for geom in wetlands.geometry if geom is not None and not geom.is_empty]
        parcels["wetland_water_overlap_ratio"] = parcels.geometry.apply(lambda geom: parcel_overlap_ratio(geom, wetlands))
        parcels["qa_land_control"] = parcels["wetland_water_overlap_ratio"] < WATER_SHORELINE_OVERLAP_RATIO
        parcel_shapes = [
            (geom, 1)
            for geom in parcels.loc[parcels["qa_land_control"], "geometry"]
            if geom is not None and not geom.is_empty
        ]
        land_mask = rasterize(
            parcel_shapes,
            out_shape=(src.height, src.width),
            transform=src.transform,
            fill=0,
            dtype="uint8",
        ).astype(bool)
        wetland_mask = rasterize(
            wetland_shapes,
            out_shape=(src.height, src.width),
            transform=src.transform,
            fill=0,
            dtype="uint8",
        ).astype(bool)
        refined_land_mask = land_mask & ~wetland_mask
        dem = src.read(1, masked=False)
        valid_dem = np.isfinite(dem) & (dem != src.nodata)
        land_cells = int(np.count_nonzero(land_mask))
        valid_land_cells = int(np.count_nonzero(land_mask & valid_dem))
        refined_land_cells = int(np.count_nonzero(refined_land_mask))
        valid_refined_land_cells = int(np.count_nonzero(refined_land_mask & valid_dem))

        rows: list[dict[str, object]] = []
        residuals_all: list[float] = []
        residuals_medium_high: list[float] = []
        abs_residuals_medium_high: list[float] = []
        coverage_ratios: list[float] = []

        for index, parcel in parcels.iterrows():
            fid = int(parcel["fid"])
            metric = metrics.get(fid, {})
            expected = finite_float(metric.get("ground_elev_p50_m"))
            confidence = metric.get("lidar_metric_confidence") or ""
            terrain_point_count = int(float(metric.get("terrain_point_count") or 0))
            cell_count, valid_cells, dem_median = parcel_dem_stats(src, parcel.geometry)
            coverage_ratio = valid_cells / cell_count if cell_count else None
            residual = (dem_median - expected) if dem_median is not None and expected is not None else None
            if coverage_ratio is not None:
                coverage_ratios.append(coverage_ratio)
            wetland_overlap_ratio = float(parcel["wetland_water_overlap_ratio"])
            if residual is not None:
                residuals_all.append(residual)
                if confidence in {"high", "medium"} and terrain_point_count > 0 and parcel["qa_land_control"]:
                    residuals_medium_high.append(residual)
                    abs_residuals_medium_high.append(abs(residual))
            rows.append(
                {
                    "source_parcel_fid": fid,
                    "parcel_cell_count": cell_count,
                    "valid_dem_cell_count": valid_cells,
                    "dem_coverage_ratio": round(coverage_ratio, 6) if coverage_ratio is not None else None,
                    "dem_ground_median_m": round(dem_median, 4) if dem_median is not None else None,
                    "metric_ground_p50_m": expected,
                    "residual_m": round(residual, 4) if residual is not None else None,
                    "abs_residual_m": round(abs(residual), 4) if residual is not None else None,
                    "lidar_metric_confidence": confidence,
                    "terrain_point_count": terrain_point_count,
                    "wetland_water_overlap_ratio": round(wetland_overlap_ratio, 6),
                    "qa_land_control": bool(parcel["qa_land_control"]),
                }
            )

    with RESIDUALS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    residual_count = len(residuals_medium_high)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dem": str(DEM_PATH.relative_to(ROOT)),
        "parcels": str(PARCELS_PATH.relative_to(ROOT)),
        "metrics": str(METRICS_PATH.relative_to(ROOT)),
        "parcel_count": int(len(parcels)),
        "land_mask_source": (
            "CHTWN_Parcel_Map parcel fabric rasterized to DEM grid after excluding parcels with "
            f"CHTWN_Schedule_A_Wetlands overlap >= {WATER_SHORELINE_OVERLAP_RATIO:.2f}"
        ),
        "refined_land_mask_source": (
            "QA land-control parcels minus CHTWN_Schedule_A_Wetlands water/wetland cartographic fill"
        ),
        "land_cells": land_cells,
        "valid_land_cells": valid_land_cells,
        "land_coverage_ratio": round(valid_land_cells / land_cells, 6) if land_cells else None,
        "refined_land_cells": refined_land_cells,
        "valid_refined_land_cells": valid_refined_land_cells,
        "refined_land_coverage_ratio": round(valid_refined_land_cells / refined_land_cells, 6) if refined_land_cells else None,
        "excluded_wetland_water_cells": int(np.count_nonzero(land_mask & wetland_mask)),
        "excluded_water_shoreline_parcels": int(np.count_nonzero(~parcels["qa_land_control"])),
        "water_shoreline_parcel_overlap_min_ratio": WATER_SHORELINE_OVERLAP_RATIO,
        "wetlands": str(WETLANDS_PATH.relative_to(ROOT)),
        "parcel_coverage_ratio": {
            "p05": percentile(coverage_ratios, 5),
            "p50": percentile(coverage_ratios, 50),
            "p95": percentile(coverage_ratios, 95),
        },
        "residual_controls": {
            "scope": (
                "QA land-control parcels with high or medium lidar_metric_confidence "
                "and terrain_point_count > 0"
            ),
            "count": residual_count,
            "median_residual_m": percentile(residuals_medium_high, 50),
            "median_abs_residual_m": percentile(abs_residuals_medium_high, 50),
            "p95_abs_residual_m": percentile(abs_residuals_medium_high, 95),
            "max_abs_residual_m": round(max(abs_residuals_medium_high), 4) if abs_residuals_medium_high else None,
        },
        "acceptance": {
            "land_coverage_min_ratio": 0.99,
            "land_coverage_pass": (valid_land_cells / land_cells) >= 0.99 if land_cells else False,
            "refined_land_coverage_pass": (valid_refined_land_cells / refined_land_cells) >= 0.99 if refined_land_cells else False,
            "median_abs_residual_max_m": 0.75,
            "median_abs_residual_pass": percentile(abs_residuals_medium_high, 50) <= 0.75 if residual_count else False,
        },
        "outputs": {
            "summary": str(SUMMARY_PATH.relative_to(ROOT)),
            "parcel_residuals": str(RESIDUALS_PATH.relative_to(ROOT)),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
