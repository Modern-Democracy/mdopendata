BEGIN;

CREATE TABLE budget.semantic_table_column (
  id bigserial PRIMARY KEY,
  source_table_id bigint NOT NULL REFERENCES budget.source_table(id) ON DELETE CASCADE,
  semantic_column_key text NOT NULL,
  column_order integer NOT NULL CHECK (column_order >= 0),
  raw_header text,
  column_role text NOT NULL CHECK (column_role IN (
    'line_label','period_value','context','note_reference'
  )),
  bbox numeric(9,6)[],
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  review_status text NOT NULL DEFAULT 'needs_review' CHECK (
    review_status IN ('unreviewed','needs_review','approved','rejected')
  ),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (btrim(semantic_column_key) <> ''),
  CHECK (btrim(rationale) <> ''),
  CHECK (bbox IS NULL OR array_length(bbox,1)=4),
  CHECK (review_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  UNIQUE (source_table_id,semantic_column_key),
  UNIQUE (source_table_id,column_order)
);

CREATE TABLE budget.source_cell_semantic_assignment (
  id bigserial PRIMARY KEY,
  source_cell_id bigint NOT NULL REFERENCES budget.source_table_cell(id) ON DELETE CASCADE,
  semantic_column_id bigint NOT NULL REFERENCES budget.semantic_table_column(id) ON DELETE CASCADE,
  fragment_key text NOT NULL,
  fragment_order integer NOT NULL CHECK (fragment_order >= 0),
  raw_fragment_text text NOT NULL,
  fragment_bbox numeric(9,6)[],
  assignment_basis text NOT NULL CHECK (assignment_basis IN (
    'bbox_alignment','header_alignment','manual_review','manual_transcription'
  )),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  review_status text NOT NULL DEFAULT 'needs_review' CHECK (
    review_status IN ('unreviewed','needs_review','approved','rejected')
  ),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (btrim(fragment_key) <> ''),
  CHECK (btrim(raw_fragment_text) <> ''),
  CHECK (btrim(rationale) <> ''),
  CHECK (fragment_bbox IS NULL OR array_length(fragment_bbox,1)=4),
  CHECK (review_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  UNIQUE (source_cell_id,fragment_key),
  UNIQUE (source_cell_id,fragment_order)
);

CREATE FUNCTION budget.validate_source_cell_semantic_assignment() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  cell_table_id bigint;
  semantic_table_id bigint;
  semantic_review_status text;
  source_raw_text text;
BEGIN
  SELECT row.source_table_id,cell.raw_text
  INTO cell_table_id,source_raw_text
  FROM budget.source_table_cell cell
  JOIN budget.source_table_row row ON row.id=cell.source_row_id
  WHERE cell.id=NEW.source_cell_id;

  SELECT source_table_id,review_status
  INTO semantic_table_id,semantic_review_status
  FROM budget.semantic_table_column
  WHERE id=NEW.semantic_column_id;

  IF cell_table_id IS NULL OR semantic_table_id IS NULL
     OR cell_table_id IS DISTINCT FROM semantic_table_id THEN
    RAISE EXCEPTION 'semantic assignment cell and semantic column must belong to the same source table';
  END IF;
  IF NEW.assignment_basis <> 'manual_transcription'
     AND position(NEW.raw_fragment_text IN source_raw_text)=0 THEN
    RAISE EXCEPTION 'semantic assignment fragment must occur in raw cell text unless it is an approved transcription';
  END IF;
  IF NEW.review_status='approved' AND semantic_review_status <> 'approved' THEN
    RAISE EXCEPTION 'approved semantic assignment requires an approved semantic column';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_budget_source_cell_semantic_assignment_compatibility
BEFORE INSERT OR UPDATE ON budget.source_cell_semantic_assignment
FOR EACH ROW EXECUTE FUNCTION budget.validate_source_cell_semantic_assignment();

ALTER TABLE budget.document_period
  ADD COLUMN semantic_column_id bigint REFERENCES budget.semantic_table_column(id);
ALTER TABLE budget.document_period
  ALTER COLUMN source_table_column_id DROP NOT NULL;
ALTER TABLE budget.document_period
  DROP CONSTRAINT document_period_document_id_source_table_column_id_period_r_key;
ALTER TABLE budget.document_period
  ADD CONSTRAINT document_period_source_column_xor CHECK (
    (source_table_column_id IS NOT NULL)::integer + (semantic_column_id IS NOT NULL)::integer = 1
  );

CREATE UNIQUE INDEX uq_budget_document_period_raw_column_role
ON budget.document_period (document_id,source_table_column_id,period_role)
WHERE source_table_column_id IS NOT NULL;

CREATE UNIQUE INDEX uq_budget_document_period_semantic_column_role
ON budget.document_period (document_id,semantic_column_id,period_role)
WHERE semantic_column_id IS NOT NULL;

CREATE OR REPLACE FUNCTION budget.validate_cross_table_links() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  expected_table_id bigint;
  expected_document_id bigint;
  semantic_column_role text;
BEGIN
  IF TG_TABLE_NAME = 'source_table_cell' THEN
    SELECT source_table_id INTO expected_table_id FROM budget.source_table_row WHERE id=NEW.source_row_id;
    IF NOT EXISTS (
      SELECT 1 FROM budget.source_table_column
      WHERE id=NEW.source_table_column_id AND source_table_id=expected_table_id
    ) THEN
      RAISE EXCEPTION 'cell row and column must belong to the same source table';
    END IF;
  ELSIF TG_TABLE_NAME = 'document_period' THEN
    IF NEW.source_table_column_id IS NOT NULL THEN
      SELECT source_table.document_id INTO expected_document_id
      FROM budget.source_table_column source_column
      JOIN budget.source_table source_table ON source_table.id=source_column.source_table_id
      WHERE source_column.id=NEW.source_table_column_id;
    ELSE
      SELECT source_table.document_id,semantic_column.column_role
      INTO expected_document_id,semantic_column_role
      FROM budget.semantic_table_column semantic_column
      JOIN budget.source_table source_table ON source_table.id=semantic_column.source_table_id
      WHERE semantic_column.id=NEW.semantic_column_id;
      IF semantic_column_role IS DISTINCT FROM 'period_value' THEN
        RAISE EXCEPTION 'document period semantic column must have period_value role';
      END IF;
    END IF;
    IF expected_document_id IS DISTINCT FROM NEW.document_id THEN
      RAISE EXCEPTION 'document period column must belong to the same document';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE INDEX idx_budget_semantic_table_column_table_role
ON budget.semantic_table_column (source_table_id,column_role,review_status);
CREATE INDEX idx_budget_source_cell_semantic_assignment_column
ON budget.source_cell_semantic_assignment (semantic_column_id,review_status);

COMMIT;
