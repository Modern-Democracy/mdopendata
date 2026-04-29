CREATE SCHEMA IF NOT EXISTS zoning;

CREATE TABLE IF NOT EXISTS zoning.bylaw_document (
  bylaw_document_id bigserial PRIMARY KEY,
  jurisdiction text NOT NULL,
  bylaw_name text NOT NULL,
  document_family text NOT NULL,
  source_document_path text NOT NULL,
  document_type text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_zoning_bylaw_document_family
    CHECK (document_family IN ('current', 'draft')),
  CONSTRAINT uq_zoning_bylaw_document
    UNIQUE (jurisdiction, bylaw_name, document_family, source_document_path)
);

CREATE TABLE IF NOT EXISTS zoning.document_revision (
  document_revision_id bigserial PRIMARY KEY,
  bylaw_document_id bigint NOT NULL REFERENCES zoning.bylaw_document(bylaw_document_id) ON DELETE CASCADE,
  revision_label text NOT NULL,
  source_manifest_path text,
  source_manifest_hash text,
  natural_key text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zoning.import_batch (
  import_batch_id bigserial PRIMARY KEY,
  document_family text NOT NULL,
  source_root text NOT NULL,
  source_manifest_path text,
  source_manifest_hash text,
  importer_name text NOT NULL,
  importer_version text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_zoning_import_batch_family
    CHECK (document_family IN ('current', 'draft')),
  CONSTRAINT ck_zoning_import_batch_status
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS zoning.source_file (
  source_file_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  import_batch_id bigint NOT NULL REFERENCES zoning.import_batch(import_batch_id) ON DELETE CASCADE,
  repo_relpath text NOT NULL,
  file_kind text NOT NULL,
  document_type text,
  zone_code text,
  title_raw text,
  source_file_hash text NOT NULL,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.source_file(source_file_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_revision_id, repo_relpath, import_batch_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_source_file_active_key
  ON zoning.source_file(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.import_record_event (
  import_record_event_id bigserial PRIMARY KEY,
  import_batch_id bigint NOT NULL REFERENCES zoning.import_batch(import_batch_id) ON DELETE CASCADE,
  record_family text NOT NULL,
  natural_key text NOT NULL,
  prior_content_hash text,
  content_hash text,
  change_status text NOT NULL,
  active_record_table text,
  active_record_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_zoning_import_record_event_status
    CHECK (change_status IN ('added', 'removed', 'changed', 'unchanged'))
);

CREATE INDEX IF NOT EXISTS idx_zoning_import_record_event_batch
  ON zoning.import_record_event(import_batch_id, record_family, change_status);

CREATE TABLE IF NOT EXISTS zoning.bylaw_part (
  bylaw_part_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  part_label_raw text,
  part_title_raw text,
  document_type text,
  zone_code text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.bylaw_part(bylaw_part_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_bylaw_part_active_key
  ON zoning.bylaw_part(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.section (
  section_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  bylaw_part_id bigint REFERENCES zoning.bylaw_part(bylaw_part_id) ON DELETE SET NULL,
  section_source_id text,
  section_label_raw text,
  section_title_raw text,
  assigned_topic text,
  document_type text,
  zone_code text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.section(section_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_section_active_key
  ON zoning.section(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.clause (
  clause_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  section_id bigint REFERENCES zoning.section(section_id) ON DELETE SET NULL,
  clause_source_id text,
  parent_clause_source_id text,
  clause_label_raw text,
  clause_path text[],
  clause_text_raw text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.clause(clause_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_clause_active_key
  ON zoning.clause(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.definition (
  definition_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  term_key text NOT NULL,
  term_raw text NOT NULL,
  definition_text_raw text NOT NULL,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.definition(definition_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_definition_active_key
  ON zoning.definition(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.source_unit (
  source_unit_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  source_unit_source_id text,
  source_unit_type text,
  label_raw text,
  title_raw text,
  text_raw text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.source_unit(source_unit_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_source_unit_active_key
  ON zoning.source_unit(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.raw_page (
  raw_page_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  page_source_id text,
  page_label_raw text,
  page_number integer,
  text_raw text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.raw_page(raw_page_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_raw_page_active_key
  ON zoning.raw_page(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.raw_table (
  raw_table_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  section_id bigint REFERENCES zoning.section(section_id) ON DELETE SET NULL,
  table_source_id text,
  table_title_raw text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.raw_table(raw_table_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_raw_table_active_key
  ON zoning.raw_table(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.raw_table_cell (
  raw_table_cell_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  raw_table_id bigint REFERENCES zoning.raw_table(raw_table_id) ON DELETE CASCADE,
  row_order integer,
  column_order integer,
  column_id text,
  column_label_raw text,
  cell_text_raw text,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.raw_table_cell(raw_table_cell_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_raw_table_cell_active_key
  ON zoning.raw_table_cell(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.raw_map_reference (
  raw_map_reference_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  map_reference_source_id text,
  map_reference_type text,
  label_raw text,
  title_raw text,
  text_raw text,
  source_order integer,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.raw_map_reference(raw_map_reference_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_raw_map_reference_active_key
  ON zoning.raw_map_reference(natural_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS zoning.structured_fact (
  structured_fact_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint NOT NULL REFERENCES zoning.source_file(source_file_id) ON DELETE CASCADE,
  source_record_table text,
  source_record_key text,
  fact_family text NOT NULL,
  fact_type text,
  raw_label text,
  raw_text text,
  normalized_key text,
  value_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES zoning.structured_fact(structured_fact_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_zoning_structured_fact_active_key
  ON zoning.structured_fact(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_zoning_structured_fact_family
  ON zoning.structured_fact(document_revision_id, fact_family, fact_type);

CREATE TABLE IF NOT EXISTS zoning.section_equivalence (
  section_equivalence_id bigserial PRIMARY KEY,
  current_section_id bigint REFERENCES zoning.section(section_id) ON DELETE CASCADE,
  draft_section_id bigint REFERENCES zoning.section(section_id) ON DELETE CASCADE,
  current_section_key text,
  draft_section_key text,
  candidate_method text NOT NULL,
  title_similarity numeric,
  text_similarity numeric,
  assigned_topic text,
  review_status text NOT NULL DEFAULT 'candidate',
  reviewer_notes text,
  equivalence_type text,
  created_import_batch_id bigint REFERENCES zoning.import_batch(import_batch_id),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_zoning_section_equivalence_review_status
    CHECK (review_status IN ('candidate', 'accepted', 'rejected', 'needs_review')),
  CONSTRAINT ck_zoning_section_equivalence_type
    CHECK (equivalence_type IS NULL OR equivalence_type IN ('same_topic', 'renamed_or_restructured', 'partial_overlap', 'current_deferred', 'not_equivalent'))
);

CREATE TABLE IF NOT EXISTS zoning.coverage_gap (
  coverage_gap_id bigserial PRIMARY KEY,
  bylaw_document_id bigint REFERENCES zoning.bylaw_document(bylaw_document_id) ON DELETE CASCADE,
  document_revision_id bigint REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  gap_type text NOT NULL,
  logical_bylaw_part text,
  source_locator text,
  source_file text,
  expected_record_family text,
  comparison_effect text NOT NULL,
  status text NOT NULL,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_zoning_coverage_gap_type
    CHECK (gap_type IN ('deferred_current_chapter', 'deferred_current_appendix_table_rows', 'pdf_only_schedule', 'not_yet_digitized_map', 'source_layout_limit')),
  CONSTRAINT ck_zoning_coverage_gap_status
    CHECK (status IN ('deferred', 'in_progress', 'resolved', 'wont_fix'))
);

CREATE TABLE IF NOT EXISTS zoning.manual_correction (
  manual_correction_id bigserial PRIMARY KEY,
  correction_type text NOT NULL,
  target_table text NOT NULL,
  target_natural_key text NOT NULL,
  target_content_hash text NOT NULL,
  patch_payload jsonb NOT NULL,
  author_or_source text NOT NULL,
  status text NOT NULL,
  reason text,
  created_import_batch_id bigint REFERENCES zoning.import_batch(import_batch_id),
  last_evaluated_import_batch_id bigint REFERENCES zoning.import_batch(import_batch_id),
  replacement_target_key text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_zoning_manual_correction_status
    CHECK (status IN ('active', 'needs_re_evaluation', 'reapplied', 'superseded', 'rejected'))
);

CREATE TABLE IF NOT EXISTS zoning.spatial_layer (
  spatial_layer_id bigserial PRIMARY KEY,
  layer_key text NOT NULL UNIQUE,
  source_path text,
  source_schema text,
  source_table text,
  source_layer text,
  primary_feature_key text NOT NULL,
  geometry_column text NOT NULL DEFAULT 'geom',
  expected_geometry_type text NOT NULL,
  srid integer NOT NULL,
  zone_code_field text,
  feature_count_baseline integer,
  invalid_geometry_count integer,
  status text NOT NULL DEFAULT 'registered',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_zoning_spatial_layer_status
    CHECK (status IN ('registered', 'loaded', 'invalid', 'retired'))
);

CREATE TABLE IF NOT EXISTS zoning.spatial_feature (
  spatial_feature_id bigserial PRIMARY KEY,
  spatial_layer_id bigint NOT NULL REFERENCES zoning.spatial_layer(spatial_layer_id) ON DELETE CASCADE,
  feature_key text NOT NULL,
  zone_code_raw text,
  zone_code_normalized text,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  geom geometry(Geometry, 2954),
  is_valid boolean,
  validation_reason text,
  UNIQUE (spatial_layer_id, feature_key)
);

CREATE INDEX IF NOT EXISTS idx_zoning_spatial_feature_geom
  ON zoning.spatial_feature
  USING gist (geom);

CREATE TABLE IF NOT EXISTS zoning.zone_code_crosswalk (
  zone_code_crosswalk_id bigserial PRIMARY KEY,
  context text NOT NULL,
  source_code text NOT NULL,
  target_code text NOT NULL,
  reason text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  UNIQUE (context, source_code, target_code)
);

CREATE TABLE IF NOT EXISTS zoning.zone_spatial_feature (
  zone_spatial_feature_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  zone_code text NOT NULL,
  spatial_feature_id bigint NOT NULL REFERENCES zoning.spatial_feature(spatial_feature_id) ON DELETE CASCADE,
  match_method text NOT NULL,
  crosswalk_id bigint REFERENCES zoning.zone_code_crosswalk(zone_code_crosswalk_id),
  UNIQUE (document_revision_id, zone_code, spatial_feature_id)
);

CREATE TABLE IF NOT EXISTS zoning.spatial_reference (
  spatial_reference_id bigserial PRIMARY KEY,
  document_revision_id bigint NOT NULL REFERENCES zoning.document_revision(document_revision_id) ON DELETE CASCADE,
  source_file_id bigint REFERENCES zoning.source_file(source_file_id) ON DELETE SET NULL,
  source_record_table text,
  source_record_key text,
  reference_type text NOT NULL,
  reference_label_raw text,
  spatial_layer_id bigint REFERENCES zoning.spatial_layer(spatial_layer_id),
  classification text NOT NULL,
  notes text,
  CONSTRAINT ck_zoning_spatial_reference_classification
    CHECK (classification IN ('already_spatial', 'pdf_only_image', 'schedule_needing_digitization', 'text_only_reference'))
);

CREATE TABLE IF NOT EXISTS zoning.section_topic (
  topic_key text PRIMARY KEY,
  topic_label text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active'
);

INSERT INTO zoning.section_topic (topic_key, topic_label, description) VALUES
  ('administration', 'Administration', 'Bylaw administration and interpretation.'),
  ('definitions', 'Definitions', 'Defined terms and interpretation rules.'),
  ('permitted_uses', 'Permitted uses', 'Use permissions and use categories.'),
  ('lot_requirements', 'Lot requirements', 'Lot area, frontage, coverage, yards, setbacks, and dimensional standards.'),
  ('parking', 'Parking', 'Parking, loading, access, and circulation requirements.'),
  ('signage', 'Signage', 'Signs and sign controls.'),
  ('landscaping', 'Landscaping', 'Landscaping, buffering, screening, and open space requirements.'),
  ('design_standards', 'Design standards', 'Built-form and design requirements.'),
  ('maps_schedules', 'Maps and schedules', 'Map, schedule, overlay, and spatial references.'),
  ('site_specific', 'Site specific', 'Site-specific exemptions, rules, or development agreements.'),
  ('process', 'Process', 'Permit, application, and approval process provisions.'),
  ('other', 'Other', 'Provision does not fit another seeded topic.')
ON CONFLICT (topic_key) DO NOTHING;

INSERT INTO zoning.zone_code_crosswalk (context, source_code, target_code, reason) VALUES
  ('charlottetown_draft_schedule_a', 'H', 'HI', 'Draft spatial layer uses H while draft bylaw zone code is HI.'),
  ('charlottetown_current_map', 'R1L', 'R-1L', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R1N', 'R-1N', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R1S', 'R-1S', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R2S', 'R-2S', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R3T', 'R-3T', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R4A', 'R-4A', 'Current map code omits hyphen used in bylaw zone code.'),
  ('charlottetown_current_map', 'R4B', 'R-4B', 'Current map code omits hyphen used in bylaw zone code.')
ON CONFLICT (context, source_code, target_code) DO NOTHING;
