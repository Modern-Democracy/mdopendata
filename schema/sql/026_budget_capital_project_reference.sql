CREATE TABLE budget.capital_project_reference (
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES budget.source_document(id) ON DELETE CASCADE,
  capital_project_id bigint REFERENCES budget.capital_project(id),
  source_table_id bigint REFERENCES budget.source_table(id),
  source_row_id bigint REFERENCES budget.source_table_row(id),
  raw_label text NOT NULL,
  reference_kind text NOT NULL,
  document_adoption_state text NOT NULL CHECK (document_adoption_state IN ('adopted','draft','unknown')),
  identity_evidence text NOT NULL CHECK (identity_evidence IN ('exact','strong','possible','conflicting')),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (document_id, source_table_id, source_row_id, raw_label),
  CHECK ((identity_evidence IN ('exact','strong') AND capital_project_id IS NOT NULL) OR identity_evidence IN ('possible','conflicting'))
);
