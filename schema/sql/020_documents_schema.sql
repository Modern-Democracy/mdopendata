CREATE SCHEMA IF NOT EXISTS documents;

CREATE TABLE IF NOT EXISTS documents.ingest_batch (
  ingest_batch_id bigserial PRIMARY KEY,
  batch_key text NOT NULL,
  source_root text NOT NULL,
  source_manifest_path text,
  source_manifest_hash text,
  ingester_name text NOT NULL,
  ingester_version text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_ingest_batch_status
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_ingest_batch_key
  ON documents.ingest_batch(batch_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_ingest_batch_natural_key
  ON documents.ingest_batch(natural_key);

CREATE TABLE IF NOT EXISTS documents.source_document (
  source_document_id bigserial PRIMARY KEY,
  ingest_batch_id bigint REFERENCES documents.ingest_batch(ingest_batch_id) ON DELETE SET NULL,
  source_document_key text NOT NULL,
  jurisdiction_key text,
  jurisdiction_name_raw text,
  municipality_raw text,
  province text,
  country text NOT NULL DEFAULT 'Canada',
  document_family_key text,
  document_type_key text,
  title_raw text,
  repo_relpath text NOT NULL,
  source_url text,
  mime_type text,
  page_count integer,
  source_file_hash text NOT NULL,
  published_date date,
  acquired_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.source_document(source_document_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_source_document_page_count
    CHECK (page_count IS NULL OR page_count >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_document_active_key
  ON documents.source_document(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_document_key_active
  ON documents.source_document(source_document_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_source_document_jurisdiction
  ON documents.source_document(jurisdiction_key, document_family_key, document_type_key);

CREATE TABLE IF NOT EXISTS documents.source_page (
  source_page_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  page_label_raw text,
  source_locator text NOT NULL,
  text_raw text,
  text_extraction_status text NOT NULL DEFAULT 'not_attempted',
  width numeric,
  height numeric,
  render_dpi integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.source_page(source_page_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_source_page_number
    CHECK (page_number >= 1),
  CONSTRAINT ck_documents_source_page_text_status
    CHECK (text_extraction_status IN ('embedded', 'ocr', 'empty', 'failed', 'not_attempted'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_page_active_key
  ON documents.source_page(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_page_document_number_active
  ON documents.source_page(source_document_id, page_number)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_source_page_document
  ON documents.source_page(source_document_id, page_number);

CREATE TABLE IF NOT EXISTS documents.source_asset (
  source_asset_id bigserial PRIMARY KEY,
  source_document_id bigint REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  source_page_id bigint REFERENCES documents.source_page(source_page_id) ON DELETE CASCADE,
  asset_type text NOT NULL,
  repo_relpath text NOT NULL,
  mime_type text,
  file_hash text,
  width integer,
  height integer,
  render_dpi integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.source_asset(source_asset_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_source_asset_owner
    CHECK (source_document_id IS NOT NULL OR source_page_id IS NOT NULL),
  CONSTRAINT ck_documents_source_asset_type
    CHECK (asset_type IN ('page_render', 'ocr_image', 'embedded_image', 'thumbnail', 'source_file', 'other'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_asset_active_key
  ON documents.source_asset(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_source_asset_page
  ON documents.source_asset(source_page_id, asset_type);

CREATE INDEX IF NOT EXISTS idx_documents_source_asset_document
  ON documents.source_asset(source_document_id, asset_type);

CREATE TABLE IF NOT EXISTS documents.document_family (
  document_family_id bigserial PRIMARY KEY,
  document_family_key text NOT NULL,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.document_family(document_family_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_document_family_status
    CHECK (status IN ('active', 'review', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_document_family_active_key
  ON documents.document_family(document_family_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS documents.document_type (
  document_type_id bigserial PRIMARY KEY,
  document_family_id bigint REFERENCES documents.document_family(document_family_id) ON DELETE SET NULL,
  document_type_key text NOT NULL,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.document_type(document_type_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_document_type_status
    CHECK (status IN ('active', 'review', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_document_type_active_key
  ON documents.document_type(document_type_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_document_type_family
  ON documents.document_type(document_family_id, document_type_key);

CREATE TABLE IF NOT EXISTS documents.section_type (
  section_type_id bigserial PRIMARY KEY,
  section_type_key text NOT NULL,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.section_type(section_type_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_section_type_status
    CHECK (status IN ('active', 'review', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_section_type_active_key
  ON documents.section_type(section_type_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS documents.page_template (
  page_template_id bigserial PRIMARY KEY,
  page_template_key text NOT NULL,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.page_template(page_template_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_page_template_status
    CHECK (status IN ('active', 'review', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_page_template_active_key
  ON documents.page_template(page_template_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS documents.pattern (
  pattern_id bigserial PRIMARY KEY,
  pattern_key text NOT NULL,
  pattern_scope text NOT NULL,
  pattern_name text NOT NULL,
  jurisdiction_scope text NOT NULL DEFAULT 'global',
  document_family_id bigint REFERENCES documents.document_family(document_family_id) ON DELETE SET NULL,
  document_type_id bigint REFERENCES documents.document_type(document_type_id) ON DELETE SET NULL,
  section_type_id bigint REFERENCES documents.section_type(section_type_id) ON DELETE SET NULL,
  page_template_id bigint REFERENCES documents.page_template(page_template_id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'observed',
  confidence_rule jsonb NOT NULL DEFAULT '{}'::jsonb,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.pattern(pattern_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_pattern_scope
    CHECK (pattern_scope IN ('document', 'section', 'page')),
  CONSTRAINT ck_documents_pattern_status
    CHECK (status IN ('observed', 'candidate', 'approved', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pattern_active_key
  ON documents.pattern(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pattern_key_active
  ON documents.pattern(pattern_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_pattern_lookup
  ON documents.pattern(pattern_scope, status, document_family_id, document_type_id, section_type_id, page_template_id);

CREATE TABLE IF NOT EXISTS documents.pattern_cue (
  pattern_cue_id bigserial PRIMARY KEY,
  pattern_id bigint NOT NULL REFERENCES documents.pattern(pattern_id) ON DELETE CASCADE,
  cue_type text NOT NULL,
  cue_value text,
  cue_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  required boolean NOT NULL DEFAULT false,
  weight numeric,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.pattern_cue(pattern_cue_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_pattern_cue_type
    CHECK (cue_type IN ('text', 'regex', 'layout', 'visual', 'metadata', 'page_position'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pattern_cue_active_key
  ON documents.pattern_cue(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_pattern_cue_pattern
  ON documents.pattern_cue(pattern_id, cue_type, required);

CREATE TABLE IF NOT EXISTS documents.pattern_example (
  pattern_example_id bigserial PRIMARY KEY,
  pattern_id bigint NOT NULL REFERENCES documents.pattern(pattern_id) ON DELETE CASCADE,
  source_page_id bigint NOT NULL REFERENCES documents.source_page(source_page_id) ON DELETE CASCADE,
  example_type text NOT NULL,
  evidence_note text,
  reviewer_status text NOT NULL DEFAULT 'unreviewed',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.pattern_example(pattern_example_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_pattern_example_type
    CHECK (example_type IN ('positive', 'negative', 'edge_case')),
  CONSTRAINT ck_documents_pattern_example_reviewer_status
    CHECK (reviewer_status IN ('unreviewed', 'accepted', 'rejected', 'needs_review'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pattern_example_active_key
  ON documents.pattern_example(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pattern_example_page_active
  ON documents.pattern_example(pattern_id, source_page_id, example_type)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_pattern_example_pattern
  ON documents.pattern_example(pattern_id, example_type, reviewer_status);

CREATE TABLE IF NOT EXISTS documents.pattern_version (
  pattern_version_id bigserial PRIMARY KEY,
  pattern_id bigint NOT NULL REFERENCES documents.pattern(pattern_id) ON DELETE CASCADE,
  version_label text NOT NULL,
  prior_status text,
  status text NOT NULL,
  change_reason text NOT NULL,
  changed_by text,
  changed_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_documents_pattern_version_status
    CHECK (status IN ('observed', 'candidate', 'approved', 'deprecated')),
  CONSTRAINT ck_documents_pattern_version_prior_status
    CHECK (prior_status IS NULL OR prior_status IN ('observed', 'candidate', 'approved', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pattern_version_label
  ON documents.pattern_version(pattern_id, version_label);

CREATE TABLE IF NOT EXISTS documents.document_section (
  document_section_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  parent_document_section_id bigint REFERENCES documents.document_section(document_section_id) ON DELETE SET NULL,
  section_key text NOT NULL,
  section_type_id bigint REFERENCES documents.section_type(section_type_id) ON DELETE SET NULL,
  title_raw text,
  page_start integer NOT NULL,
  page_end integer NOT NULL,
  boundary_basis text,
  review_status text NOT NULL DEFAULT 'needs_review',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.document_section(document_section_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_document_section_pages
    CHECK (page_start >= 1 AND page_end >= page_start),
  CONSTRAINT ck_documents_document_section_review_status
    CHECK (review_status IN ('accepted', 'rejected', 'needs_review'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_document_section_active_key
  ON documents.document_section(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_document_section_document_pages
  ON documents.document_section(source_document_id, page_start, page_end);

CREATE TABLE IF NOT EXISTS documents.page_classification (
  page_classification_id bigserial PRIMARY KEY,
  source_page_id bigint NOT NULL REFERENCES documents.source_page(source_page_id) ON DELETE CASCADE,
  document_section_id bigint REFERENCES documents.document_section(document_section_id) ON DELETE SET NULL,
  pattern_id bigint REFERENCES documents.pattern(pattern_id) ON DELETE SET NULL,
  document_family_id bigint REFERENCES documents.document_family(document_family_id) ON DELETE SET NULL,
  document_type_id bigint REFERENCES documents.document_type(document_type_id) ON DELETE SET NULL,
  section_type_id bigint REFERENCES documents.section_type(section_type_id) ON DELETE SET NULL,
  page_template_id bigint REFERENCES documents.page_template(page_template_id) ON DELETE SET NULL,
  classification_source text NOT NULL,
  confidence numeric,
  review_status text NOT NULL DEFAULT 'needs_review',
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.page_classification(page_classification_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_page_classification_source
    CHECK (classification_source IN ('parser', 'reviewer', 'imported', 'model')),
  CONSTRAINT ck_documents_page_classification_confidence
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  CONSTRAINT ck_documents_page_classification_review_status
    CHECK (review_status IN ('accepted', 'rejected', 'needs_review'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_page_classification_active_key
  ON documents.page_classification(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_page_classification_page
  ON documents.page_classification(source_page_id, review_status);

CREATE INDEX IF NOT EXISTS idx_documents_page_classification_pattern
  ON documents.page_classification(pattern_id, review_status);

CREATE TABLE IF NOT EXISTS documents.extracted_field (
  extracted_field_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  source_page_id bigint REFERENCES documents.source_page(source_page_id) ON DELETE SET NULL,
  document_section_id bigint REFERENCES documents.document_section(document_section_id) ON DELETE SET NULL,
  field_key text NOT NULL,
  field_label_raw text,
  value_raw text,
  value_normalized text,
  value_json jsonb,
  bbox jsonb,
  extraction_source text NOT NULL,
  confidence numeric,
  review_status text NOT NULL DEFAULT 'needs_review',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.extracted_field(extracted_field_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_extracted_field_source
    CHECK (extraction_source IN ('parser', 'ocr', 'reviewer', 'imported', 'model')),
  CONSTRAINT ck_documents_extracted_field_confidence
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  CONSTRAINT ck_documents_extracted_field_review_status
    CHECK (review_status IN ('accepted', 'rejected', 'needs_review'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_extracted_field_active_key
  ON documents.extracted_field(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_extracted_field_document
  ON documents.extracted_field(source_document_id, field_key, review_status);

CREATE INDEX IF NOT EXISTS idx_documents_extracted_field_page
  ON documents.extracted_field(source_page_id, field_key);

CREATE TABLE IF NOT EXISTS documents.pipeline (
  pipeline_id bigserial PRIMARY KEY,
  pipeline_key text NOT NULL,
  pipeline_name text NOT NULL,
  pipeline_scope text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.pipeline(pipeline_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_pipeline_scope
    CHECK (pipeline_scope IN ('document', 'section', 'page', 'field')),
  CONSTRAINT ck_documents_pipeline_status
    CHECK (status IN ('active', 'review', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pipeline_active_key
  ON documents.pipeline(pipeline_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS documents.pipeline_route (
  pipeline_route_id bigserial PRIMARY KEY,
  pipeline_id bigint NOT NULL REFERENCES documents.pipeline(pipeline_id) ON DELETE CASCADE,
  source_document_id bigint REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  source_page_id bigint REFERENCES documents.source_page(source_page_id) ON DELETE CASCADE,
  document_section_id bigint REFERENCES documents.document_section(document_section_id) ON DELETE CASCADE,
  page_classification_id bigint REFERENCES documents.page_classification(page_classification_id) ON DELETE SET NULL,
  route_source text NOT NULL,
  route_status text NOT NULL DEFAULT 'needs_review',
  route_reason text,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.pipeline_route(pipeline_route_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_pipeline_route_target
    CHECK (source_document_id IS NOT NULL OR source_page_id IS NOT NULL OR document_section_id IS NOT NULL),
  CONSTRAINT ck_documents_pipeline_route_source
    CHECK (route_source IN ('parser', 'reviewer', 'imported', 'model')),
  CONSTRAINT ck_documents_pipeline_route_status
    CHECK (route_status IN ('accepted', 'rejected', 'needs_review', 'blocked'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_pipeline_route_active_key
  ON documents.pipeline_route(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_pipeline_route_pipeline
  ON documents.pipeline_route(pipeline_id, route_status);

CREATE INDEX IF NOT EXISTS idx_documents_pipeline_route_document
  ON documents.pipeline_route(source_document_id, route_status);

CREATE INDEX IF NOT EXISTS idx_documents_pipeline_route_page
  ON documents.pipeline_route(source_page_id, route_status);

CREATE TABLE IF NOT EXISTS documents.model_gap (
  model_gap_id bigserial PRIMARY KEY,
  source_document_id bigint REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  source_page_id bigint REFERENCES documents.source_page(source_page_id) ON DELETE SET NULL,
  document_section_id bigint REFERENCES documents.document_section(document_section_id) ON DELETE SET NULL,
  gap_type text NOT NULL,
  observed_content_summary text NOT NULL,
  blocking_reason text NOT NULL,
  blocking_status text NOT NULL DEFAULT 'blocks_normalization',
  proposed_owner_role text NOT NULL,
  status text NOT NULL DEFAULT 'open',
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.model_gap(model_gap_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_model_gap_target
    CHECK (source_document_id IS NOT NULL OR source_page_id IS NOT NULL OR document_section_id IS NOT NULL),
  CONSTRAINT ck_documents_model_gap_type
    CHECK (gap_type IN ('new_document_type', 'new_section_type', 'new_page_template', 'new_pipeline', 'new_field_model', 'ambiguous_taxonomy', 'source_quality_blocker')),
  CONSTRAINT ck_documents_model_gap_blocking_status
    CHECK (blocking_status IN ('blocks_ingestion', 'blocks_normalization', 'blocks_routing', 'non_blocking_review')),
  CONSTRAINT ck_documents_model_gap_owner_role
    CHECK (proposed_owner_role IN ('Business Analyst', 'Coding Architect', 'Data Engineer', 'Data Quality Analyst', 'Debugger', 'QA Reviewer', 'Project Management')),
  CONSTRAINT ck_documents_model_gap_status
    CHECK (status IN ('open', 'accepted', 'rejected', 'resolved', 'deferred'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_model_gap_active_key
  ON documents.model_gap(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_model_gap_status
  ON documents.model_gap(status, gap_type, proposed_owner_role);

CREATE INDEX IF NOT EXISTS idx_documents_model_gap_document
  ON documents.model_gap(source_document_id, status);

CREATE TABLE IF NOT EXISTS documents.review_decision (
  review_decision_id bigserial PRIMARY KEY,
  reviewed_table text NOT NULL,
  reviewed_id bigint NOT NULL,
  decision text NOT NULL,
  reviewer text,
  decision_reason text,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  decided_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_documents_review_decision
    CHECK (decision IN ('accepted', 'rejected', 'needs_review', 'deferred', 'superseded'))
);

CREATE INDEX IF NOT EXISTS idx_documents_review_decision_reviewed
  ON documents.review_decision(reviewed_table, reviewed_id, decided_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_review_decision_decision
  ON documents.review_decision(decision, decided_at DESC);
