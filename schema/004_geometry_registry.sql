CREATE TABLE IF NOT EXISTS hrm.geometry_registry (
  geometry_registry_pk bigserial PRIMARY KEY,
  source_schema text NOT NULL,
  source_table text NOT NULL,
  source_identifier text NOT NULL,
  feature_class text,
  feature_key text,
  feature_name text,
  bylaw_slug text,
  jurisdiction text,
  source_label_raw text,
  match_method text,
  confidence numeric,
  status text NOT NULL DEFAULT 'active',
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  geom geometry(Geometry, 4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_hrm_geometry_registry_source
    UNIQUE (source_schema, source_table, source_identifier),
  CONSTRAINT ck_hrm_geometry_registry_status
    CHECK (status IN ('active', 'derived', 'backlog', 'retired'))
);

CREATE INDEX IF NOT EXISTS idx_hrm_geometry_registry_geom
  ON hrm.geometry_registry
  USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_hrm_geometry_registry_class
  ON hrm.geometry_registry(feature_class);

CREATE INDEX IF NOT EXISTS idx_hrm_geometry_registry_bylaw_feature_key
  ON hrm.geometry_registry(bylaw_slug, feature_key);

CREATE INDEX IF NOT EXISTS idx_hrm_geometry_registry_source_lookup
  ON hrm.geometry_registry(source_schema, source_table, source_identifier);

CREATE OR REPLACE VIEW hrm.v_geometry_registry_qgis AS
SELECT
  gr.geometry_registry_pk,
  gr.source_schema,
  gr.source_table,
  gr.source_identifier,
  gr.feature_class,
  gr.feature_key,
  gr.feature_name,
  gr.bylaw_slug,
  gr.jurisdiction,
  gr.source_label_raw,
  gr.match_method,
  gr.confidence,
  gr.status,
  gr.attributes,
  gr.geom
FROM hrm.geometry_registry AS gr;

CREATE OR REPLACE VIEW hrm.v_spatial_reference_geometry AS
SELECT
  sr.spatial_ref_pk,
  sr.source_key AS spatial_source_key,
  b.bylaw_slug AS spatial_reference_bylaw_slug,
  z.zone_code AS spatial_reference_zone_code,
  sr.feature_key,
  sr.feature_class,
  sr.source_type,
  sr.source_label_raw,
  sr.schedule_file,
  sr.extraction_status,
  sr.target_schema,
  sr.target_table,
  sr.target_identifier,
  sr.join_method,
  sr.metadata AS spatial_reference_metadata,
  gr.geometry_registry_pk,
  gr.source_schema,
  gr.source_table,
  gr.source_identifier,
  gr.feature_name,
  gr.bylaw_slug AS geometry_bylaw_slug,
  gr.jurisdiction,
  gr.match_method,
  gr.confidence,
  gr.status AS geometry_status,
  gr.attributes AS geometry_attributes,
  gr.geom
FROM hrm.spatial_reference AS sr
LEFT JOIN hrm.bylaw AS b
  ON b.bylaw_pk = sr.bylaw_pk
LEFT JOIN hrm.zone AS z
  ON z.zone_pk = sr.zone_pk
LEFT JOIN hrm.geometry_registry AS gr
  ON gr.source_schema = sr.target_schema
 AND gr.source_table = sr.target_table
 AND gr.source_identifier = sr.target_identifier;

CREATE OR REPLACE VIEW hrm.v_rule_atom_spatial_geometry AS
SELECT
  ra.rule_atom_pk,
  ra.source_key AS rule_source_key,
  b.bylaw_slug,
  z.zone_code,
  ra.rule_type,
  ra.metric,
  ra.use_name,
  ra.numeric_value,
  ra.value_text,
  ra.unit,
  ra.comparator,
  ra.condition_text,
  ra.applicability_scope,
  ra.status AS rule_status,
  rsa.rule_spatial_applicability_pk,
  rsa.source_key AS applicability_source_key,
  rsa.applicability_type,
  rsa.priority_order,
  rsa.notes,
  vsrg.spatial_ref_pk,
  vsrg.spatial_source_key,
  vsrg.feature_key,
  vsrg.feature_class,
  vsrg.source_type,
  vsrg.source_label_raw,
  vsrg.schedule_file,
  vsrg.extraction_status,
  vsrg.target_schema,
  vsrg.target_table,
  vsrg.target_identifier,
  vsrg.join_method,
  vsrg.geometry_registry_pk,
  vsrg.feature_name,
  vsrg.geometry_bylaw_slug,
  vsrg.jurisdiction,
  vsrg.match_method,
  vsrg.confidence,
  vsrg.geometry_status,
  vsrg.geometry_attributes,
  vsrg.geom
FROM hrm.rule_spatial_applicability AS rsa
JOIN hrm.rule_atom AS ra
  ON ra.rule_atom_pk = rsa.rule_atom_pk
LEFT JOIN hrm.zone AS z
  ON z.zone_pk = ra.zone_pk
LEFT JOIN hrm.bylaw AS b
  ON b.bylaw_pk = z.bylaw_pk
LEFT JOIN hrm.v_spatial_reference_geometry AS vsrg
  ON vsrg.spatial_ref_pk = rsa.spatial_ref_pk;
