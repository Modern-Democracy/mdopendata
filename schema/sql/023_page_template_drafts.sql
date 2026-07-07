CREATE TABLE IF NOT EXISTS documents.page_template_draft (
  page_template_draft_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES documents.source_document(source_document_id) ON DELETE CASCADE,
  draft_key text NOT NULL,
  name text NOT NULL,
  description text,
  model_name text NOT NULL,
  model_output jsonb NOT NULL,
  source_page_numbers integer[] NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  approved_page_template_id bigint REFERENCES documents.page_template(page_template_id) ON DELETE SET NULL,
  approved_pattern_id bigint REFERENCES documents.pattern(pattern_id) ON DELETE SET NULL,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  approved_at timestamptz,
  CONSTRAINT ck_documents_page_template_draft_status
    CHECK (status IN ('draft', 'approved', 'rejected')),
  CONSTRAINT ck_documents_page_template_draft_pages
    CHECK (cardinality(source_page_numbers) >= 1),
  CONSTRAINT ck_documents_page_template_draft_approval
    CHECK ((status <> 'approved') OR
      (approved_page_template_id IS NOT NULL AND approved_pattern_id IS NOT NULL AND approved_at IS NOT NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_page_template_draft_natural_key
  ON documents.page_template_draft(natural_key);

CREATE INDEX IF NOT EXISTS idx_documents_page_template_draft_document
  ON documents.page_template_draft(source_document_id, status);
