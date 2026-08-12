BEGIN;

-- The ward PDF contains 69 printed voting-area polygons. The first component
-- of each code (for example, 8 in 8-7) identifies one of 10 voting districts.
-- The source tables are loaded from the extracted GeoPackage before this
-- migration is applied, but the registration remains safe when they are absent.
INSERT INTO zoning.spatial_layer (
  layer_key, source_path, source_schema, source_table, source_layer,
  primary_feature_key, geometry_column, expected_geometry_type, srid,
  zone_code_field, feature_count_baseline, invalid_geometry_count, status, metadata
)
VALUES
  (
    'charlottetown_voting_areas',
    'data/spatial/charlottetown/charlottetown-wards-municipal-fit.gpkg',
    'public', 'CHTWN_Voting_Areas', 'voting_areas_municipal_fit',
    'voting_area_code', 'geom', 'MULTIPOLYGON', 2954,
    NULL, 69, 0, 'registered',
    '{"source_pdf":"maps/Chtown_All_Wards.pdf", "layer_role":"printed_voting_areas", "district_key":"district_code", "approved_map_fit":true}'::jsonb
  ),
  (
    'charlottetown_voting_districts',
    'data/spatial/charlottetown/charlottetown-wards-municipal-fit.gpkg',
    'public', 'CHTWN_Voting_Districts', 'voting_districts_municipal_fit',
    'district_code', 'geom', 'MULTIPOLYGON', 2954,
    NULL, 10, 0, 'registered',
    '{"source_pdf":"maps/Chtown_All_Wards.pdf", "layer_role":"dissolved_voting_districts", "area_layer_key":"charlottetown_voting_areas", "approved_map_fit":true}'::jsonb
  )
ON CONFLICT (layer_key) DO UPDATE SET
  source_path = EXCLUDED.source_path,
  source_schema = EXCLUDED.source_schema,
  source_table = EXCLUDED.source_table,
  source_layer = EXCLUDED.source_layer,
  primary_feature_key = EXCLUDED.primary_feature_key,
  geometry_column = EXCLUDED.geometry_column,
  expected_geometry_type = EXCLUDED.expected_geometry_type,
  srid = EXCLUDED.srid,
  zone_code_field = EXCLUDED.zone_code_field,
  feature_count_baseline = EXCLUDED.feature_count_baseline,
  invalid_geometry_count = EXCLUDED.invalid_geometry_count,
  metadata = EXCLUDED.metadata;

DELETE FROM zoning.spatial_feature sf
USING zoning.spatial_layer sl
WHERE sf.spatial_layer_id = sl.spatial_layer_id
  AND sl.layer_key IN ('charlottetown_voting_areas', 'charlottetown_voting_districts');

DO $$
BEGIN
  IF to_regclass('public."CHTWN_Voting_Areas"') IS NOT NULL THEN
    INSERT INTO zoning.spatial_feature (
      spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason
    )
    SELECT sl.spatial_layer_id,
           t.voting_area_code,
           to_jsonb(t) - 'geom',
           t.geom::geometry(MultiPolygon, 2954),
           ST_IsValid(t.geom),
           ST_IsValidReason(t.geom)
    FROM public."CHTWN_Voting_Areas" t
    JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_voting_areas'
    ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
      attributes = EXCLUDED.attributes,
      geom = EXCLUDED.geom,
      is_valid = EXCLUDED.is_valid,
      validation_reason = EXCLUDED.validation_reason;
  END IF;

  IF to_regclass('public."CHTWN_Voting_Districts"') IS NOT NULL THEN
    INSERT INTO zoning.spatial_feature (
      spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason
    )
    SELECT sl.spatial_layer_id,
           t.district_code,
           to_jsonb(t) - 'geom',
           t.geom::geometry(MultiPolygon, 2954),
           ST_IsValid(t.geom),
           ST_IsValidReason(t.geom)
    FROM public."CHTWN_Voting_Districts" t
    JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_voting_districts'
    ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
      attributes = EXCLUDED.attributes,
      geom = EXCLUDED.geom,
      is_valid = EXCLUDED.is_valid,
      validation_reason = EXCLUDED.validation_reason;
  END IF;
END $$;

UPDATE zoning.spatial_layer sl
SET status = CASE WHEN EXISTS (
                  SELECT 1 FROM zoning.spatial_feature sf
                  WHERE sf.spatial_layer_id = sl.spatial_layer_id
                ) THEN 'loaded' ELSE 'registered' END,
    metadata = CASE WHEN EXISTS (
                  SELECT 1 FROM zoning.spatial_feature sf
                  WHERE sf.spatial_layer_id = sl.spatial_layer_id
                )
                THEN sl.metadata - 'source_table_missing_at_migration' - 'source_table_missing_checked_at'
                WHEN to_regclass(format('%I.%I', sl.source_schema, sl.source_table)) IS NULL
                THEN sl.metadata || jsonb_build_object('source_table_missing_at_migration', true, 'source_table_missing_checked_at', now())
                ELSE sl.metadata END
WHERE sl.layer_key IN ('charlottetown_voting_areas', 'charlottetown_voting_districts');

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_voting_areas CASCADE;
CREATE MATERIALIZED VIEW zoning.v_charlottetown_voting_areas AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key AS voting_area_code,
  sf.attributes ->> 'district_code' AS district_code,
  (sf.attributes ->> 'district_number')::integer AS district_number,
  (sf.attributes ->> 'voting_area_number')::integer AS voting_area_number,
  sf.attributes ->> 'source_pdf' AS source_pdf,
  sf.attributes ->> 'source_fill_rgb' AS source_fill_rgb,
  (sf.attributes ->> 'area_m2')::double precision AS area_m2,
  (sf.attributes ->> 'label_match_distance_m')::double precision AS label_match_distance_m,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_voting_areas'
WITH DATA;
CREATE UNIQUE INDEX ux_v_charlottetown_voting_areas_id
  ON zoning.v_charlottetown_voting_areas (spatial_feature_id);
CREATE UNIQUE INDEX ux_v_charlottetown_voting_areas_code
  ON zoning.v_charlottetown_voting_areas (voting_area_code);
CREATE INDEX ix_v_charlottetown_voting_areas_district
  ON zoning.v_charlottetown_voting_areas (district_code);
CREATE INDEX sidx_v_charlottetown_voting_areas_geom
  ON zoning.v_charlottetown_voting_areas USING gist (geom);

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_voting_districts CASCADE;
CREATE MATERIALIZED VIEW zoning.v_charlottetown_voting_districts AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key AS district_code,
  (sf.attributes ->> 'district_number')::integer AS district_number,
  (sf.attributes ->> 'voting_area_count')::integer AS voting_area_count,
  sf.attributes ->> 'source_pdf' AS source_pdf,
  sf.attributes ->> 'source_fill_rgb' AS source_fill_rgb,
  (sf.attributes ->> 'area_m2')::double precision AS area_m2,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_voting_districts'
WITH DATA;
CREATE UNIQUE INDEX ux_v_charlottetown_voting_districts_id
  ON zoning.v_charlottetown_voting_districts (spatial_feature_id);
CREATE UNIQUE INDEX ux_v_charlottetown_voting_districts_code
  ON zoning.v_charlottetown_voting_districts (district_code);
CREATE INDEX sidx_v_charlottetown_voting_districts_geom
  ON zoning.v_charlottetown_voting_districts USING gist (geom);

COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_voting_areas IS
  'GIS-facing 69-feature Charlottetown voting-area layer extracted from maps/Chtown_All_Wards.pdf.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_voting_districts IS
  'GIS-facing 10-feature Charlottetown voting-district layer dissolved from the extracted voting areas.';

COMMIT;
