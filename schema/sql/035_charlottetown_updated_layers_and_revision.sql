BEGIN;

-- The updated parcel source replaces the registered parcel layer while the
-- original public source table remains available for audit/comparison views.
UPDATE zoning.spatial_layer
SET source_path = 'data/spatial/charlottetown/charlottetown-draft-map-layers-2026-07-30-municipal-fit.gpkg',
    source_table = 'CHTWN_Parcel_Map_Update',
    source_layer = 'schedule_c_parcel_candidates_municipal_fit',
    feature_count_baseline = 14327,
    metadata = metadata || jsonb_build_object(
      'replacement_source_table', 'public.CHTWN_Parcel_Map_Update',
      'replaced_source_table', 'public.CHTWN_Parcel_Map',
      'updated_at', CURRENT_DATE
    )
WHERE layer_key = 'charlottetown_parcel_map';

DELETE FROM zoning.spatial_feature sf
USING zoning.spatial_layer sl
WHERE sf.spatial_layer_id = sl.spatial_layer_id
  AND sl.layer_key = 'charlottetown_parcel_map';

INSERT INTO zoning.spatial_feature (
  spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason
)
SELECT sl.spatial_layer_id, t.fid::text, to_jsonb(t) - 'geom', t.geom,
       ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Parcel_Map_Update" t
JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_parcel_map'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

REFRESH MATERIALIZED VIEW zoning.v_charlottetown_parcel_map;

-- Register the July 30 updated zoning map as a separate layer. The April
-- draft layer and its GIS-facing view remain unchanged for side-by-side use.
INSERT INTO zoning.spatial_layer (
  layer_key, source_path, source_schema, source_table, source_layer,
  primary_feature_key, geometry_column, expected_geometry_type, srid,
  zone_code_field, feature_count_baseline, invalid_geometry_count, status, metadata
)
VALUES (
  'charlottetown_draft_zoning_boundaries_update',
  'data/spatial/charlottetown/charlottetown-draft-map-layers-2026-07-30-municipal-fit.gpkg',
  'public', 'CHTWN_Draft_Zoning_Boundaries_Update',
  'schedule_a_zoning_areas_municipal_fit', 'fid', 'geom', 'MULTIPOLYGON', 2954,
  'zone_code', 18, 0, 'loaded',
  '{"approved_phase4_layer": true, "source_pdf": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-07-30.pdf", "role": "updated_draft_map"}'::jsonb
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

DELETE FROM zoning.spatial_feature sf
USING zoning.spatial_layer sl
WHERE sf.spatial_layer_id = sl.spatial_layer_id
  AND sl.layer_key = 'charlottetown_draft_zoning_boundaries_update';

INSERT INTO zoning.spatial_feature (
  spatial_layer_id, feature_key, zone_code_raw, zone_code_normalized,
  attributes, geom, is_valid, validation_reason
)
SELECT sl.spatial_layer_id, t.fid::text, t.zone_code,
       COALESCE(c.target_code, t.zone_code), to_jsonb(t) - 'geom', t.geom,
       ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Draft_Zoning_Boundaries_Update" t
JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_draft_zoning_boundaries_update'
LEFT JOIN zoning.zone_code_crosswalk c
  ON c.context = 'charlottetown_draft_schedule_a'
 AND c.source_code = t.zone_code
 AND c.status = 'active'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  zone_code_raw = EXCLUDED.zone_code_raw,
  zone_code_normalized = EXCLUDED.zone_code_normalized,
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

-- Link updated map features to the July revision imported from the normalized
-- JSON set. The lookup is source-path based to keep this migration rerunnable.
INSERT INTO zoning.zone_spatial_feature (
  document_revision_id, zone_code, spatial_feature_id, match_method, crosswalk_id
)
SELECT dr.document_revision_id, sf.zone_code_normalized, sf.spatial_feature_id,
       CASE WHEN c.zone_code_crosswalk_id IS NULL THEN 'direct_zone_code' ELSE 'zone_code_crosswalk' END,
       c.zone_code_crosswalk_id
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl ON sl.spatial_layer_id = sf.spatial_layer_id
JOIN zoning.document_revision dr
  ON dr.source_manifest_path = 'data/zoning/charlottetown-draft-2026-07-30/source-manifest.json'
JOIN zoning.source_file z
  ON z.document_revision_id = dr.document_revision_id
 AND z.file_kind = 'zone'
 AND z.is_active
 AND z.zone_code = sf.zone_code_normalized
LEFT JOIN zoning.zone_code_crosswalk c
  ON c.context = 'charlottetown_draft_schedule_a'
 AND c.source_code = sf.zone_code_raw
 AND c.target_code = sf.zone_code_normalized
 AND c.status = 'active'
WHERE sl.layer_key = 'charlottetown_draft_zoning_boundaries_update'
ON CONFLICT (document_revision_id, zone_code, spatial_feature_id) DO UPDATE SET
  match_method = EXCLUDED.match_method,
  crosswalk_id = EXCLUDED.crosswalk_id;

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_boundaries_update CASCADE;
CREATE MATERIALIZED VIEW zoning.v_charlottetown_draft_zoning_boundaries_update AS
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
JOIN zoning.spatial_layer sl ON sl.spatial_layer_id = sf.spatial_layer_id
LEFT JOIN zoning.zone_spatial_feature zsf
  ON zsf.spatial_feature_id = sf.spatial_feature_id
 AND zsf.document_revision_id = (
   SELECT dr.document_revision_id
   FROM zoning.document_revision dr
   WHERE dr.source_manifest_path = 'data/zoning/charlottetown-draft-2026-07-30/source-manifest.json'
   ORDER BY dr.document_revision_id DESC
   LIMIT 1
 )
LEFT JOIN zoning.zone_code_crosswalk zcc ON zcc.zone_code_crosswalk_id = zsf.crosswalk_id
WHERE sl.layer_key = 'charlottetown_draft_zoning_boundaries_update'
WITH DATA;
CREATE UNIQUE INDEX ux_v_charlottetown_draft_zoning_boundaries_update_id
  ON zoning.v_charlottetown_draft_zoning_boundaries_update (spatial_feature_id);
CREATE INDEX sidx_v_charlottetown_draft_zoning_boundaries_update_geom
  ON zoning.v_charlottetown_draft_zoning_boundaries_update USING gist (geom);
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_draft_zoning_boundaries_update IS
  'GIS-facing July 30 2026 updated draft zoning boundary layer.';

CREATE OR REPLACE VIEW zoning.v_charlottetown_draft_zoning_boundaries_original AS
SELECT * FROM zoning.v_charlottetown_draft_zoning_boundaries;
COMMENT ON VIEW zoning.v_charlottetown_draft_zoning_boundaries_original IS
  'Stable alias for the April 9 2026 original draft zoning boundary layer.';

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
  SELECT cz.spatial_feature_id, cz.feature_key,
         upper(COALESCE(cz.bylaw_zone_code, cz.zone_code_normalized, cz.zone_code_raw)) AS zone_code,
         upper(COALESCE(cz.bylaw_zone_code, cz.zone_code_normalized, cz.zone_code_raw)) AS zone_name,
         ST_Area(ST_Intersection(cz.geom, p.geom)) AS overlap_area_m2
  FROM zoning.v_charlottetown_current_zoning_boundaries cz
  WHERE cz.geom && p.geom AND ST_Intersects(cz.geom, p.geom)
  ORDER BY overlap_area_m2 DESC NULLS LAST, cz.spatial_feature_id
  LIMIT 1
) current_zone ON true
LEFT JOIN LATERAL (
  SELECT dz.spatial_feature_id, dz.feature_key,
         upper(COALESCE(dz.bylaw_zone_code, dz.zone_code_normalized, dz.zone_code_raw, dz.zone_code)) AS zone_code,
         dz.zone_name,
         ST_Area(ST_Intersection(dz.geom, p.geom)) AS overlap_area_m2
  FROM zoning.v_charlottetown_draft_zoning_boundaries_update dz
  WHERE dz.geom && p.geom AND ST_Intersects(dz.geom, p.geom)
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
  'One row per updated Charlottetown parcel with largest-overlap current and July 30 updated draft zoning assignments.';

COMMIT;
