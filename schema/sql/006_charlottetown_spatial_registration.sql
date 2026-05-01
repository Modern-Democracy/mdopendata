BEGIN;

INSERT INTO zoning.zone_code_crosswalk (context, source_code, target_code, reason) VALUES
  ('charlottetown_draft_schedule_a', 'H', 'HI', 'Draft spatial layer uses H while draft bylaw zone code is HI.'),
  ('charlottetown_current_map', 'C1', 'C-1', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'C2', 'C-2', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'C3', 'C-3', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'ERMUVC', 'ER-MUVC', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'FDA', 'FD', 'Current map code uses FDA for the Future Development bylaw zone FD.'),
  ('charlottetown_current_map', 'M1', 'M-1', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'M2', 'M-2', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'M3', 'M-3', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'MUVC', 'ER-MUVC', 'Current source boundary table uses MUVC while the current legend lists ERMUVC for bylaw zone ER-MUVC.'),
  ('charlottetown_current_map', 'R1L', 'R-1L', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R1N', 'R-1N', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R1S', 'R-1S', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R2', 'R-2', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R2S', 'R-2S', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R3', 'R-3', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R3T', 'R-3T', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R4', 'R-4', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R4A', 'R-4A', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R4B', 'R-4B', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'WLOS', 'WL-OS', 'Current map code omits hyphen used in bylaw zone code.')
ON CONFLICT (context, source_code, target_code) DO NOTHING;

INSERT INTO zoning.spatial_layer (
  layer_key, source_path, source_schema, source_table, source_layer, primary_feature_key,
  geometry_column, expected_geometry_type, srid, zone_code_field, feature_count_baseline,
  invalid_geometry_count, status, metadata
) VALUES
  ('charlottetown_draft_zoning_boundaries', 'data/spatial/charlottetown/charlottetown-draft-map-layers-2026-04-09-municipal-fit.gpkg', 'public', 'CHTWN_Draft_Zoning_Boundaries', 'schedule_a_zoning_areas_municipal_fit', 'fid', 'geom', 'MULTIPOLYGON', 2954, 'zone_code', 20, 0, 'loaded', '{"approved_phase4_layer": true, "source_pdf": "docs/charlottetown/charlottetown-zoning-bylaw-draft_2026-04-09.pdf"}'::jsonb),
  ('charlottetown_civic_addresses', NULL, 'public', 'CHTWN_Civic_Addresses', 'CHTWN_Civic_Addresses', 'id', 'geom', 'POINT', 4326, NULL, 14676, 0, 'loaded', '{"approved_phase4_layer": true}'::jsonb),
  ('charlottetown_parcel_map', 'data/spatial/charlottetown/charlottetown-draft-map-layers-2026-04-09-municipal-fit.gpkg', 'public', 'CHTWN_Parcel_Map', 'schedule_c_parcel_candidates_municipal_fit', 'fid', 'geom', 'MULTIPOLYGON', 2954, NULL, 13833, 0, 'loaded', '{"approved_phase4_layer": true}'::jsonb),
  ('charlottetown_street_network', NULL, 'public', 'CHTWN_Street_Network', 'CHTWN_Street_Network', 'id', 'geom', 'MULTILINESTRING', 4326, NULL, 4598, 0, 'loaded', '{"approved_phase4_layer": true}'::jsonb),
  ('charlottetown_current_zoning_boundaries', NULL, 'public', 'CHTWN_Zoning_Boundaries', 'CHTWN_Zoning_Boundaries', 'id', 'geom', 'MULTIPOLYGON', 2954, 'ZONING', 1558, 0, 'loaded', '{"approved_phase4_layer": true, "legend_source": "docs/charlottetown/current-zoning-codes-and-map-legend.md"}'::jsonb),
  ('charlottetown_schedule_a_wetlands', 'data/spatial/charlottetown/charlottetown-draft-map-layers-2026-04-09-municipal-fit.gpkg', 'public', 'CHTWN_Schedule_A_Wetlands', 'schedule_a_wetlands_excluded_from_parcels', 'fid', 'geom', 'MULTIPOLYGON', 2954, 'feature_type', 64, 0, 'loaded', '{"approved_phase4_layer": true}'::jsonb)
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

INSERT INTO zoning.spatial_feature (spatial_layer_id, feature_key, zone_code_raw, zone_code_normalized, attributes, geom, is_valid, validation_reason)
SELECT l.spatial_layer_id, t.fid::text, t.zone_code, COALESCE(c.target_code, t.zone_code),
       to_jsonb(t) - 'geom', t.geom, ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Draft_Zoning_Boundaries" t
JOIN zoning.spatial_layer l ON l.layer_key = 'charlottetown_draft_zoning_boundaries'
LEFT JOIN zoning.zone_code_crosswalk c
  ON c.context = 'charlottetown_draft_schedule_a' AND c.source_code = t.zone_code AND c.status = 'active'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  zone_code_raw = EXCLUDED.zone_code_raw,
  zone_code_normalized = EXCLUDED.zone_code_normalized,
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

INSERT INTO zoning.spatial_feature (spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason)
SELECT l.spatial_layer_id, t.id::text, to_jsonb(t) - 'geom', ST_Transform(t.geom, 2954), ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Civic_Addresses" t
JOIN zoning.spatial_layer l ON l.layer_key = 'charlottetown_civic_addresses'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

INSERT INTO zoning.spatial_feature (spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason)
SELECT l.spatial_layer_id, t.fid::text, to_jsonb(t) - 'geom', t.geom, ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Parcel_Map" t
JOIN zoning.spatial_layer l ON l.layer_key = 'charlottetown_parcel_map'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

INSERT INTO zoning.spatial_feature (spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason)
SELECT l.spatial_layer_id, t.id::text, to_jsonb(t) - 'geom', ST_Transform(t.geom, 2954), ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Street_Network" t
JOIN zoning.spatial_layer l ON l.layer_key = 'charlottetown_street_network'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

INSERT INTO zoning.spatial_feature (spatial_layer_id, feature_key, zone_code_raw, zone_code_normalized, attributes, geom, is_valid, validation_reason)
SELECT l.spatial_layer_id, t.id::text, t."ZONING", COALESCE(c.target_code, t."ZONING"),
       to_jsonb(t) - 'geom', t.geom, ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Zoning_Boundaries" t
JOIN zoning.spatial_layer l ON l.layer_key = 'charlottetown_current_zoning_boundaries'
LEFT JOIN zoning.zone_code_crosswalk c
  ON c.context = 'charlottetown_current_map' AND c.source_code = t."ZONING" AND c.status = 'active'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  zone_code_raw = EXCLUDED.zone_code_raw,
  zone_code_normalized = EXCLUDED.zone_code_normalized,
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

INSERT INTO zoning.spatial_feature (spatial_layer_id, feature_key, zone_code_raw, zone_code_normalized, attributes, geom, is_valid, validation_reason)
SELECT l.spatial_layer_id, t.fid::text, t.feature_type, t.feature_type,
       to_jsonb(t) - 'geom', t.geom, ST_IsValid(t.geom), ST_IsValidReason(t.geom)
FROM public."CHTWN_Schedule_A_Wetlands" t
JOIN zoning.spatial_layer l ON l.layer_key = 'charlottetown_schedule_a_wetlands'
ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
  zone_code_raw = EXCLUDED.zone_code_raw,
  zone_code_normalized = EXCLUDED.zone_code_normalized,
  attributes = EXCLUDED.attributes,
  geom = EXCLUDED.geom,
  is_valid = EXCLUDED.is_valid,
  validation_reason = EXCLUDED.validation_reason;

INSERT INTO zoning.zone_spatial_feature (document_revision_id, zone_code, spatial_feature_id, match_method, crosswalk_id)
SELECT dr.document_revision_id, sf.zone_code_normalized, sf.spatial_feature_id,
       CASE WHEN c.zone_code_crosswalk_id IS NULL THEN 'direct_zone_code' ELSE 'zone_code_crosswalk' END,
       c.zone_code_crosswalk_id
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer l ON l.spatial_layer_id = sf.spatial_layer_id
JOIN zoning.document_revision dr ON dr.document_revision_id = 1
JOIN zoning.source_file z ON z.document_revision_id = dr.document_revision_id AND z.file_kind = 'zone' AND z.is_active AND z.zone_code = sf.zone_code_normalized
LEFT JOIN zoning.zone_code_crosswalk c
  ON c.context = 'charlottetown_current_map' AND c.source_code = sf.zone_code_raw AND c.target_code = sf.zone_code_normalized AND c.status = 'active'
WHERE l.layer_key = 'charlottetown_current_zoning_boundaries'
ON CONFLICT (document_revision_id, zone_code, spatial_feature_id) DO UPDATE SET
  match_method = EXCLUDED.match_method,
  crosswalk_id = EXCLUDED.crosswalk_id;

INSERT INTO zoning.zone_spatial_feature (document_revision_id, zone_code, spatial_feature_id, match_method, crosswalk_id)
SELECT dr.document_revision_id, sf.zone_code_normalized, sf.spatial_feature_id,
       CASE WHEN c.zone_code_crosswalk_id IS NULL THEN 'direct_zone_code' ELSE 'zone_code_crosswalk' END,
       c.zone_code_crosswalk_id
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer l ON l.spatial_layer_id = sf.spatial_layer_id
JOIN zoning.document_revision dr ON dr.document_revision_id = 2
JOIN zoning.source_file z ON z.document_revision_id = dr.document_revision_id AND z.file_kind = 'zone' AND z.is_active AND z.zone_code = sf.zone_code_normalized
LEFT JOIN zoning.zone_code_crosswalk c
  ON c.context = 'charlottetown_draft_schedule_a' AND c.source_code = sf.zone_code_raw AND c.target_code = sf.zone_code_normalized AND c.status = 'active'
WHERE l.layer_key = 'charlottetown_draft_zoning_boundaries'
ON CONFLICT (document_revision_id, zone_code, spatial_feature_id) DO UPDATE SET
  match_method = EXCLUDED.match_method,
  crosswalk_id = EXCLUDED.crosswalk_id;

DELETE FROM zoning.spatial_reference
WHERE source_record_table = 'zoning.raw_map_reference';

INSERT INTO zoning.spatial_reference (
  document_revision_id, source_file_id, source_record_table, source_record_key,
  reference_type, reference_label_raw, spatial_layer_id, classification, notes
)
SELECT r.document_revision_id, r.source_file_id, 'zoning.raw_map_reference', r.natural_key,
       COALESCE(r.map_reference_type, 'map_reference'),
       COALESCE(r.label_raw, r.title_raw, r.map_reference_source_id),
       CASE
         WHEN r.document_revision_id = 1 AND r.map_reference_source_id LIKE '%zoning-map%' THEN current_layer.spatial_layer_id
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id IN ('schedule-schedule-a-map') THEN draft_layer.spatial_layer_id
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id LIKE 'zone-%-map-zoning-map' THEN draft_layer.spatial_layer_id
         ELSE NULL
       END,
       CASE
         WHEN r.document_revision_id = 1 AND r.map_reference_source_id LIKE '%zoning-map%' THEN 'already_spatial'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id IN ('schedule-schedule-a-map') THEN 'already_spatial'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id LIKE 'zone-%-map-zoning-map' THEN 'already_spatial'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id IN ('schedule-schedule-b-map', 'schedule-schedule-d-map') THEN 'pdf_only_image'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id = 'schedule-schedule-c-map' THEN 'schedule_needing_digitization'
         ELSE 'text_only_reference'
       END,
       CASE
         WHEN r.document_revision_id = 1 AND r.map_reference_source_id LIKE '%zoning-map%' THEN 'Linked to current zoning boundary layer from public.CHTWN_Zoning_Boundaries.'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id IN ('schedule-schedule-a-map') THEN 'Linked to digitized draft Schedule A zoning boundary layer.'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id LIKE 'zone-%-map-zoning-map' THEN 'Zone-level reference to draft Schedule A zoning boundary layer.'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id IN ('schedule-schedule-b-map', 'schedule-schedule-d-map') THEN 'Extracted schedule map text exists, but no approved usable spatial layer is registered for this schedule.'
         WHEN r.document_revision_id = 2 AND r.map_reference_source_id = 'schedule-schedule-c-map' THEN 'Schedule C street hierarchy source has extracted text and parcel-line fit artifacts but no approved usable street-hierarchy spatial layer.'
         ELSE 'Reference text mentions a map or zoning map without a distinct approved spatial layer linkage.'
       END
FROM zoning.raw_map_reference r
LEFT JOIN zoning.spatial_layer current_layer ON current_layer.layer_key = 'charlottetown_current_zoning_boundaries'
LEFT JOIN zoning.spatial_layer draft_layer ON draft_layer.layer_key = 'charlottetown_draft_zoning_boundaries'
WHERE r.is_active
ON CONFLICT DO NOTHING;

COMMIT;
