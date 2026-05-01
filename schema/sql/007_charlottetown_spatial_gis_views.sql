BEGIN;

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_civic_addresses CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_current_zoning_boundaries CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_boundaries CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_parcel_map CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_schedule_a_wetlands CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_street_network CASCADE;

DROP VIEW IF EXISTS zoning.v_charlottetown_civic_addresses CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_current_zoning_boundaries CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_boundaries CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_parcel_map CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_schedule_a_wetlands CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_street_network CASCADE;

CREATE MATERIALIZED VIEW zoning.v_charlottetown_civic_addresses AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(Point, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_civic_addresses'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_civic_addresses_id
  ON zoning.v_charlottetown_civic_addresses (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_civic_addresses_geom
  ON zoning.v_charlottetown_civic_addresses USING gist (geom);

CREATE MATERIALIZED VIEW zoning.v_charlottetown_current_zoning_boundaries AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.zone_code_raw AS "ZONING",
  sf.zone_code_raw,
  sf.zone_code_normalized,
  zsf.zone_code AS bylaw_zone_code,
  zsf.match_method,
  zcc.zone_code_crosswalk_id,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
LEFT JOIN zoning.zone_spatial_feature zsf
  ON zsf.spatial_feature_id = sf.spatial_feature_id
LEFT JOIN zoning.zone_code_crosswalk zcc
  ON zcc.zone_code_crosswalk_id = zsf.crosswalk_id
WHERE sl.layer_key = 'charlottetown_current_zoning_boundaries'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_current_zoning_boundaries_id
  ON zoning.v_charlottetown_current_zoning_boundaries (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_current_zoning_boundaries_geom
  ON zoning.v_charlottetown_current_zoning_boundaries USING gist (geom);

CREATE MATERIALIZED VIEW zoning.v_charlottetown_draft_zoning_boundaries AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.zone_code_raw AS zone_code,
  sf.attributes ->> 'zone_name' AS zone_name,
  sf.zone_code_raw,
  sf.zone_code_normalized,
  zsf.zone_code AS bylaw_zone_code,
  zsf.match_method,
  zcc.zone_code_crosswalk_id,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
LEFT JOIN zoning.zone_spatial_feature zsf
  ON zsf.spatial_feature_id = sf.spatial_feature_id
LEFT JOIN zoning.zone_code_crosswalk zcc
  ON zcc.zone_code_crosswalk_id = zsf.crosswalk_id
WHERE sl.layer_key = 'charlottetown_draft_zoning_boundaries'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_draft_zoning_boundaries_id
  ON zoning.v_charlottetown_draft_zoning_boundaries (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_draft_zoning_boundaries_geom
  ON zoning.v_charlottetown_draft_zoning_boundaries USING gist (geom);

CREATE MATERIALIZED VIEW zoning.v_charlottetown_parcel_map AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_parcel_map'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_parcel_map_id
  ON zoning.v_charlottetown_parcel_map (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_parcel_map_geom
  ON zoning.v_charlottetown_parcel_map USING gist (geom);

CREATE MATERIALIZED VIEW zoning.v_charlottetown_schedule_a_wetlands AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.zone_code_raw AS feature_type_raw,
  sf.zone_code_normalized AS feature_type_normalized,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_schedule_a_wetlands'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_schedule_a_wetlands_id
  ON zoning.v_charlottetown_schedule_a_wetlands (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_schedule_a_wetlands_geom
  ON zoning.v_charlottetown_schedule_a_wetlands USING gist (geom);

CREATE MATERIALIZED VIEW zoning.v_charlottetown_street_network AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiLineString, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl
  ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_street_network'
WITH DATA;

CREATE UNIQUE INDEX ux_v_charlottetown_street_network_id
  ON zoning.v_charlottetown_street_network (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_street_network_geom
  ON zoning.v_charlottetown_street_network USING gist (geom);

COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_civic_addresses IS
  'GIS-facing point materialized view over zoning.spatial_feature for the Charlottetown civic address layer.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_current_zoning_boundaries IS
  'GIS-facing polygon materialized view over zoning.spatial_feature for current Charlottetown zoning boundaries.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_draft_zoning_boundaries IS
  'GIS-facing polygon materialized view over zoning.spatial_feature for draft Charlottetown zoning boundaries.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_parcel_map IS
  'GIS-facing polygon materialized view over zoning.spatial_feature for the Charlottetown parcel candidate layer.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_schedule_a_wetlands IS
  'GIS-facing polygon materialized view over zoning.spatial_feature for Schedule A wetland and waterbody reference features.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_street_network IS
  'GIS-facing line materialized view over zoning.spatial_feature for the Charlottetown street network layer.';

COMMIT;
