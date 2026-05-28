CREATE SCHEMA IF NOT EXISTS help;

CREATE TABLE IF NOT EXISTS help.import_batch (
  import_batch_id bigserial PRIMARY KEY,
  source_root text NOT NULL,
  source_manifest_path text,
  source_manifest_hash text,
  importer_name text NOT NULL,
  importer_version text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_help_import_batch_status
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS help.import_record_event (
  import_record_event_id bigserial PRIMARY KEY,
  import_batch_id bigint NOT NULL REFERENCES help.import_batch(import_batch_id) ON DELETE CASCADE,
  record_family text NOT NULL,
  natural_key text NOT NULL,
  prior_content_hash text,
  content_hash text,
  change_status text NOT NULL,
  active_record_table text,
  active_record_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_help_import_record_event_status
    CHECK (change_status IN ('added', 'removed', 'changed', 'unchanged'))
);

CREATE INDEX IF NOT EXISTS idx_help_import_record_event_batch
  ON help.import_record_event(import_batch_id, record_family, change_status);

CREATE TABLE IF NOT EXISTS help.term (
  term_id bigserial PRIMARY KEY,
  term_key text NOT NULL,
  term_type text NOT NULL,
  display_label text NOT NULL,
  raw_label text,
  short_help text NOT NULL,
  long_help text,
  audience text NOT NULL DEFAULT 'public',
  status text NOT NULL DEFAULT 'active',
  review_status text NOT NULL DEFAULT 'release_ready',
  source_schema text,
  source_table text,
  source_id text,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES help.term(term_id),
  created_import_batch_id bigint REFERENCES help.import_batch(import_batch_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_help_term_type
    CHECK (term_type IN ('business', 'technical')),
  CONSTRAINT ck_help_term_audience
    CHECK (audience IN ('public', 'staff', 'technical', 'internal')),
  CONSTRAINT ck_help_term_status
    CHECK (status IN ('active', 'deprecated', 'internal_only', 'retired')),
  CONSTRAINT ck_help_term_review_status
    CHECK (review_status IN ('draft', 'needs_review', 'release_ready', 'internal_only'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_term_active_key
  ON help.term(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_term_key_active
  ON help.term(term_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_help_term_release
  ON help.term(audience, status, review_status)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS help.code_table (
  code_table_id bigserial PRIMARY KEY,
  table_key text NOT NULL,
  display_label text NOT NULL,
  description text,
  audience text NOT NULL DEFAULT 'public',
  status text NOT NULL DEFAULT 'active',
  review_status text NOT NULL DEFAULT 'release_ready',
  source_schema text,
  source_table text,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES help.code_table(code_table_id),
  created_import_batch_id bigint REFERENCES help.import_batch(import_batch_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_help_code_table_audience
    CHECK (audience IN ('public', 'staff', 'technical', 'internal')),
  CONSTRAINT ck_help_code_table_status
    CHECK (status IN ('active', 'deprecated', 'internal_only', 'retired')),
  CONSTRAINT ck_help_code_table_review_status
    CHECK (review_status IN ('draft', 'needs_review', 'release_ready', 'internal_only'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_code_table_active_key
  ON help.code_table(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_code_table_key_active
  ON help.code_table(table_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS help.code_value (
  code_value_id bigserial PRIMARY KEY,
  code_table_id bigint NOT NULL REFERENCES help.code_table(code_table_id) ON DELETE CASCADE,
  value_key text NOT NULL,
  raw_value text NOT NULL,
  display_label text NOT NULL,
  description text,
  sort_order integer,
  audience text NOT NULL DEFAULT 'public',
  status text NOT NULL DEFAULT 'active',
  review_status text NOT NULL DEFAULT 'release_ready',
  source_schema text,
  source_table text,
  source_id text,
  citations jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES help.code_value(code_value_id),
  created_import_batch_id bigint REFERENCES help.import_batch(import_batch_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_help_code_value_audience
    CHECK (audience IN ('public', 'staff', 'technical', 'internal')),
  CONSTRAINT ck_help_code_value_status
    CHECK (status IN ('active', 'deprecated', 'internal_only', 'retired')),
  CONSTRAINT ck_help_code_value_review_status
    CHECK (review_status IN ('draft', 'needs_review', 'release_ready', 'internal_only'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_code_value_active_key
  ON help.code_value(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_code_value_table_key_active
  ON help.code_value(code_table_id, value_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_help_code_value_release
  ON help.code_value(code_table_id, audience, status, review_status)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS help.context_binding (
  context_binding_id bigserial PRIMARY KEY,
  context_key text NOT NULL,
  context_type text NOT NULL,
  term_id bigint REFERENCES help.term(term_id) ON DELETE CASCADE,
  code_value_id bigint REFERENCES help.code_value(code_value_id) ON DELETE CASCADE,
  display_order integer,
  help_variant text NOT NULL DEFAULT 'default',
  audience text NOT NULL DEFAULT 'public',
  status text NOT NULL DEFAULT 'active',
  review_status text NOT NULL DEFAULT 'release_ready',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES help.context_binding(context_binding_id),
  created_import_batch_id bigint REFERENCES help.import_batch(import_batch_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_help_context_binding_target
    CHECK (
      (term_id IS NOT NULL AND code_value_id IS NULL)
      OR (term_id IS NULL AND code_value_id IS NOT NULL)
    ),
  CONSTRAINT ck_help_context_binding_type
    CHECK (context_type IN ('route', 'field', 'card', 'filter', 'tooltip', 'panel')),
  CONSTRAINT ck_help_context_binding_audience
    CHECK (audience IN ('public', 'staff', 'technical', 'internal')),
  CONSTRAINT ck_help_context_binding_status
    CHECK (status IN ('active', 'deprecated', 'internal_only', 'retired')),
  CONSTRAINT ck_help_context_binding_review_status
    CHECK (review_status IN ('draft', 'needs_review', 'release_ready', 'internal_only'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_help_context_binding_active_key
  ON help.context_binding(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_help_context_binding_context
  ON help.context_binding(context_key, audience, status, review_status)
  WHERE is_active;
