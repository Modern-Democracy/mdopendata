from __future__ import annotations

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

ZONE_NAMES = {
    "RN": "Neighbourhood",
    "EG": "Eastern Gateway",
}

ZONE_RGB = {
    "RN": "#fbf8bf",
    "EG": "#4e4e4f",
}

CORRECTIONS = [
    {
        "correction_id": "RN_belfast_brittany_strathmore_edinburgh",
        "zone_code": "RN",
        "description": (
            "Missing RN block south of Belfast Street, east of Brittany Drive, "
            "north of Strathmore Lane, and west of Edinburgh Drive."
        ),
        "parcel_candidate_ids": [
            23104,
            23105,
            23346,
            23347,
            23388,
            23438,
            23511,
            23672,
            23673,
            23715,
            23751,
            23752,
            23898,
            23901,
            23943,
            24006,
            24007,
            24067,
            24122,
            24184,
            24252,
            24397,
            24411,
            24529,
        ],
    },
    {
        "correction_id": "RN_brittany_strathmore_edinburgh",
        "zone_code": "RN",
        "description": (
            "Missing RN block south of Strathmore Lane, east and north of "
            "Brittany Drive, and west of Edinburgh Drive."
        ),
        "parcel_candidate_ids": [
            23823,
            24008,
            24139,
            24447,
            24457,
        ],
    },
    {
        "correction_id": "RN_edinburgh_westwood_berkeley",
        "zone_code": "RN",
        "description": (
            "Missing RN block east of Edinburgh Drive and within Westwood Crescent, "
            "including the Berkeley Way cul-de-sac."
        ),
        "parcel_candidate_ids": [
            24860,
            24934,
            25009,
            25011,
            25113,
            25168,
            25276,
            25296,
            25351,
            25495,
            25519,
            25537,
            25607,
            25620,
            25621,
            25706,
            25707,
            25792,
            25798,
            25822,
            25954,
            26088,
        ],
    },
    {
        "correction_id": "RN_deep_river",
        "zone_code": "RN",
        "description": (
            "Missing RN properties south of Deep River Drive, west of River Ridge Road, "
            "east of parkland, and north of medium density residential."
        ),
        "parcel_candidate_ids": [82693, 82830, 82833, 82875, 82974],
    },
    {
        "correction_id": "EG_water_weymouth_grafton",
        "zone_code": "EG",
        "description": (
            "Missing EG lots east of Water Street between Weymouth Street and Grafton Street, "
            "north of the Institutional zone."
        ),
        "parcel_candidate_ids": [63727, 64156, 64549],
    },
]


def build_corrections(parcels: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    rows = []
    for correction in CORRECTIONS:
        ids = correction["parcel_candidate_ids"]
        selected = parcels[parcels["parcel_candidate_id"].isin(ids)]
        missing = sorted(set(ids) - set(selected["parcel_candidate_id"].astype(int)))
        if missing:
            raise RuntimeError(f"{correction['correction_id']} missing parcel candidates: {missing}")
        geom = block_envelope_geometry(
            correction["correction_id"],
            unary_union(list(selected.geometry)).buffer(0),
        )
        rows.append(
            {
                "correction_id": correction["correction_id"],
                "zone_code": correction["zone_code"],
                "zone_name": ZONE_NAMES[correction["zone_code"]],
                "legend_rgb": ZONE_RGB[correction["zone_code"]],
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
    zones = pyogrio.read_dataframe(IN_GPKG, layer="draft_zoning_areas_municipal_fit")
    parcels = pyogrio.read_dataframe(IN_GPKG, layer="draft_parcel_polygons_municipal_fit")
    linework = pyogrio.read_dataframe(IN_GPKG, layer="draft_parcel_linework_municipal_fit")
    boundary = pyogrio.read_dataframe(IN_GPKG, layer="municipal_boundary_reference")

    corrections = build_corrections(parcels)
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
