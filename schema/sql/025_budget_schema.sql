CREATE SCHEMA IF NOT EXISTS budget;

CREATE TABLE budget.municipality (
  id bigserial PRIMARY KEY, slug text NOT NULL UNIQUE, legal_name text NOT NULL,
  province_code text NOT NULL, country_code text NOT NULL DEFAULT 'CA', boundary_feature_id bigint,
  effective_from date NOT NULL, effective_to date,
  CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE budget.source_document (
  id bigserial PRIMARY KEY, municipality_id bigint NOT NULL REFERENCES budget.municipality(id),
  title text NOT NULL, document_kind text NOT NULL, source_uri text, local_path text,
  sha256 text NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'), published_on date,
  retrieved_at timestamptz, page_count integer CHECK (page_count > 0),
  status text NOT NULL DEFAULT 'discovered' CHECK (status IN ('discovered','extracted','reviewed','published','superseded'))
);

CREATE TABLE budget.source_page (
  id bigserial PRIMARY KEY, document_id bigint NOT NULL REFERENCES budget.source_document(id) ON DELETE CASCADE,
  pdf_page_number integer NOT NULL CHECK (pdf_page_number > 0), printed_page_label text,
  section_label text, content_type text, text_path text, image_path text,
  extraction_method text CHECK (extraction_method IN ('embedded_text','ocr','manual_transcription')),
  extractor_version text, extraction_confidence numeric(6,5) CHECK (extraction_confidence BETWEEN 0 AND 1),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (document_id, pdf_page_number)
);

CREATE TABLE budget.source_table (
  id bigserial PRIMARY KEY, document_id bigint NOT NULL REFERENCES budget.source_document(id) ON DELETE CASCADE,
  table_key text NOT NULL, raw_title text, table_type text, continuation_group_key text,
  extraction_status text NOT NULL DEFAULT 'extracted' CHECK (extraction_status IN ('pending','extracted','failed')),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (document_id, table_key)
);

CREATE TABLE budget.source_table_page (
  source_table_id bigint NOT NULL REFERENCES budget.source_table(id) ON DELETE CASCADE,
  source_page_id bigint NOT NULL REFERENCES budget.source_page(id) ON DELETE CASCADE,
  page_order integer NOT NULL CHECK (page_order > 0), page_role text NOT NULL DEFAULT 'body',
  bbox numeric(9,6)[], extraction_method_override text CHECK (extraction_method_override IN ('embedded_text','ocr','manual_transcription')),
  PRIMARY KEY (source_table_id, source_page_id), UNIQUE (source_table_id, page_order),
  CHECK (bbox IS NULL OR array_length(bbox, 1) = 4)
);

CREATE TABLE budget.source_table_column (
  id bigserial PRIMARY KEY, source_table_id bigint NOT NULL REFERENCES budget.source_table(id) ON DELETE CASCADE,
  column_key text NOT NULL, column_index integer NOT NULL CHECK (column_index >= 0), raw_header text,
  column_role text, bbox numeric(9,6)[],
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (source_table_id, column_key), UNIQUE (source_table_id, column_index),
  CHECK (bbox IS NULL OR array_length(bbox, 1) = 4)
);

CREATE TABLE budget.source_table_row (
  id bigserial PRIMARY KEY, source_table_id bigint NOT NULL REFERENCES budget.source_table(id) ON DELETE CASCADE,
  row_key text NOT NULL, row_index integer NOT NULL CHECK (row_index >= 0), raw_text text NOT NULL,
  raw_label text, indent_level integer CHECK (indent_level >= 0), row_style jsonb NOT NULL DEFAULT '{}'::jsonb,
  bbox numeric(9,6)[], parser_confidence numeric(6,5) CHECK (parser_confidence BETWEEN 0 AND 1),
  UNIQUE (source_table_id, row_key), UNIQUE (source_table_id, row_index),
  CHECK (bbox IS NULL OR array_length(bbox, 1) = 4)
);

CREATE TABLE budget.source_table_cell (
  id bigserial PRIMARY KEY, source_row_id bigint NOT NULL REFERENCES budget.source_table_row(id) ON DELETE CASCADE,
  source_table_column_id bigint NOT NULL REFERENCES budget.source_table_column(id) ON DELETE CASCADE,
  raw_text text NOT NULL, bbox numeric(9,6)[], parsed_numeric numeric(20,4), parsed_text text,
  parse_status text NOT NULL DEFAULT 'unparsed' CHECK (parse_status IN ('unparsed','parsed','ambiguous','invalid')),
  parser_confidence numeric(6,5) CHECK (parser_confidence BETWEEN 0 AND 1),
  UNIQUE (source_row_id, source_table_column_id), CHECK (bbox IS NULL OR array_length(bbox, 1) = 4)
);

CREATE TABLE budget.reporting_entity (
  id bigserial PRIMARY KEY, municipality_id bigint NOT NULL REFERENCES budget.municipality(id),
  parent_entity_id bigint REFERENCES budget.reporting_entity(id), slug text NOT NULL, display_name text NOT NULL,
  entity_type text NOT NULL, effective_from date NOT NULL, effective_to date,
  UNIQUE (municipality_id, slug, effective_from), CHECK (parent_entity_id IS NULL OR parent_entity_id <> id),
  CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE budget.organization_unit (
  id bigserial PRIMARY KEY, reporting_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id),
  parent_id bigint REFERENCES budget.organization_unit(id), unit_key text NOT NULL, display_name text NOT NULL,
  unit_type text NOT NULL, effective_from date NOT NULL, effective_to date,
  UNIQUE (reporting_entity_id, unit_key, effective_from), CHECK (parent_id IS NULL OR parent_id <> id),
  CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE budget.fiscal_period (
  id bigserial PRIMARY KEY, municipality_id bigint NOT NULL REFERENCES budget.municipality(id), label text NOT NULL,
  start_date date NOT NULL, end_date date NOT NULL, period_kind text NOT NULL,
  UNIQUE (municipality_id, start_date, end_date, period_kind), CHECK (end_date >= start_date)
);

CREATE TABLE budget.fund (
  id bigserial PRIMARY KEY, reporting_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id),
  parent_id bigint REFERENCES budget.fund(id), fund_key text NOT NULL, display_name text NOT NULL, fund_type text NOT NULL,
  effective_from date NOT NULL, effective_to date, UNIQUE (reporting_entity_id, fund_key, effective_from),
  CHECK (parent_id IS NULL OR parent_id <> id), CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE budget.measure_unit (
  id bigserial PRIMARY KEY, code text NOT NULL UNIQUE, display_name text NOT NULL, unit_kind text NOT NULL,
  currency_code text, scale numeric(20,8) NOT NULL DEFAULT 1 CHECK (scale > 0), denominator_text text
);
CREATE TABLE budget.amount_type (id bigserial PRIMARY KEY, code text NOT NULL UNIQUE, display_name text NOT NULL);
CREATE TABLE budget.normalized_category (
  id bigserial PRIMARY KEY, taxonomy_version text NOT NULL, category_key text NOT NULL,
  parent_id bigint REFERENCES budget.normalized_category(id), domain text NOT NULL, display_name text NOT NULL,
  UNIQUE (taxonomy_version, category_key), CHECK (parent_id IS NULL OR parent_id <> id)
);

CREATE TABLE budget.document_period (
  id bigserial PRIMARY KEY, document_id bigint NOT NULL REFERENCES budget.source_document(id) ON DELETE CASCADE,
  fiscal_period_id bigint NOT NULL REFERENCES budget.fiscal_period(id),
  source_table_column_id bigint NOT NULL REFERENCES budget.source_table_column(id), period_role text NOT NULL,
  raw_column_label text NOT NULL, column_order integer NOT NULL CHECK (column_order >= 0),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (document_id, source_table_column_id, period_role)
);

CREATE TABLE budget.statement (
  id bigserial PRIMARY KEY, document_id bigint NOT NULL REFERENCES budget.source_document(id) ON DELETE CASCADE,
  reporting_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id), fund_id bigint REFERENCES budget.fund(id),
  statement_key text NOT NULL, statement_kind text NOT NULL, title text NOT NULL, scope_note text,
  source_table_id bigint REFERENCES budget.source_table(id), UNIQUE (document_id, statement_key)
);
CREATE TABLE budget.line_item (
  id bigserial PRIMARY KEY, statement_id bigint NOT NULL REFERENCES budget.statement(id) ON DELETE CASCADE,
  parent_id bigint REFERENCES budget.line_item(id), line_key text NOT NULL, row_order integer NOT NULL CHECK (row_order >= 0),
  raw_label text NOT NULL, display_label text, line_kind text NOT NULL,
  aggregation_role text NOT NULL CHECK (aggregation_role IN ('detail','subtotal','total','memo','non_additive')),
  organization_unit_id bigint REFERENCES budget.organization_unit(id), normalized_category_id bigint REFERENCES budget.normalized_category(id),
  source_row_id bigint REFERENCES budget.source_table_row(id), UNIQUE (statement_id, line_key), CHECK (parent_id IS NULL OR parent_id <> id)
);
CREATE TABLE budget.fact_derivation (
  id bigserial PRIMARY KEY, formula_code text NOT NULL, formula_text text NOT NULL,
  input_fact_ids bigint[] NOT NULL DEFAULT '{}', calculated_at timestamptz NOT NULL DEFAULT now(), software_version text NOT NULL
);
CREATE TABLE budget.fact (
  id bigserial PRIMARY KEY, line_item_id bigint NOT NULL REFERENCES budget.line_item(id) ON DELETE CASCADE,
  document_period_id bigint NOT NULL REFERENCES budget.document_period(id), amount_type_id bigint NOT NULL REFERENCES budget.amount_type(id),
  measure_unit_id bigint NOT NULL REFERENCES budget.measure_unit(id), value_numeric numeric(20,4), value_text text,
  value_state text NOT NULL CHECK (value_state IN ('reported','reported_zero','dash_unresolved','not_applicable','missing','suppressed')),
  is_reported boolean NOT NULL DEFAULT true, derivation_id bigint REFERENCES budget.fact_derivation(id),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (line_item_id, document_period_id, amount_type_id, measure_unit_id),
  CHECK ((value_state IN ('missing','not_applicable','suppressed','dash_unresolved') AND value_numeric IS NULL AND value_text IS NULL)
    OR (value_state NOT IN ('missing','not_applicable','suppressed','dash_unresolved') AND ((value_numeric IS NOT NULL)::integer + (value_text IS NOT NULL)::integer = 1))),
  CHECK ((is_reported AND derivation_id IS NULL) OR (NOT is_reported AND derivation_id IS NOT NULL))
);
CREATE TABLE budget.fact_source (
  fact_id bigint NOT NULL REFERENCES budget.fact(id) ON DELETE CASCADE,
  source_cell_id bigint NOT NULL REFERENCES budget.source_table_cell(id), source_role text NOT NULL,
  source_order integer NOT NULL DEFAULT 0 CHECK (source_order >= 0), PRIMARY KEY (fact_id, source_cell_id, source_role),
  CHECK (source_role IN ('reported_value','assessment_operand','rate_operand','denominator','label_context','derivation_input'))
);
CREATE TABLE budget.statement_relationship (
  parent_statement_id bigint NOT NULL REFERENCES budget.statement(id) ON DELETE CASCADE,
  child_statement_id bigint NOT NULL REFERENCES budget.statement(id) ON DELETE CASCADE, relationship_type text NOT NULL,
  PRIMARY KEY (parent_statement_id, child_statement_id, relationship_type), CHECK (parent_statement_id <> child_statement_id)
);

CREATE TABLE budget.capital_project (
  id bigserial PRIMARY KEY, municipality_id bigint NOT NULL REFERENCES budget.municipality(id), reporting_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id),
  project_key text NOT NULL, name text NOT NULL, description text, status text, location_text text,
  organization_unit_id bigint REFERENCES budget.organization_unit(id), effective_from date NOT NULL, effective_to date,
  UNIQUE (municipality_id, project_key, effective_from), CHECK (effective_to IS NULL OR effective_to >= effective_from)
);
CREATE TABLE budget.capital_project_alias (
  id bigserial PRIMARY KEY, capital_project_id bigint NOT NULL REFERENCES budget.capital_project(id), document_id bigint NOT NULL REFERENCES budget.source_document(id),
  raw_label text NOT NULL, review_status text NOT NULL DEFAULT 'unreviewed', UNIQUE (capital_project_id, document_id, raw_label)
);
CREATE TABLE budget.capital_project_fact (fact_id bigint PRIMARY KEY REFERENCES budget.fact(id) ON DELETE CASCADE, capital_project_id bigint NOT NULL REFERENCES budget.capital_project(id), funding_source_category_id bigint REFERENCES budget.normalized_category(id));
CREATE TABLE budget.capital_project_profile (
  id bigserial PRIMARY KEY, capital_project_id bigint NOT NULL REFERENCES budget.capital_project(id), document_id bigint NOT NULL REFERENCES budget.source_document(id),
  field_key text NOT NULL, raw_value text NOT NULL, normalized_value text, source_row_id bigint REFERENCES budget.source_table_row(id),
  source_page_id bigint REFERENCES budget.source_page(id), review_status text NOT NULL DEFAULT 'unreviewed', UNIQUE (capital_project_id, document_id, field_key)
);
CREATE TABLE budget.tax_class (
  id bigserial PRIMARY KEY, municipality_id bigint NOT NULL REFERENCES budget.municipality(id), parent_id bigint REFERENCES budget.tax_class(id),
  normalized_key text NOT NULL, raw_label text NOT NULL, residency text, property_use_class text, special_district text,
  effective_from date NOT NULL, effective_to date, UNIQUE (municipality_id, normalized_key, effective_from), CHECK (parent_id IS NULL OR parent_id <> id)
);
CREATE TABLE budget.rate_fact (fact_id bigint PRIMARY KEY REFERENCES budget.fact(id) ON DELETE CASCADE, tax_class_id bigint REFERENCES budget.tax_class(id), customer_class text, geography text, assessment_base numeric(20,4), denominator_definition text);
CREATE TABLE budget.debt_instrument (
  id bigserial PRIMARY KEY, reporting_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id), lender text, raw_label text NOT NULL,
  normalized_label text, instrument_type text, issue_date date, maturity_date date, effective_from date NOT NULL, effective_to date,
  CHECK (maturity_date IS NULL OR issue_date IS NULL OR maturity_date >= issue_date)
);
CREATE TABLE budget.debt_fact (fact_id bigint PRIMARY KEY REFERENCES budget.fact(id) ON DELETE CASCADE, debt_instrument_id bigint NOT NULL REFERENCES budget.debt_instrument(id), debt_measure text NOT NULL);
CREATE TABLE budget.reserve_fund (id bigserial PRIMARY KEY, reporting_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id), reserve_key text NOT NULL, name text NOT NULL, reserve_type text, effective_from date NOT NULL, effective_to date, UNIQUE (reporting_entity_id, reserve_key, effective_from));
CREATE TABLE budget.reserve_fact (fact_id bigint PRIMARY KEY REFERENCES budget.fact(id) ON DELETE CASCADE, reserve_fund_id bigint NOT NULL REFERENCES budget.reserve_fund(id), movement_type text NOT NULL);

CREATE TABLE budget.import_batch (
  id bigserial PRIMARY KEY, document_id bigint NOT NULL REFERENCES budget.source_document(id), source_sha256 text NOT NULL,
  extractor_version text NOT NULL, started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
  status text NOT NULL CHECK (status IN ('started','completed','failed')), metrics_json jsonb NOT NULL DEFAULT '{}'::jsonb, error_json jsonb
);
CREATE TABLE budget.import_record_event (
  id bigserial PRIMARY KEY, batch_id bigint NOT NULL REFERENCES budget.import_batch(id) ON DELETE CASCADE, record_type text NOT NULL,
  natural_key text NOT NULL, content_hash text NOT NULL, event_type text NOT NULL CHECK (event_type IN ('added','changed','unchanged','removed','review_needed')),
  review_reason text, UNIQUE (batch_id, record_type, natural_key)
);
CREATE TABLE budget.normalization_decision (
  id bigserial PRIMARY KEY, source_entity_type text NOT NULL, source_entity_key text NOT NULL, target_entity_type text NOT NULL,
  target_entity_id bigint NOT NULL, decision text NOT NULL, rationale text NOT NULL, reviewer text NOT NULL,
  decided_at timestamptz NOT NULL DEFAULT now(), taxonomy_version text
);
CREATE TABLE budget.reconciliation_result (
  id bigserial PRIMARY KEY, statement_id bigint REFERENCES budget.statement(id), fiscal_period_id bigint REFERENCES budget.fiscal_period(id),
  check_type text NOT NULL, calculated_value numeric(20,4), reported_value numeric(20,4), difference numeric(20,4),
  tolerance numeric(20,4), passed boolean, input_fact_ids bigint[] NOT NULL DEFAULT '{}'
);
CREATE TABLE budget.review_issue (
  id bigserial PRIMARY KEY, review_key text NOT NULL UNIQUE, reconciliation_result_id bigint REFERENCES budget.reconciliation_result(id),
  subject_record_type text NOT NULL, subject_natural_key text NOT NULL, issue_code text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('low','medium','high','critical')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_review','resolved','superseded')),
  title text NOT NULL, description text NOT NULL, publication_effect text NOT NULL, required_resolution text NOT NULL,
  prohibited_action text NOT NULL, assignee text, created_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz,
  CHECK (issue_code IN ('reported_calculation_variance','reported_dash_with_calculated_balance','reported_dash_with_nonzero_calculated_balance')),
  CHECK ((status = 'resolved') = (resolved_at IS NOT NULL))
);
CREATE TABLE budget.review_issue_evidence (
  id bigserial PRIMARY KEY, review_issue_id bigint NOT NULL REFERENCES budget.review_issue(id) ON DELETE CASCADE,
  source_cell_id bigint REFERENCES budget.source_table_cell(id), reconciliation_result_id bigint REFERENCES budget.reconciliation_result(id),
  evidence_role text NOT NULL, evidence_order integer NOT NULL DEFAULT 0, notes text,
  CHECK (source_cell_id IS NOT NULL OR reconciliation_result_id IS NOT NULL)
);
CREATE TABLE budget.review_decision (
  id bigserial PRIMARY KEY, review_issue_id bigint NOT NULL REFERENCES budget.review_issue(id), decision_code text NOT NULL,
  rationale text NOT NULL, reviewer text NOT NULL, decided_at timestamptz NOT NULL DEFAULT now(),
  authoritative_source_document_id bigint REFERENCES budget.source_document(id), supersedes_decision_id bigint REFERENCES budget.review_decision(id)
);
CREATE TABLE budget.review_issue_allowed_decision (
  issue_code text NOT NULL,
  decision_code text NOT NULL,
  PRIMARY KEY (issue_code, decision_code)
);
CREATE TABLE budget.publication_snapshot (
  id bigserial PRIMARY KEY, municipality_id bigint NOT NULL REFERENCES budget.municipality(id), release_label text NOT NULL,
  taxonomy_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), source_document_ids bigint[] NOT NULL,
  status text NOT NULL CHECK (status IN ('draft','published','superseded')), UNIQUE (municipality_id, release_label)
);
CREATE TABLE budget.publication_fact (snapshot_id bigint NOT NULL REFERENCES budget.publication_snapshot(id) ON DELETE CASCADE, fact_id bigint NOT NULL REFERENCES budget.fact(id), PRIMARY KEY (snapshot_id, fact_id));

INSERT INTO budget.measure_unit (code, display_name, unit_kind, currency_code, scale, denominator_text) VALUES
  ('cad','Canadian dollars','currency','CAD',1,NULL), ('percent','Percent','rate',NULL,0.01,'100'),
  ('count','Count','count',NULL,1,NULL), ('cad_per_100_assessed','CAD per $100 assessed','rate','CAD',1,'100 assessed dollars')
ON CONFLICT (code) DO NOTHING;
INSERT INTO budget.amount_type (code, display_name) VALUES
  ('budget','Budget'),('forecast','Forecast'),('actual','Actual'),('balance','Balance'),('principal','Principal'),
  ('interest','Interest'),('gross','Gross'),('funding_deduction','Funding deduction'),('net','Net')
ON CONFLICT (code) DO NOTHING;
INSERT INTO budget.review_issue_allowed_decision (issue_code, decision_code) VALUES
  ('reported_calculation_variance','authoritative_clarification'),
  ('reported_calculation_variance','accept_reported_with_warning'),
  ('reported_calculation_variance','corrected_source'),
  ('reported_dash_with_calculated_balance','confirm_zero'),
  ('reported_dash_with_calculated_balance','confirm_not_applicable'),
  ('reported_dash_with_calculated_balance','retain_unresolved_dash'),
  ('reported_dash_with_calculated_balance','corrected_source'),
  ('reported_dash_with_nonzero_calculated_balance','authoritative_clarification'),
  ('reported_dash_with_nonzero_calculated_balance','accept_derived_with_warning'),
  ('reported_dash_with_nonzero_calculated_balance','retain_unresolved_dash'),
  ('reported_dash_with_nonzero_calculated_balance','corrected_source')
ON CONFLICT (issue_code, decision_code) DO NOTHING;

CREATE INDEX idx_budget_source_page_document ON budget.source_page(document_id);
CREATE INDEX idx_budget_source_row_table ON budget.source_table_row(source_table_id);
CREATE INDEX idx_budget_source_cell_row ON budget.source_table_cell(source_row_id);
CREATE INDEX idx_budget_document_period_fiscal ON budget.document_period(fiscal_period_id);
CREATE INDEX idx_budget_fact_period ON budget.fact(document_period_id);
CREATE INDEX idx_budget_fact_review ON budget.fact(review_status);
CREATE INDEX idx_budget_line_item_category ON budget.line_item(normalized_category_id);
CREATE INDEX idx_budget_line_item_org ON budget.line_item(organization_unit_id);
CREATE INDEX idx_budget_statement_kind ON budget.statement(statement_kind);
CREATE INDEX idx_budget_review_issue_status ON budget.review_issue(status, severity);
CREATE INDEX idx_budget_publication_fact_fact ON budget.publication_fact(fact_id);
CREATE INDEX idx_budget_source_document_municipality ON budget.source_document(municipality_id);
CREATE INDEX idx_budget_fiscal_period_municipality_dates ON budget.fiscal_period(municipality_id, start_date, end_date);
CREATE INDEX idx_budget_statement_entity_kind ON budget.statement(reporting_entity_id, statement_kind);
CREATE INDEX idx_budget_capital_project_municipality ON budget.capital_project(municipality_id, reporting_entity_id);
CREATE INDEX idx_budget_capital_project_fact_project ON budget.capital_project_fact(capital_project_id, fact_id);
CREATE INDEX idx_budget_publication_snapshot_municipality ON budget.publication_snapshot(municipality_id, status);

CREATE FUNCTION budget.prevent_raw_source_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE allowed_columns text[] := CASE WHEN TG_NARGS = 0 OR TG_ARGV[0] = '' THEN '{}'::text[] ELSE string_to_array(TG_ARGV[0], ',') END;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'raw source records are append-only';
  END IF;
  IF (to_jsonb(NEW) - allowed_columns) IS DISTINCT FROM (to_jsonb(OLD) - allowed_columns) THEN
    RAISE EXCEPTION 'raw source content is immutable';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_budget_source_document_immutable BEFORE UPDATE OR DELETE ON budget.source_document
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('status,retrieved_at');
CREATE TRIGGER trg_budget_source_page_immutable BEFORE UPDATE OR DELETE ON budget.source_page
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('review_status');
CREATE TRIGGER trg_budget_source_table_immutable BEFORE UPDATE OR DELETE ON budget.source_table
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('extraction_status,review_status');
CREATE TRIGGER trg_budget_source_table_page_immutable BEFORE UPDATE OR DELETE ON budget.source_table_page
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('');
CREATE TRIGGER trg_budget_source_table_column_immutable BEFORE UPDATE OR DELETE ON budget.source_table_column
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('review_status');
CREATE TRIGGER trg_budget_source_table_row_immutable BEFORE UPDATE OR DELETE ON budget.source_table_row
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('');
CREATE TRIGGER trg_budget_source_table_cell_immutable BEFORE UPDATE OR DELETE ON budget.source_table_cell
FOR EACH ROW EXECUTE FUNCTION budget.prevent_raw_source_mutation('');

CREATE FUNCTION budget.validate_hierarchy_cycle() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_column text := TG_ARGV[0]; parent_value bigint; cycle_found boolean;
BEGIN
  parent_value := (to_jsonb(NEW) ->> parent_column)::bigint;
  IF parent_value IS NULL THEN RETURN NEW; END IF;
  EXECUTE format(
    'WITH RECURSIVE ancestors AS (
       SELECT id, %1$I AS parent_id FROM budget.%2$I WHERE id = $1
       UNION ALL
       SELECT item.id, item.%1$I FROM budget.%2$I item JOIN ancestors ON item.id = ancestors.parent_id
     ) SELECT EXISTS (SELECT 1 FROM ancestors WHERE id = $2)',
    parent_column, TG_TABLE_NAME
  ) INTO cycle_found USING parent_value, NEW.id;
  IF cycle_found THEN RAISE EXCEPTION 'hierarchy cycle detected in budget.%', TG_TABLE_NAME; END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_budget_reporting_entity_no_cycle AFTER INSERT OR UPDATE OF parent_entity_id ON budget.reporting_entity
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_hierarchy_cycle('parent_entity_id');
CREATE CONSTRAINT TRIGGER trg_budget_organization_unit_no_cycle AFTER INSERT OR UPDATE OF parent_id ON budget.organization_unit
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_hierarchy_cycle('parent_id');
CREATE CONSTRAINT TRIGGER trg_budget_fund_no_cycle AFTER INSERT OR UPDATE OF parent_id ON budget.fund
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_hierarchy_cycle('parent_id');
CREATE CONSTRAINT TRIGGER trg_budget_category_no_cycle AFTER INSERT OR UPDATE OF parent_id ON budget.normalized_category
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_hierarchy_cycle('parent_id');
CREATE CONSTRAINT TRIGGER trg_budget_line_item_no_cycle AFTER INSERT OR UPDATE OF parent_id ON budget.line_item
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_hierarchy_cycle('parent_id');

CREATE FUNCTION budget.validate_cross_table_links() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_table_id bigint; expected_document_id bigint;
BEGIN
  IF TG_TABLE_NAME = 'source_table_cell' THEN
    SELECT source_table_id INTO expected_table_id FROM budget.source_table_row WHERE id = NEW.source_row_id;
    IF NOT EXISTS (SELECT 1 FROM budget.source_table_column WHERE id = NEW.source_table_column_id AND source_table_id = expected_table_id) THEN
      RAISE EXCEPTION 'cell row and column must belong to the same source table';
    END IF;
  ELSIF TG_TABLE_NAME = 'document_period' THEN
    SELECT st.document_id INTO expected_document_id FROM budget.source_table_column c JOIN budget.source_table st ON st.id = c.source_table_id WHERE c.id = NEW.source_table_column_id;
    IF expected_document_id IS DISTINCT FROM NEW.document_id THEN RAISE EXCEPTION 'document period column must belong to the same document'; END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_budget_cell_same_table AFTER INSERT OR UPDATE ON budget.source_table_cell DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_cross_table_links();
CREATE CONSTRAINT TRIGGER trg_budget_period_same_document AFTER INSERT OR UPDATE ON budget.document_period DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION budget.validate_cross_table_links();

CREATE FUNCTION budget.validate_source_table_page_document() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM budget.source_table t
    JOIN budget.source_page p ON p.document_id = t.document_id
    WHERE t.id = NEW.source_table_id AND p.id = NEW.source_page_id
  ) THEN
    RAISE EXCEPTION 'source table and page must belong to the same document';
  END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_budget_table_page_same_document
AFTER INSERT OR UPDATE ON budget.source_table_page DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_source_table_page_document();

CREATE FUNCTION budget.assert_reported_fact_source(checked_fact_id bigint) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM budget.fact WHERE id = checked_fact_id AND is_reported)
     AND NOT EXISTS (SELECT 1 FROM budget.fact_source WHERE fact_id = checked_fact_id AND source_role = 'reported_value') THEN
    RAISE EXCEPTION 'reported fact % requires reported_value source evidence', checked_fact_id;
  END IF;
END $$;
CREATE FUNCTION budget.validate_reported_fact_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME = 'fact' THEN
    PERFORM budget.assert_reported_fact_source(NEW.id);
  ELSIF TG_OP = 'DELETE' THEN
    PERFORM budget.assert_reported_fact_source(OLD.fact_id);
  ELSIF TG_OP = 'UPDATE' THEN
    PERFORM budget.assert_reported_fact_source(OLD.fact_id);
    IF NEW.fact_id IS DISTINCT FROM OLD.fact_id THEN
      PERFORM budget.assert_reported_fact_source(NEW.fact_id);
    END IF;
  ELSE
    PERFORM budget.assert_reported_fact_source(NEW.fact_id);
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE CONSTRAINT TRIGGER trg_budget_reported_fact_source_fact
AFTER INSERT OR UPDATE ON budget.fact DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_reported_fact_source();
CREATE CONSTRAINT TRIGGER trg_budget_reported_fact_source_evidence
AFTER INSERT OR UPDATE OR DELETE ON budget.fact_source DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_reported_fact_source();

CREATE FUNCTION budget.validate_resolved_review_issue() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'resolved' AND NOT EXISTS (
    SELECT 1
    FROM budget.review_decision d
    JOIN budget.review_issue_allowed_decision a
      ON a.issue_code = NEW.issue_code AND a.decision_code = d.decision_code
    WHERE d.review_issue_id = NEW.id
  ) THEN
    RAISE EXCEPTION 'resolved review issue % requires an allowed review decision', NEW.review_key;
  END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_budget_resolved_issue_decision
AFTER INSERT OR UPDATE ON budget.review_issue DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_resolved_review_issue();

CREATE FUNCTION budget.prevent_review_decision_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'review decisions are append-only; insert a superseding decision';
END $$;
CREATE TRIGGER trg_budget_review_decision_append_only
BEFORE UPDATE OR DELETE ON budget.review_decision
FOR EACH ROW EXECUTE FUNCTION budget.prevent_review_decision_mutation();

CREATE FUNCTION budget.validate_publication_fact_municipality() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE checked_snapshot_id bigint;
BEGIN
  IF TG_TABLE_NAME = 'publication_snapshot' THEN
    checked_snapshot_id := NEW.id;
  ELSE
    checked_snapshot_id := NEW.snapshot_id;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM budget.publication_snapshot ps
    CROSS JOIN LATERAL unnest(ps.source_document_ids) source_id
    LEFT JOIN budget.source_document source_document ON source_document.id = source_id
    WHERE ps.id = checked_snapshot_id
      AND (source_document.id IS NULL OR source_document.municipality_id <> ps.municipality_id)
  ) THEN
    RAISE EXCEPTION 'publication snapshot % contains an invalid source document', checked_snapshot_id;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM budget.publication_fact pf
    JOIN budget.publication_snapshot ps ON ps.id = pf.snapshot_id
    JOIN budget.fact f ON f.id = pf.fact_id
    JOIN budget.line_item li ON li.id = f.line_item_id
    JOIN budget.statement s ON s.id = li.statement_id
    JOIN budget.source_document d ON d.id = s.document_id
    WHERE pf.snapshot_id = checked_snapshot_id
      AND (d.municipality_id <> ps.municipality_id OR NOT d.id = ANY(ps.source_document_ids))
  ) THEN
    RAISE EXCEPTION 'publication snapshot % contains a fact outside its municipality or source documents', checked_snapshot_id;
  END IF;
  IF EXISTS (
    SELECT 1 FROM budget.publication_fact pf
    JOIN budget.fact f ON f.id = pf.fact_id
    WHERE pf.snapshot_id = checked_snapshot_id AND f.review_status <> 'approved'
  ) THEN
    RAISE EXCEPTION 'publication snapshot % contains an unapproved fact', checked_snapshot_id;
  END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_budget_publication_fact_municipality
AFTER INSERT OR UPDATE ON budget.publication_fact DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_publication_fact_municipality();
CREATE CONSTRAINT TRIGGER trg_budget_publication_snapshot_municipality
AFTER INSERT OR UPDATE OF municipality_id, source_document_ids ON budget.publication_snapshot DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_publication_fact_municipality();

CREATE FUNCTION budget.prevent_published_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME = 'publication_snapshot' THEN
    IF OLD.status = 'published' THEN RAISE EXCEPTION 'published snapshots are immutable'; END IF;
  ELSIF TG_TABLE_NAME = 'publication_fact' THEN
    IF EXISTS (SELECT 1 FROM budget.publication_snapshot WHERE id = COALESCE(NEW.snapshot_id, OLD.snapshot_id) AND status = 'published')
    THEN RAISE EXCEPTION 'published snapshot membership is immutable'; END IF;
  ELSIF TG_TABLE_NAME = 'fact' THEN
    IF EXISTS (SELECT 1 FROM budget.publication_fact pf JOIN budget.publication_snapshot ps ON ps.id = pf.snapshot_id WHERE pf.fact_id = OLD.id AND ps.status = 'published')
    THEN RAISE EXCEPTION 'published facts are immutable'; END IF;
  ELSE
    IF EXISTS (SELECT 1 FROM budget.publication_fact pf JOIN budget.publication_snapshot ps ON ps.id = pf.snapshot_id WHERE pf.fact_id = OLD.fact_id AND ps.status = 'published')
    THEN RAISE EXCEPTION 'published fact provenance is immutable'; END IF;
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER trg_budget_published_snapshot_immutable BEFORE UPDATE OR DELETE ON budget.publication_snapshot
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();
CREATE TRIGGER trg_budget_published_membership_immutable BEFORE INSERT OR UPDATE OR DELETE ON budget.publication_fact
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();
CREATE TRIGGER trg_budget_published_fact_immutable BEFORE UPDATE OR DELETE ON budget.fact
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();
CREATE TRIGGER trg_budget_published_fact_source_immutable BEFORE UPDATE OR DELETE ON budget.fact_source
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();

CREATE VIEW budget.v_published_facts AS
SELECT ps.id AS snapshot_id, ps.release_label, ps.taxonomy_version,
  m.id AS municipality_id, m.slug AS municipality_slug,
  re.id AS reporting_entity_id, re.display_name AS reporting_entity_name,
  fp.id AS fiscal_period_id, fp.label AS fiscal_period_label, fp.start_date, fp.end_date,
  s.id AS statement_id, s.statement_key, s.statement_kind, s.title AS statement_title,
  li.id AS line_item_id, li.line_key, li.parent_id AS parent_line_item_id, li.row_order,
  li.raw_label, li.display_label, li.line_kind, li.aggregation_role,
  li.organization_unit_id, li.normalized_category_id, nc.category_key, nc.domain AS category_domain,
  f.id AS fact_id, at.code AS amount_type, mu.code AS measure_unit,
  f.value_numeric, f.value_text, f.value_state, f.is_reported,
  evidence.source_cell_ids, evidence.source_roles
FROM budget.publication_snapshot ps
JOIN budget.municipality m ON m.id = ps.municipality_id
JOIN budget.publication_fact pf ON pf.snapshot_id = ps.id
JOIN budget.fact f ON f.id = pf.fact_id AND f.review_status = 'approved'
JOIN budget.line_item li ON li.id = f.line_item_id
JOIN budget.statement s ON s.id = li.statement_id
JOIN budget.reporting_entity re ON re.id = s.reporting_entity_id
JOIN budget.document_period dp ON dp.id = f.document_period_id
JOIN budget.fiscal_period fp ON fp.id = dp.fiscal_period_id
JOIN budget.amount_type at ON at.id = f.amount_type_id
JOIN budget.measure_unit mu ON mu.id = f.measure_unit_id
LEFT JOIN budget.normalized_category nc ON nc.id = li.normalized_category_id
LEFT JOIN LATERAL (
  SELECT array_agg(fs.source_cell_id ORDER BY fs.source_order, fs.source_cell_id) AS source_cell_ids,
    array_agg(fs.source_role ORDER BY fs.source_order, fs.source_cell_id) AS source_roles
  FROM budget.fact_source fs WHERE fs.fact_id = f.id
) evidence ON true
WHERE ps.status = 'published';

CREATE VIEW budget.v_operating_flow AS
SELECT * FROM budget.v_published_facts
WHERE statement_kind = 'operating' AND aggregation_role = 'detail';

CREATE VIEW budget.v_capital_investment AS
SELECT pf.*, cpf.capital_project_id, cp.project_key, cp.name AS project_name,
  cpf.funding_source_category_id
FROM budget.v_published_facts pf
JOIN budget.capital_project_fact cpf ON cpf.fact_id = pf.fact_id
JOIN budget.capital_project cp ON cp.id = cpf.capital_project_id
WHERE pf.amount_type IN ('gross','funding_deduction','net');

CREATE VIEW budget.v_revenue_sources AS
SELECT * FROM budget.v_published_facts
WHERE aggregation_role = 'detail'
  AND category_domain IN ('revenue','tax','rate','transfer','fee','financing');

CREATE VIEW budget.v_period_comparison AS
SELECT current_fact.snapshot_id, current_fact.taxonomy_version,
  current_fact.municipality_id, current_fact.reporting_entity_id,
  current_fact.statement_key, current_fact.line_key, current_fact.category_key,
  current_fact.amount_type, current_fact.measure_unit,
  prior_fact.fiscal_period_id AS prior_fiscal_period_id,
  prior_fact.fiscal_period_label AS prior_fiscal_period_label,
  prior_fact.value_numeric AS prior_value_numeric,
  current_fact.fiscal_period_id AS current_fiscal_period_id,
  current_fact.fiscal_period_label AS current_fiscal_period_label,
  current_fact.value_numeric AS current_value_numeric,
  current_fact.value_numeric - prior_fact.value_numeric AS numeric_change
FROM budget.v_published_facts current_fact
JOIN budget.v_published_facts prior_fact
  ON prior_fact.snapshot_id = current_fact.snapshot_id
 AND prior_fact.taxonomy_version = current_fact.taxonomy_version
 AND prior_fact.municipality_id = current_fact.municipality_id
 AND prior_fact.reporting_entity_id = current_fact.reporting_entity_id
 AND prior_fact.statement_key = current_fact.statement_key
 AND prior_fact.line_key = current_fact.line_key
 AND prior_fact.amount_type = current_fact.amount_type
 AND prior_fact.measure_unit = current_fact.measure_unit
 AND prior_fact.end_date < current_fact.start_date
WHERE prior_fact.value_numeric IS NOT NULL AND current_fact.value_numeric IS NOT NULL;

CREATE VIEW budget.v_extraction_coverage AS
SELECT d.id AS document_id, d.title,
  count(DISTINCT t.id) AS source_table_count, count(DISTINCT r.id) AS source_row_count,
  count(DISTINCT c.id) AS source_cell_count, count(DISTINCT f.id) AS fact_count,
  count(DISTINCT f.id) FILTER (WHERE f.review_status = 'approved') AS approved_fact_count,
  count(DISTINCT i.id) FILTER (WHERE i.status IN ('open','in_review')) AS unresolved_issue_count
FROM budget.source_document d
LEFT JOIN budget.source_table t ON t.document_id = d.id
LEFT JOIN budget.source_table_row r ON r.source_table_id = t.id
LEFT JOIN budget.source_table_cell c ON c.source_row_id = r.id
LEFT JOIN budget.fact_source fs ON fs.source_cell_id = c.id
LEFT JOIN budget.fact f ON f.id = fs.fact_id
LEFT JOIN budget.review_issue i ON i.subject_natural_key = d.sha256
GROUP BY d.id, d.title;
