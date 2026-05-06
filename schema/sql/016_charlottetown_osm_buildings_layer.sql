BEGIN;

INSERT INTO zoning.spatial_layer (
  layer_key, source_path, source_schema, source_table, source_layer,
  primary_feature_key, geometry_column, expected_geometry_type, srid,
  zone_code_field, feature_count_baseline, invalid_geometry_count, status,
  metadata
) VALUES (
  'charlottetown_osm_buildings',
  'maps/pei/CHTWN_OSM_Buildings.geojson',
  'public',
  'CHTWN_OSM_Buildings',
  'CHTWN_OSM_Buildings',
  'id',
  'geom',
  'MULTIPOLYGON',
  4326,
  NULL,
  13144,
  0,
  'loaded',
  '{"source": "OpenStreetMap Overpass API", "clipped_to": "public.CHTWN_Municipal_Boundary"}'::jsonb
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
  IF to_regclass('public."CHTWN_OSM_Buildings"') IS NOT NULL THEN
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
      t.id::text,
      to_jsonb(t) - 'geom',
      ST_Transform(t.geom, 2954),
      ST_IsValid(t.geom),
      ST_IsValidReason(t.geom)
    FROM public."CHTWN_OSM_Buildings" t
    JOIN zoning.spatial_layer l
      ON l.layer_key = 'charlottetown_osm_buildings'
    ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
      attributes = EXCLUDED.attributes,
      geom = EXCLUDED.geom,
      is_valid = EXCLUDED.is_valid,
      validation_reason = EXCLUDED.validation_reason;
  END IF;
END $$;

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_osm_buildings CASCADE;

CREATE MATERIALIZED VIEW zoning.v_charlottetown_osm_buildings AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.attributes ->> 'osm_type' AS osm_type,
  (sf.attributes ->> 'osm_id')::bigint AS osm_id,
  sf.attributes ->> 'building' AS building,
  sf.attributes ->> 'name' AS name,
  sf.attributes ->> 'levels' AS levels,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_osm_buildings'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_osm_buildings_id
  ON zoning.v_charlottetown_osm_buildings (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_osm_buildings_geom
  ON zoning.v_charlottetown_osm_buildings USING gist (geom);

COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_osm_buildings IS
  'GIS-facing polygon materialized view over zoning.spatial_feature for Charlottetown OpenStreetMap building footprints.';

COMMIT;
