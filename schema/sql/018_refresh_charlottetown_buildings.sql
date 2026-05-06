BEGIN;

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_osm_buildings CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_buildings CASCADE;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM zoning.spatial_layer WHERE layer_key = 'charlottetown_osm_buildings'
  ) AND NOT EXISTS (
    SELECT 1 FROM zoning.spatial_layer WHERE layer_key = 'charlottetown_buildings'
  ) THEN
    UPDATE zoning.spatial_layer
       SET layer_key = 'charlottetown_buildings'
     WHERE layer_key = 'charlottetown_osm_buildings';
  ELSIF EXISTS (
    SELECT 1 FROM zoning.spatial_layer WHERE layer_key = 'charlottetown_osm_buildings'
  ) THEN
    DELETE FROM zoning.spatial_feature sf
    USING zoning.spatial_layer sl
    WHERE sf.spatial_layer_id = sl.spatial_layer_id
      AND sl.layer_key = 'charlottetown_osm_buildings';

    DELETE FROM zoning.spatial_layer
     WHERE layer_key = 'charlottetown_osm_buildings';
  END IF;
END $$;

INSERT INTO zoning.spatial_layer (
  layer_key, source_path, source_schema, source_table, source_layer,
  primary_feature_key, geometry_column, expected_geometry_type, srid,
  zone_code_field, feature_count_baseline, invalid_geometry_count, status,
  metadata
) VALUES (
  'charlottetown_buildings',
  NULL,
  'public',
  'CHTWN_Buildings',
  'CHTWN_Buildings',
  'source_osm_building_id',
  'geom',
  'MULTIPOLYGON',
  4326,
  NULL,
  13144,
  0,
  CASE
    WHEN to_regclass('public."CHTWN_Buildings"') IS NULL THEN 'registered'
    ELSE 'loaded'
  END,
  '{"source": "public.CHTWN_Buildings", "derived_from": "public.CHTWN_OSM_Buildings", "height_source": "PEI 2020 LiDAR"}'::jsonb
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
  status = EXCLUDED.status,
  metadata = EXCLUDED.metadata;

DO $$
BEGIN
  IF to_regclass('public."CHTWN_Buildings"') IS NOT NULL THEN
    DELETE FROM zoning.spatial_feature sf
    USING zoning.spatial_layer l
    WHERE sf.spatial_layer_id = l.spatial_layer_id
      AND l.layer_key = 'charlottetown_buildings';

    INSERT INTO zoning.spatial_feature (
      spatial_layer_id,
      feature_key,
      attributes,
      geom,
      is_valid,
      validation_reason
    )
    SELECT
      l.spatial_layer_id,
      t.source_osm_building_id::text,
      to_jsonb(t) - 'geom',
      ST_Transform(t.geom, 2954),
      ST_IsValid(t.geom),
      ST_IsValidReason(t.geom)
    FROM public."CHTWN_Buildings" t
    JOIN zoning.spatial_layer l
      ON l.layer_key = 'charlottetown_buildings';
  END IF;
END $$;

CREATE MATERIALIZED VIEW zoning.v_charlottetown_buildings AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  (sf.attributes ->> 'source_osm_building_id')::integer AS source_osm_building_id,
  sf.attributes ->> 'osm_type' AS osm_type,
  (sf.attributes ->> 'osm_id')::bigint AS osm_id,
  sf.attributes ->> 'building' AS building,
  sf.attributes ->> 'name' AS name,
  sf.attributes ->> 'levels' AS levels,
  (sf.attributes ->> 'height_lidar_m')::numeric AS height_lidar_m,
  sf.attributes ->> 'height_lidar_method' AS height_lidar_method,
  sf.attributes ->> 'height_lidar_confidence' AS height_lidar_confidence,
  sf.attributes ->> 'height_lidar_status' AS height_lidar_status,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_buildings'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_buildings_id
  ON zoning.v_charlottetown_buildings (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_buildings_geom
  ON zoning.v_charlottetown_buildings USING gist (geom);

COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_buildings IS
  'GIS-facing polygon materialized view over zoning.spatial_feature for Charlottetown building footprints with LiDAR-derived height attributes.';

COMMIT;
