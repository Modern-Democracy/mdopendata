CREATE TABLE IF NOT EXISTS documents.package_extraction (
  package_extraction_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  extraction_status text NOT NULL DEFAULT 'discovering_templates',
  agenda_document_key text,
  unresolved_template_count integer NOT NULL DEFAULT 0,
  result_json jsonb,
  pipeline_version text NOT NULL,
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.package_extraction(package_extraction_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  CONSTRAINT ck_documents_package_extraction_status
    CHECK (extraction_status IN ('discovering_templates', 'awaiting_template_approval', 'ready_for_extraction', 'extracting', 'completed', 'failed')),
  CONSTRAINT ck_documents_package_extraction_unresolved_count CHECK (unresolved_template_count >= 0),
  CONSTRAINT ck_documents_package_extraction_completed CHECK (
    extraction_status <> 'completed'
    OR (unresolved_template_count = 0 AND agenda_document_key IS NOT NULL AND result_json IS NOT NULL AND completed_at IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_package_extraction_active_key
  ON documents.package_extraction(natural_key) WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_package_extraction_document
  ON documents.package_extraction(source_document_id, extraction_status);

CREATE TABLE IF NOT EXISTS documents.package_extracted_document (
  package_extracted_document_id bigserial PRIMARY KEY,
  package_extraction_id bigint NOT NULL REFERENCES documents.package_extraction(package_extraction_id) ON DELETE CASCADE,
  document_key text NOT NULL,
  document_role text NOT NULL,
  source_order integer NOT NULL,
  primary_agenda_item_key text,
  document_type_key text NOT NULL,
  title_raw text,
  page_numbers integer[] NOT NULL,
  page_template_keys text[] NOT NULL,
  content_json jsonb NOT NULL,
  provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES documents.package_extracted_document(package_extracted_document_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_documents_package_extracted_document_role CHECK (document_role IN ('agenda', 'agenda_item_document')),
  CONSTRAINT ck_documents_package_extracted_document_order CHECK (source_order >= 1),
  CONSTRAINT ck_documents_package_extracted_document_pages CHECK (cardinality(page_numbers) >= 1 AND 0 < ALL(page_numbers)),
  CONSTRAINT ck_documents_package_extracted_document_templates CHECK (cardinality(page_template_keys) >= 1),
  CONSTRAINT ck_documents_package_extracted_document_agenda_binding CHECK (
    (document_role = 'agenda' AND source_order = 1 AND primary_agenda_item_key IS NULL)
    OR (document_role = 'agenda_item_document' AND source_order > 1 AND primary_agenda_item_key IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_package_extracted_document_active_key
  ON documents.package_extracted_document(natural_key) WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_package_extracted_document_order_active
  ON documents.package_extracted_document(package_extraction_id, source_order) WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_package_extracted_document_key_active
  ON documents.package_extracted_document(package_extraction_id, document_key) WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_package_extracted_document_agenda_item
  ON documents.package_extracted_document(primary_agenda_item_key, source_order);
