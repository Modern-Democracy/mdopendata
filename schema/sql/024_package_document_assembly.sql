ALTER TABLE documents.package_extraction
  DROP CONSTRAINT IF EXISTS ck_documents_package_extraction_status;

ALTER TABLE documents.package_extraction
  ADD CONSTRAINT ck_documents_package_extraction_status
  CHECK (extraction_status IN (
    'discovering_templates', 'awaiting_template_approval',
    'awaiting_document_assembly', 'ready_for_extraction',
    'extracting', 'completed', 'failed'
  ));

CREATE TABLE IF NOT EXISTS documents.package_document_assembly (
  package_document_assembly_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  document_key text NOT NULL,
  document_order integer NOT NULL,
  title text NOT NULL,
  page_start integer NOT NULL,
  page_end integer NOT NULL,
  is_agenda boolean NOT NULL DEFAULT false,
  primary_agenda_item_key text,
  page_template_keys text[] NOT NULL,
  assembly_rule jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'draft',
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  approved_at timestamptz,
  CONSTRAINT ck_documents_package_document_assembly_order CHECK (document_order >= 1),
  CONSTRAINT ck_documents_package_document_assembly_pages CHECK (page_start >= 1 AND page_end >= page_start),
  CONSTRAINT ck_documents_package_document_assembly_status CHECK (status IN ('draft', 'approved')),
  CONSTRAINT ck_documents_package_document_assembly_templates CHECK (cardinality(page_template_keys) >= 1),
  CONSTRAINT ck_documents_package_document_assembly_agenda_binding CHECK (
    (is_agenda AND primary_agenda_item_key IS NULL) OR
    (NOT is_agenda AND (status = 'draft' OR primary_agenda_item_key IS NOT NULL))
  ),
  CONSTRAINT ck_documents_package_document_assembly_approval CHECK (status <> 'approved' OR approved_at IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_package_document_assembly_natural_key
  ON documents.package_document_assembly(natural_key) WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_package_document_assembly_order
  ON documents.package_document_assembly(source_document_id, document_order) WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_documents_package_document_assembly_pages
  ON documents.package_document_assembly(source_document_id, page_start, page_end) WHERE is_active;
