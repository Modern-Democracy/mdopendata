from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from shapely.geometry import Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
IN_GPKG = (
    ROOT
    / "data"
    / "spatial"
    / "charlottetown"
    / "charlottetown-draft-zoning-map-2026-04-09-page-197-vector-municipal-fit-draft.gpkg"
)
OUT_GPKG = (
    ROOT
    / "data"
    / "spatial"
    / "charlottetown"
    / "charlottetown-draft-zoning-map-2026-04-09-page-197-vector-municipal-fit-corrected-cleaned-draft.gpkg"
)
CORRECTIONS_JSON = (
    ROOT
    / "data"
    / "spatial"
    / "charlottetown"
    / "manual-corrections"
    / "draft-zoning-map-corrections.json"
)
SUPPORTED_SCHEMA_VERSIONS = {1}


def load_corrections_artifact(path: Path) -> tuple[list[dict], dict[str, dict[str, str]]]:
    """Load the reviewer-decision JSON and return (corrections, zone_attributes).

    See data/spatial/charlottetown/manual-corrections/draft-zoning-map-corrections.json
    for the schema. Validates schema_version, presence of the required fields,
    and that every correction's zone_code has a zone_attributes entry.
    """
    if not path.exists():
        raise SystemExit(f"Corrections file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SystemExit(
            f"Unsupported schema_version {schema_version!r}; "
            f"this script supports {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    corrections = payload.get("corrections") or []
    zone_attributes = payload.get("zone_attributes") or {}
    seen_ids: set[str] = set()
    for entry in corrections:
        for field in ("correction_id", "zone_code", "description", "parcel_candidate_ids"):
            if not entry.get(field):
                raise SystemExit(f"Correction is missing required field {field!r}: {entry!r}")
        if entry["correction_id"] in seen_ids:
            raise SystemExit(f"Duplicate correction_id {entry['correction_id']!r}")
        seen_ids.add(entry["correction_id"])
        attrs = zone_attributes.get(entry["zone_code"])
        if not attrs or "zone_name" not in attrs or "legend_rgb" not in attrs:
            raise SystemExit(
                f"zone_attributes entry for {entry['zone_code']!r} is missing or incomplete"
            )
    return corrections, zone_attributes


def build_corrections(
    parcels: gpd.GeoDataFrame,
    corrections_data: list[dict],
    zone_attributes: dict[str, dict[str, str]],
) -> gpd.GeoDataFrame:
    rows = []
    for correction in corrections_data:
        ids = correction["parcel_candidate_ids"]
        selected = parcels[parcels["parcel_candidate_id"].isin(ids)]
        missing = sorted(set(ids) - set(selected["parcel_candidate_id"].astype(int)))
        if missing:
            raise RuntimeError(f"{correction['correction_id']} missing parcel candidates: {missing}")
        geom = block_envelope_geometry(
            correction["correction_id"],
            unary_union(list(selected.geometry)).buffer(0),
        )
        attrs = zone_attributes[correction["zone_code"]]
        rows.append(
            {
                "correction_id": correction["correction_id"],
                "zone_code": correction["zone_code"],
                "zone_name": attrs["zone_name"],
                "legend_rgb": attrs["legend_rgb"],
                "parcel_candidate_ids": ",".join(str(item) for item in ids),
                "parcel_candidate_count": len(ids),
                "description": correction["description"],
                "method": "manual correction from user-identified missing draft zoning areas using municipal-fit parcel candidates",
                "geometry": geom,
            }
        )
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=parcels.crs)


def fill_polygon_holes(geometry):
    if geometry.geom_type == "Polygon":
        return Polygon(geometry.exterior)
    if geometry.geom_type == "MultiPolygon":
        return unary_union([Polygon(part.exterior) for part in geometry.geoms]).buffer(0)
    return geometry


def block_envelope_geometry(correction_id: str, geometry):
    # Small parcel-line gaps and diagonal artifacts should not become zoning
    # boundaries. A short close-open operation keeps street-side outlines while
    # removing sub-parcel holes and near-touching slivers.
    closed = geometry.buffer(3.0, join_style=2).buffer(-3.0, join_style=2).buffer(0)
    closed = fill_polygon_holes(closed).buffer(0)
    if correction_id == "RN_deep_river":
        # The middle Deep River property is missing its street-side line in the
        # polygonized parcel candidates. The convex hull restores the straight
        # northern street edge across the three-property correction group.
        return closed.convex_hull.buffer(0)
    return closed


def build_corrected_zones(zones: gpd.GeoDataFrame, corrections: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    correction_union = unary_union(list(corrections.geometry)).buffer(0)
    rows = []
    for zone in zones.itertuples():
        geom = zone.geometry
        other_corrections = corrections[corrections["zone_code"] != zone.zone_code]
        if not other_corrections.empty:
            geom = geom.difference(unary_union(list(other_corrections.geometry)))
        matching = corrections[corrections["zone_code"] == zone.zone_code]
        if not matching.empty:
            geom = unary_union([geom, *list(matching.geometry)]).buffer(0)
        else:
            geom = geom.buffer(0)
        rows.append(
            {
                "zone_code": zone.zone_code,
                "zone_name": zone.zone_name,
                "legend_rgb": zone.legend_rgb,
                "source_pdf": zone.source_pdf,
                "source_page": zone.source_page,
                "registration": zone.registration,
                "method": f"{zone.method}; manual correction layer applied",
                "manual_correction": bool(zone.zone_code in set(corrections["zone_code"])),
                "geometry": geom,
            }
        )

    corrected = gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=zones.crs)
    corrected["area_m2"] = corrected.area
    return corrected


def exterior_vertex_count(geometry) -> int:
    if geometry.geom_type == "MultiPolygon" and len(geometry.geoms) == 1:
        geometry = geometry.geoms[0]
    if geometry.geom_type != "Polygon":
        return 999
    return max(0, len(geometry.exterior.coords) - 1)


def single_polygon(geometry):
    if geometry.geom_type == "Polygon":
        return geometry
    if geometry.geom_type == "MultiPolygon" and len(geometry.geoms) == 1:
        return geometry.geoms[0]
    return None


def shared_diagonal(split):
    if split.is_empty or split.length < 8:
        return False
    lines = list(split.geoms) if split.geom_type == "MultiLineString" else [split]
    if not lines:
        return False
    longest = max(lines, key=lambda line: line.length)
    coords = list(longest.coords)
    if len(coords) < 2:
        return False
    dx = abs(coords[-1][0] - coords[0][0])
    dy = abs(coords[-1][1] - coords[0][1])
    if dx < 2 or dy < 2:
        return False
    ratio = dx / dy
    return 0.25 <= ratio <= 4


def clean_diagonal_parcel_splits(
    parcels: gpd.GeoDataFrame,
    corrections: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    triangles = parcels[
        parcels.geometry.apply(lambda geom: single_polygon(geom) is not None and exterior_vertex_count(geom) == 3)
    ].copy()
    triangle_indexes = set(triangles.index)
    sindex = parcels.sindex
    graph: dict[int, set[int]] = {idx: set() for idx in triangle_indexes}

    for idx, row in triangles.iterrows():
        geom = single_polygon(row.geometry)
        if geom is None:
            continue
        for other_idx in sindex.query(geom, predicate="intersects"):
            other_idx = int(other_idx)
            if other_idx <= idx or other_idx not in triangle_indexes:
                continue
            other = single_polygon(parcels.geometry.iloc[other_idx])
            if other is None:
                continue
            shared = geom.boundary.intersection(other.boundary)
            if not shared_diagonal(shared):
                continue
            merged = unary_union([geom, other]).buffer(0)
            if merged.geom_type != "Polygon":
                continue
            hull_ratio = merged.convex_hull.area / merged.area if merged.area else 999
            if exterior_vertex_count(merged) <= 6 and hull_ratio <= 1.08:
                graph[idx].add(other_idx)
                graph[other_idx].add(idx)

    seen: set[int] = set()
    groups: list[list[int]] = []
    for idx in graph:
        if idx in seen or not graph[idx]:
            continue
        stack = [idx]
        group = []
        seen.add(idx)
        while stack:
            current = stack.pop()
            group.append(current)
            for nxt in graph[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if 2 <= len(group) <= 4:
            merged = unary_union(list(parcels.geometry.iloc[group])).buffer(0)
            if merged.geom_type == "Polygon" and merged.convex_hull.area / merged.area <= 1.10:
                groups.append(group)

    correction_source_ids: set[int] = set()
    for ids_text in corrections["parcel_candidate_ids"]:
        correction_source_ids.update(int(value) for value in ids_text.split(",") if value)

    merged_indexes = {idx for group in groups for idx in group}
    correction_source_indexes = set(
        parcels[parcels["parcel_candidate_id"].astype(int).isin(correction_source_ids)].index
    )
    replaced_indexes = merged_indexes | correction_source_indexes
    rows = []
    manual_id_base = -100000
    for offset, correction in enumerate(corrections.itertuples(), start=1):
        rows.append(
            {
                "parcel_candidate_id": manual_id_base - offset,
                "source_parcel_candidate_ids": correction.parcel_candidate_ids,
                "source_part_count": int(correction.parcel_candidate_count),
                "cleaning_method": f"manual block envelope from {correction.correction_id}",
                "geometry": correction.geometry,
            }
        )

    for group_id, group in enumerate(groups, start=1):
        if any(idx in correction_source_indexes for idx in group):
            continue
        source_ids = parcels.iloc[group]["parcel_candidate_id"].astype(int).tolist()
        rows.append(
            {
                "parcel_candidate_id": min(source_ids),
                "source_parcel_candidate_ids": ",".join(str(item) for item in source_ids),
                "source_part_count": len(source_ids),
                "cleaning_method": "merged diagonal triangle split candidates",
                "geometry": unary_union(list(parcels.geometry.iloc[group])).buffer(0),
            }
        )

    for row in parcels[~parcels.index.isin(replaced_indexes)].itertuples():
        rows.append(
            {
                "parcel_candidate_id": int(row.parcel_candidate_id),
                "source_parcel_candidate_ids": str(int(row.parcel_candidate_id)),
                "source_part_count": 1,
                "cleaning_method": "unchanged",
                "geometry": row.geometry,
            }
        )

    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=parcels.crs)


def main() -> None:
    corrections_data, zone_attributes = load_corrections_artifact(CORRECTIONS_JSON)

    zones = pyogrio.read_dataframe(IN_GPKG, layer="draft_zoning_areas_municipal_fit")
    parcels = pyogrio.read_dataframe(IN_GPKG, layer="draft_parcel_polygons_municipal_fit")
    linework = pyogrio.read_dataframe(IN_GPKG, layer="draft_parcel_linework_municipal_fit")
    boundary = pyogrio.read_dataframe(IN_GPKG, layer="municipal_boundary_reference")

    corrections = build_corrections(parcels, corrections_data, zone_attributes)
    corrected = build_corrected_zones(zones, corrections)
    cleaned_parcels = clean_diagonal_parcel_splits(parcels, corrections)

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()

    pyogrio.write_dataframe(
        corrected,
        OUT_GPKG,
        layer="draft_zoning_areas_municipal_fit_corrected",
        driver="GPKG",
        geometry_type="MultiPolygon",
        promote_to_multi=True,
    )
    pyogrio.write_dataframe(
        corrections,
        OUT_GPKG,
        layer="draft_zoning_manual_corrections",
        driver="GPKG",
        geometry_type="MultiPolygon",
        promote_to_multi=True,
        append=True,
    )
    pyogrio.write_dataframe(
        parcels,
        OUT_GPKG,
        layer="draft_parcel_polygons_municipal_fit",
        driver="GPKG",
        geometry_type="MultiPolygon",
        promote_to_multi=True,
        append=True,
    )
    pyogrio.write_dataframe(
        cleaned_parcels,
        OUT_GPKG,
        layer="draft_parcel_polygons_municipal_fit_cleaned",
        driver="GPKG",
        geometry_type="MultiPolygon",
        promote_to_multi=True,
        append=True,
    )
    pyogrio.write_dataframe(
        linework,
        OUT_GPKG,
        layer="draft_parcel_linework_municipal_fit",
        driver="GPKG",
        geometry_type="MultiLineString",
        promote_to_multi=True,
        append=True,
    )
    pyogrio.write_dataframe(
        boundary,
        OUT_GPKG,
        layer="municipal_boundary_reference",
        driver="GPKG",
        geometry_type="MultiPolygon",
        promote_to_multi=True,
        append=True,
    )

    summary = corrected.drop(columns=["geometry"]).sort_values("zone_code")
    summary.to_csv(OUT_GPKG.with_suffix(".summary.csv"), index=False)

    print(f"wrote {OUT_GPKG}")
    print(f"corrected_zones {len(corrected)}")
    print(f"manual_corrections {len(corrections)}")
    print(f"manual_correction_area_m2 {corrections.area.sum():.3f}")
    print(f"cleaned_parcel_candidates {len(cleaned_parcels)} from {len(parcels)}")
    print(f"merged_diagonal_split_groups {(cleaned_parcels['source_part_count'] > 1).sum()}")
    print(corrections[["correction_id", "zone_code", "parcel_candidate_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
