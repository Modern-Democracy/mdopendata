DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_parcel_zone_assignment CASCADE;

CREATE MATERIALIZED VIEW zoning.v_charlottetown_parcel_zone_assignment AS
SELECT
  p.spatial_feature_id AS parcel_spatial_feature_id,
  p.feature_key AS parcel_feature_key,
  ST_Area(p.geom) AS parcel_area_m2,
  current_zone.spatial_feature_id AS current_zone_spatial_feature_id,
  current_zone.feature_key AS current_zone_feature_key,
  current_zone.zone_code AS current_zone_code,
  current_zone.zone_name AS current_zone_name,
  current_zone.overlap_area_m2 AS current_zone_overlap_area_m2,
  current_zone.overlap_area_m2 / NULLIF(ST_Area(p.geom), 0) AS current_zone_overlap_fraction,
  draft_zone.spatial_feature_id AS draft_zone_spatial_feature_id,
  draft_zone.feature_key AS draft_zone_feature_key,
  draft_zone.zone_code AS draft_zone_code,
  draft_zone.zone_name AS draft_zone_name,
  draft_zone.overlap_area_m2 AS draft_zone_overlap_area_m2,
  draft_zone.overlap_area_m2 / NULLIF(ST_Area(p.geom), 0) AS draft_zone_overlap_fraction,
  p.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.v_charlottetown_parcel_map p
LEFT JOIN LATERAL (
  SELECT
    cz.spatial_feature_id,
    cz.feature_key,
    upper(COALESCE(cz.bylaw_zone_code, cz.zone_code_normalized, cz.zone_code_raw)) AS zone_code,
    upper(COALESCE(cz.bylaw_zone_code, cz.zone_code_normalized, cz.zone_code_raw)) AS zone_name,
    ST_Area(ST_Intersection(cz.geom, p.geom)) AS overlap_area_m2
  FROM zoning.v_charlottetown_current_zoning_boundaries cz
  WHERE cz.geom && p.geom
    AND ST_Intersects(cz.geom, p.geom)
  ORDER BY overlap_area_m2 DESC NULLS LAST, cz.spatial_feature_id
  LIMIT 1
) current_zone ON true
LEFT JOIN LATERAL (
  SELECT
    dz.spatial_feature_id,
    dz.feature_key,
    upper(COALESCE(dz.bylaw_zone_code, dz.zone_code_normalized, dz.zone_code_raw, dz.zone_code)) AS zone_code,
    dz.zone_name,
    ST_Area(ST_Intersection(dz.geom, p.geom)) AS overlap_area_m2
  FROM zoning.v_charlottetown_draft_zoning_boundaries dz
  WHERE dz.geom && p.geom
    AND ST_Intersects(dz.geom, p.geom)
  ORDER BY overlap_area_m2 DESC NULLS LAST, dz.spatial_feature_id
  LIMIT 1
) draft_zone ON true
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_parcel_zone_assignment_parcel_id
  ON zoning.v_charlottetown_parcel_zone_assignment (parcel_spatial_feature_id);

CREATE INDEX ix_v_charlottetown_parcel_zone_assignment_current_zone
  ON zoning.v_charlottetown_parcel_zone_assignment (current_zone_code);

CREATE INDEX ix_v_charlottetown_parcel_zone_assignment_draft_zone
  ON zoning.v_charlottetown_parcel_zone_assignment (draft_zone_code);

CREATE INDEX ix_v_charlottetown_parcel_zone_assignment_zone_pair
  ON zoning.v_charlottetown_parcel_zone_assignment (current_zone_code, draft_zone_code);

CREATE INDEX sidx_v_charlottetown_parcel_zone_assignment_geom
  ON zoning.v_charlottetown_parcel_zone_assignment USING gist (geom);

COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_parcel_zone_assignment IS
  'One row per Charlottetown parcel with largest-overlap current and draft zoning assignments for indexed web map filtering.';
