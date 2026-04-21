CREATE SCHEMA IF NOT EXISTS hrm;

CREATE TABLE IF NOT EXISTS hrm.bylaw (
  bylaw_pk bigserial PRIMARY KEY,
  bylaw_slug text NOT NULL UNIQUE,
  jurisdiction text NOT NULL,
  bylaw_name text NOT NULL,
  source_document_path text,
  existing_spatial_bylaw_id text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hrm.section_file (
  section_file_pk bigserial PRIMARY KEY,
  bylaw_pk bigint NOT NULL REFERENCES hrm.bylaw(bylaw_pk) ON DELETE CASCADE,
  section_kind text NOT NULL,
  source_relpath text NOT NULL UNIQUE,
  document_type text,
  status text,
  zone_code text,
  schedule_label_raw text,
  source_pages_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  raw_json jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hrm_section_file_bylaw
  ON hrm.section_file(bylaw_pk, section_kind);

CREATE TABLE IF NOT EXISTS hrm.zone (
  zone_pk bigserial PRIMARY KEY,
  bylaw_pk bigint NOT NULL REFERENCES hrm.bylaw(bylaw_pk) ON DELETE CASCADE,
  zone_code text NOT NULL,
  zone_name text,
  zone_section_start_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  zone_section_end_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (bylaw_pk, zone_code)
);

CREATE INDEX IF NOT EXISTS idx_hrm_zone_bylaw_code
  ON hrm.zone(bylaw_pk, zone_code);

CREATE TABLE IF NOT EXISTS hrm.definition (
  definition_pk bigserial PRIMARY KEY,
  bylaw_pk bigint NOT NULL REFERENCES hrm.bylaw(bylaw_pk) ON DELETE CASCADE,
  definition_key text NOT NULL,
  term_raw text NOT NULL,
  definition_text text NOT NULL,
  status text,
  section_label_raw text,
  citations_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (bylaw_pk, definition_key)
);

CREATE INDEX IF NOT EXISTS idx_hrm_definition_term
  ON hrm.definition(bylaw_pk, term_raw);

CREATE TABLE IF NOT EXISTS hrm.provision (
  provision_pk bigserial PRIMARY KEY,
  source_key text NOT NULL UNIQUE,
  section_file_pk bigint NOT NULL REFERENCES hrm.section_file(section_file_pk) ON DELETE CASCADE,
  zone_pk bigint REFERENCES hrm.zone(zone_pk) ON DELETE SET NULL,
  provision_kind text NOT NULL,
  section_label_raw text,
  clause_label_raw text,
  clause_path text[],
  parent_clause_label_raw text,
  text_value text,
  status text,
  citations_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_hrm_provision_zone
  ON hrm.provision(zone_pk, provision_kind);

CREATE INDEX IF NOT EXISTS idx_hrm_provision_clause
  ON hrm.provision(section_label_raw, clause_label_raw);

CREATE TABLE IF NOT EXISTS hrm.rule_atom (
  rule_atom_pk bigserial PRIMARY KEY,
  source_key text NOT NULL UNIQUE,
  provision_pk bigint REFERENCES hrm.provision(provision_pk) ON DELETE CASCADE,
  zone_pk bigint REFERENCES hrm.zone(zone_pk) ON DELETE SET NULL,
  rule_type text NOT NULL,
  metric text,
  use_name text,
  numeric_value numeric,
  value_text text,
  unit text,
  comparator text,
  condition_text text,
  applicability_scope text,
  status text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_hrm_rule_atom_zone
  ON hrm.rule_atom(zone_pk, rule_type);

CREATE INDEX IF NOT EXISTS idx_hrm_rule_atom_metric
  ON hrm.rule_atom(metric);

CREATE INDEX IF NOT EXISTS idx_hrm_rule_atom_use
  ON hrm.rule_atom(use_name);

CREATE TABLE IF NOT EXISTS hrm.spatial_reference (
  spatial_ref_pk bigserial PRIMARY KEY,
  source_key text NOT NULL UNIQUE,
  bylaw_pk bigint NOT NULL REFERENCES hrm.bylaw(bylaw_pk) ON DELETE CASCADE,
  section_file_pk bigint REFERENCES hrm.section_file(section_file_pk) ON DELETE SET NULL,
  zone_pk bigint REFERENCES hrm.zone(zone_pk) ON DELETE SET NULL,
  provision_pk bigint REFERENCES hrm.provision(provision_pk) ON DELETE SET NULL,
  feature_key text NOT NULL,
  feature_class text,
  source_type text,
  source_label_raw text,
  schedule_file text,
  extraction_status text,
  target_schema text,
  target_table text,
  target_identifier text,
  join_method text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_hrm_spatial_reference_feature
  ON hrm.spatial_reference(bylaw_pk, feature_key);

CREATE TABLE IF NOT EXISTS hrm.rule_spatial_applicability (
  rule_spatial_applicability_pk bigserial PRIMARY KEY,
  source_key text NOT NULL UNIQUE,
  rule_atom_pk bigint NOT NULL REFERENCES hrm.rule_atom(rule_atom_pk) ON DELETE CASCADE,
  spatial_ref_pk bigint NOT NULL REFERENCES hrm.spatial_reference(spatial_ref_pk) ON DELETE CASCADE,
  applicability_type text NOT NULL DEFAULT 'applies_to',
  priority_order integer NOT NULL DEFAULT 100,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_hrm_rule_spatial_rule
  ON hrm.rule_spatial_applicability(rule_atom_pk);

CREATE INDEX IF NOT EXISTS idx_hrm_rule_spatial_ref
  ON hrm.rule_spatial_applicability(spatial_ref_pk);

CREATE TABLE IF NOT EXISTS hrm.zone_spatial_match (
  zone_spatial_match_pk bigserial PRIMARY KEY,
  zone_pk bigint NOT NULL REFERENCES hrm.zone(zone_pk) ON DELETE CASCADE,
  target_schema text NOT NULL,
  target_table text NOT NULL,
  target_feature_id text NOT NULL,
  match_method text NOT NULL,
  confidence numeric,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (zone_pk, target_schema, target_table, target_feature_id)
);

CREATE INDEX IF NOT EXISTS idx_hrm_zone_spatial_match_zone
  ON hrm.zone_spatial_match(zone_pk);

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
