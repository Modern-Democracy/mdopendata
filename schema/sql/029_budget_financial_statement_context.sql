BEGIN;

CREATE TABLE budget.document_accounting_context (
  document_id bigint PRIMARY KEY REFERENCES budget.source_document(id) ON DELETE CASCADE,
  reporting_framework text NOT NULL CHECK (reporting_framework IN (
    'canadian_accounting_standards_for_the_public_sector',
    'canadian_accounting_standards_for_pension_plans',
    'other',
    'unknown'
  )),
  accounting_basis text NOT NULL CHECK (accounting_basis IN ('full_accrual','modified_accrual','cash','other','unknown')),
  reporting_date date NOT NULL,
  assurance_status text NOT NULL CHECK (assurance_status IN ('audited','reviewed','unaudited','unknown')),
  audit_opinion text NOT NULL CHECK (audit_opinion IN ('unmodified','qualified','adverse','disclaimer','not_applicable','unknown')),
  auditor_name text,
  auditor_report_date date,
  consolidation_scope text NOT NULL CHECK (consolidation_scope IN (
    'consolidated','separate_component_statement','related_non_additive_plan','other','unknown'
  )),
  authority_rank smallint NOT NULL DEFAULT 0 CHECK (authority_rank BETWEEN 0 AND 100),
  authority_basis text NOT NULL,
  publication_status text NOT NULL DEFAULT 'unknown' CHECK (publication_status IN (
    'unknown','municipally_published','municipally_adopted','final_release','superseded'
  )),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  reviewed_at timestamptz,
  CHECK ((review_status = 'approved') = (reviewed_at IS NOT NULL)),
  CHECK (auditor_report_date IS NULL OR assurance_status IN ('audited','reviewed'))
);

CREATE TABLE budget.statement_class (
  id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  display_name text NOT NULL,
  statement_domain text NOT NULL CHECK (statement_domain IN ('public_sector','pension_plan','shared')),
  flow_semantics text NOT NULL CHECK (flow_semantics IN ('position','flow','movement','schedule')),
  active boolean NOT NULL DEFAULT true
);

INSERT INTO budget.statement_class (code,display_name,statement_domain,flow_semantics) VALUES
  ('financial_position','Financial position','shared','position'),
  ('operations','Operations','public_sector','flow'),
  ('changes_in_net_debt','Changes in net debt','public_sector','movement'),
  ('cash_flow','Cash flow','public_sector','flow'),
  ('changes_in_net_assets_available_for_benefits','Changes in net assets available for benefits','pension_plan','movement'),
  ('changes_in_pension_obligations','Changes in pension obligations','pension_plan','movement'),
  ('tangible_capital_assets','Tangible capital assets','public_sector','schedule'),
  ('segmented_disclosure','Segmented disclosure','public_sector','schedule'),
  ('note_schedule','Note schedule','shared','schedule')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE budget.statement
  ADD COLUMN statement_class_id bigint REFERENCES budget.statement_class(id);

CREATE TABLE budget.reporting_entity_relationship (
  id bigserial PRIMARY KEY,
  municipality_id bigint NOT NULL REFERENCES budget.municipality(id),
  parent_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id),
  child_entity_id bigint NOT NULL REFERENCES budget.reporting_entity(id),
  relationship_type text NOT NULL CHECK (relationship_type IN (
    'consolidated_component','related_pension_plan','administrative_parent'
  )),
  effective_from date NOT NULL,
  effective_to date,
  source_document_id bigint REFERENCES budget.source_document(id),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  rationale text NOT NULL,
  CHECK (parent_entity_id <> child_entity_id),
  CHECK (effective_to IS NULL OR effective_to >= effective_from),
  CHECK (review_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  UNIQUE (municipality_id,parent_entity_id,child_entity_id,relationship_type,effective_from)
);

CREATE UNIQUE INDEX uq_budget_reporting_entity_relationship_active
ON budget.reporting_entity_relationship (municipality_id,parent_entity_id,child_entity_id,relationship_type)
WHERE effective_to IS NULL;

CREATE FUNCTION budget.validate_reporting_entity_relationship() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  parent_municipality_id bigint;
  child_municipality_id bigint;
  document_municipality_id bigint;
BEGIN
  SELECT municipality_id INTO parent_municipality_id FROM budget.reporting_entity WHERE id=NEW.parent_entity_id;
  SELECT municipality_id INTO child_municipality_id FROM budget.reporting_entity WHERE id=NEW.child_entity_id;
  IF parent_municipality_id IS DISTINCT FROM NEW.municipality_id
     OR child_municipality_id IS DISTINCT FROM NEW.municipality_id THEN
    RAISE EXCEPTION 'reporting entity relationship must remain within one municipality';
  END IF;
  IF NEW.source_document_id IS NOT NULL THEN
    SELECT municipality_id INTO document_municipality_id FROM budget.source_document WHERE id=NEW.source_document_id;
    IF document_municipality_id IS DISTINCT FROM NEW.municipality_id THEN
      RAISE EXCEPTION 'reporting entity relationship source document must belong to the same municipality';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_budget_reporting_entity_relationship_compatibility
BEFORE INSERT OR UPDATE ON budget.reporting_entity_relationship
FOR EACH ROW EXECUTE FUNCTION budget.validate_reporting_entity_relationship();

CREATE TABLE budget.financial_observation_relationship (
  id bigserial PRIMARY KEY,
  municipality_id bigint NOT NULL REFERENCES budget.municipality(id),
  source_observation_id bigint NOT NULL REFERENCES budget.financial_observation(id) ON DELETE CASCADE,
  target_observation_id bigint NOT NULL REFERENCES budget.financial_observation(id) ON DELETE CASCADE,
  relationship_type text NOT NULL CHECK (relationship_type IN ('comparative_of','restates','supersedes','budget_equivalent')),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  review_status text NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (source_observation_id <> target_observation_id),
  CHECK (review_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  UNIQUE (source_observation_id,target_observation_id,relationship_type)
);

CREATE FUNCTION budget.validate_financial_observation_relationship() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  source_municipality_id bigint;
  target_municipality_id bigint;
  source_entity_id bigint;
  target_entity_id bigint;
  source_unit_id bigint;
  target_unit_id bigint;
  source_period_start date;
  source_period_end date;
  target_period_start date;
  target_period_end date;
  source_amount_type text;
  target_amount_type text;
  source_statement_class text;
  target_statement_class text;
  source_flow_semantics text;
  target_flow_semantics text;
BEGIN
  SELECT re.municipality_id,s.reporting_entity_id,o.measure_unit_id,fp.start_date,fp.end_date,
         at.code,sc.code,sc.flow_semantics
  INTO source_municipality_id,source_entity_id,source_unit_id,source_period_start,source_period_end,
       source_amount_type,source_statement_class,source_flow_semantics
  FROM budget.financial_observation o
  JOIN budget.line_item li ON li.id=o.line_item_id
  JOIN budget.statement s ON s.id=li.statement_id
  JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
  JOIN budget.document_period dp ON dp.id=o.document_period_id
  JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
  JOIN budget.amount_type at ON at.id=o.amount_type_id
  LEFT JOIN budget.statement_class sc ON sc.id=s.statement_class_id
  WHERE o.id=NEW.source_observation_id;

  SELECT re.municipality_id,s.reporting_entity_id,o.measure_unit_id,fp.start_date,fp.end_date,
         at.code,sc.code,sc.flow_semantics
  INTO target_municipality_id,target_entity_id,target_unit_id,target_period_start,target_period_end,
       target_amount_type,target_statement_class,target_flow_semantics
  FROM budget.financial_observation o
  JOIN budget.line_item li ON li.id=o.line_item_id
  JOIN budget.statement s ON s.id=li.statement_id
  JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
  JOIN budget.document_period dp ON dp.id=o.document_period_id
  JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
  JOIN budget.amount_type at ON at.id=o.amount_type_id
  LEFT JOIN budget.statement_class sc ON sc.id=s.statement_class_id
  WHERE o.id=NEW.target_observation_id;

  IF source_municipality_id IS NULL OR target_municipality_id IS NULL THEN
    RAISE EXCEPTION 'financial observation relationship requires existing observations';
  END IF;
  IF source_municipality_id IS DISTINCT FROM NEW.municipality_id
     OR target_municipality_id IS DISTINCT FROM NEW.municipality_id THEN
    RAISE EXCEPTION 'financial observation relationship must remain within one municipality';
  END IF;

  IF NEW.relationship_type='budget_equivalent' AND (
    source_entity_id IS DISTINCT FROM target_entity_id
    OR source_unit_id IS DISTINCT FROM target_unit_id
    OR source_period_start IS DISTINCT FROM target_period_start
    OR source_period_end IS DISTINCT FROM target_period_end
    OR source_amount_type IS DISTINCT FROM 'budget'
    OR target_amount_type IS DISTINCT FROM 'actual'
    OR source_statement_class IS DISTINCT FROM target_statement_class
    OR source_statement_class IS DISTINCT FROM 'operations'
    OR source_flow_semantics IS DISTINCT FROM 'flow'
    OR target_flow_semantics IS DISTINCT FROM 'flow'
  ) THEN
    RAISE EXCEPTION 'budget_equivalent observations require identical municipality, entity, period, unit, operations class, and budget-to-actual roles';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_budget_financial_observation_relationship_compatibility
BEFORE INSERT OR UPDATE ON budget.financial_observation_relationship
FOR EACH ROW EXECUTE FUNCTION budget.validate_financial_observation_relationship();

ALTER TABLE budget.review_issue DROP CONSTRAINT IF EXISTS review_issue_issue_code_check;
ALTER TABLE budget.review_issue ADD CONSTRAINT review_issue_issue_code_check CHECK (issue_code IN (
  'reported_calculation_variance',
  'reported_dash_with_calculated_balance',
  'reported_dash_with_nonzero_calculated_balance',
  'source_authority_conflict',
  'filename_reporting_date_conflict',
  'comparative_variance',
  'accounting_scope_mismatch',
  'unsupported_statement_pattern'
));

INSERT INTO budget.review_issue_allowed_decision (issue_code,decision_code) VALUES
  ('source_authority_conflict','approve_source_page_precedence'),
  ('source_authority_conflict','retain_publication_block'),
  ('source_authority_conflict','superseded_by_authoritative_source'),
  ('filename_reporting_date_conflict','approve_source_reporting_date'),
  ('filename_reporting_date_conflict','retain_unresolved'),
  ('comparative_variance','retain_document_owned_values'),
  ('comparative_variance','approve_restatement_relationship'),
  ('comparative_variance','superseded_by_corrected_source'),
  ('accounting_scope_mismatch','reject_relationship'),
  ('accounting_scope_mismatch','approve_non_additive_relationship'),
  ('unsupported_statement_pattern','extend_schema_after_spike'),
  ('unsupported_statement_pattern','retain_unmapped_with_publication_block')
ON CONFLICT (issue_code,decision_code) DO NOTHING;

CREATE INDEX idx_budget_document_accounting_reporting_date
ON budget.document_accounting_context (reporting_date,consolidation_scope);
CREATE INDEX idx_budget_statement_class ON budget.statement(statement_class_id);
CREATE INDEX idx_budget_reporting_entity_relationship_child
ON budget.reporting_entity_relationship (child_entity_id,relationship_type);
CREATE INDEX idx_budget_financial_observation_relationship_target
ON budget.financial_observation_relationship (target_observation_id,relationship_type,review_status);

COMMIT;
