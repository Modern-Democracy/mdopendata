BEGIN;

CREATE TABLE budget.financial_statement_line_category_assignment (
  id bigserial PRIMARY KEY,
  line_item_id bigint NOT NULL REFERENCES budget.line_item(id) ON DELETE CASCADE,
  statement_class_id bigint NOT NULL REFERENCES budget.statement_class(id),
  normalized_category_id bigint NOT NULL REFERENCES budget.normalized_category(id),
  taxonomy_version text NOT NULL,
  assignment_status text NOT NULL DEFAULT 'proposed' CHECK (assignment_status IN ('proposed','approved','rejected','superseded')),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('exact_label','reviewed_rule','manual_review')),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  rationale text NOT NULL,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  CHECK (assignment_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  UNIQUE (line_item_id,statement_class_id,normalized_category_id,taxonomy_version)
);

CREATE UNIQUE INDEX uq_budget_financial_statement_line_category_active
ON budget.financial_statement_line_category_assignment (line_item_id,taxonomy_version)
WHERE assignment_status IN ('proposed','approved');

CREATE FUNCTION budget.validate_financial_statement_line_category_assignment() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  line_statement_class_id bigint;
  line_statement_class_code text;
  line_statement_flow_semantics text;
  category_taxonomy_version text;
BEGIN
  SELECT s.statement_class_id,sc.code,sc.flow_semantics
  INTO line_statement_class_id,line_statement_class_code,line_statement_flow_semantics
  FROM budget.line_item li
  JOIN budget.statement s ON s.id=li.statement_id
  LEFT JOIN budget.statement_class sc ON sc.id=s.statement_class_id
  WHERE li.id=NEW.line_item_id;
  SELECT taxonomy_version INTO category_taxonomy_version
  FROM budget.normalized_category WHERE id=NEW.normalized_category_id;
  IF line_statement_class_id IS DISTINCT FROM NEW.statement_class_id THEN
    RAISE EXCEPTION 'financial statement category assignment class must match the line statement class';
  END IF;
  IF line_statement_class_code IS DISTINCT FROM 'operations'
     OR line_statement_flow_semantics IS DISTINCT FROM 'flow' THEN
    RAISE EXCEPTION 'financial statement budget categories require an operations flow statement class';
  END IF;
  IF category_taxonomy_version IS DISTINCT FROM NEW.taxonomy_version THEN
    RAISE EXCEPTION 'financial statement category assignment taxonomy version must match the category';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_budget_financial_statement_line_category_compatibility
BEFORE INSERT OR UPDATE ON budget.financial_statement_line_category_assignment
FOR EACH ROW EXECUTE FUNCTION budget.validate_financial_statement_line_category_assignment();

CREATE FUNCTION budget.assert_financial_statement_snapshot_compatible(checked_snapshot_id bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  snapshot_status text;
BEGIN
  SELECT status INTO snapshot_status FROM budget.publication_snapshot WHERE id=checked_snapshot_id;
  IF snapshot_status IS DISTINCT FROM 'published' THEN RETURN; END IF;

  IF EXISTS (
    SELECT 1
    FROM budget.publication_snapshot ps
    JOIN unnest(ps.source_document_ids) source_document_id ON true
    JOIN budget.source_document document ON document.id=source_document_id
    LEFT JOIN budget.document_accounting_context context ON context.document_id=document.id
    WHERE ps.id=checked_snapshot_id
      AND document.document_kind='financial_statements'
      AND (context.document_id IS NULL
        OR context.review_status <> 'approved'
        OR context.publication_status NOT IN ('municipally_published','municipally_adopted','final_release'))
  ) THEN
    RAISE EXCEPTION 'published snapshot contains a financial statement document without approved publication authority';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM budget.publication_observation po
    JOIN budget.publication_snapshot ps ON ps.id=po.snapshot_id
    JOIN budget.financial_observation o ON o.id=po.observation_id
    JOIN budget.line_item li ON li.id=o.line_item_id
    JOIN budget.statement s ON s.id=li.statement_id
    JOIN budget.source_document document ON document.id=s.document_id
    LEFT JOIN budget.document_accounting_context context ON context.document_id=document.id
    WHERE po.snapshot_id=checked_snapshot_id
      AND document.document_kind='financial_statements'
      AND (s.document_id <> ALL(ps.source_document_ids)
        OR context.document_id IS NULL
        OR context.review_status <> 'approved'
        OR context.publication_status NOT IN ('municipally_published','municipally_adopted','final_release')
        OR s.statement_class_id IS NULL
        OR o.review_status <> 'approved')
  ) THEN
    RAISE EXCEPTION 'published financial statement observations require statement class and approved review status';
  END IF;
END $$;

CREATE FUNCTION budget.validate_financial_statement_snapshot_trigger() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='publication_snapshot' THEN
    PERFORM budget.assert_financial_statement_snapshot_compatible(NEW.id);
  ELSIF TG_OP='DELETE' THEN
    PERFORM budget.assert_financial_statement_snapshot_compatible(OLD.snapshot_id);
  ELSE
    PERFORM budget.assert_financial_statement_snapshot_compatible(NEW.snapshot_id);
  END IF;
  RETURN COALESCE(NEW,OLD);
END $$;

CREATE CONSTRAINT TRIGGER trg_budget_financial_statement_snapshot_compatibility
AFTER INSERT OR UPDATE OF status,source_document_ids ON budget.publication_snapshot
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION budget.validate_financial_statement_snapshot_trigger();

CREATE CONSTRAINT TRIGGER trg_budget_financial_statement_membership_compatibility
AFTER INSERT OR UPDATE OR DELETE ON budget.publication_observation
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION budget.validate_financial_statement_snapshot_trigger();

CREATE FUNCTION budget.validate_financial_statement_context_publication() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM budget.publication_snapshot ps
    WHERE ps.status='published' AND NEW.document_id=ANY(ps.source_document_ids)
  ) AND (
    NEW.review_status <> 'approved'
    OR NEW.publication_status NOT IN ('municipally_published','municipally_adopted','final_release')
  ) THEN
    RAISE EXCEPTION 'financial statement context for a published snapshot requires approved publication authority';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_budget_financial_statement_context_publication
BEFORE INSERT OR UPDATE ON budget.document_accounting_context
FOR EACH ROW EXECUTE FUNCTION budget.validate_financial_statement_context_publication();

CREATE VIEW budget.v_published_financial_statement_observations AS
SELECT published.*,
  context.reporting_framework,context.accounting_basis,context.reporting_date,
  context.assurance_status,context.audit_opinion,context.auditor_name,context.auditor_report_date,
  context.consolidation_scope,context.authority_rank,context.authority_basis,context.publication_status,
  sc.code AS statement_class,sc.display_name AS statement_class_name,
  sc.statement_domain,sc.flow_semantics,re.entity_type AS reporting_entity_type,
  category.category_key AS financial_statement_category_key,
  category.display_name AS financial_statement_category_name,
  category_assignment.taxonomy_version AS financial_statement_taxonomy_version,
  entity_relationship.relationships AS reporting_entity_relationships
FROM budget.v_published_financial_observations published
JOIN budget.document_accounting_context context ON context.document_id=published.source_document_id
JOIN budget.statement_class sc ON sc.id=(
  SELECT statement_class_id FROM budget.statement WHERE id=published.statement_id
)
JOIN budget.reporting_entity re ON re.id=published.reporting_entity_id
LEFT JOIN LATERAL (
  SELECT assignment.normalized_category_id,assignment.taxonomy_version
  FROM budget.financial_statement_line_category_assignment assignment
  WHERE assignment.line_item_id=published.line_item_id
    AND assignment.assignment_status='approved'
  ORDER BY assignment.id DESC LIMIT 1
) category_assignment ON true
LEFT JOIN budget.normalized_category category ON category.id=category_assignment.normalized_category_id
LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object(
    'relationship_type',relationship.relationship_type,
    'parent_entity_id',relationship.parent_entity_id,
    'child_entity_id',relationship.child_entity_id
  ) ORDER BY relationship.relationship_type,relationship.id) AS relationships
  FROM budget.reporting_entity_relationship relationship
  WHERE relationship.review_status='approved'
    AND relationship.municipality_id=published.municipality_id
    AND published.reporting_entity_id IN (relationship.parent_entity_id,relationship.child_entity_id)
    AND relationship.effective_from <= published.end_date
    AND (relationship.effective_to IS NULL OR relationship.effective_to >= published.start_date)
) entity_relationship ON true;

CREATE VIEW budget.v_budget_actual_comparison AS
SELECT relationship.id AS relationship_id,
  budget_observation.snapshot_id,budget_observation.release_label,budget_observation.municipality_id,
  budget_observation.reporting_entity_id,budget_observation.reporting_entity_name,
  budget_observation.fiscal_period_id,budget_observation.fiscal_period_label,
  budget_observation.statement_class,budget_observation.line_item_id,
  budget_observation.line_key,budget_observation.raw_label,
  budget_observation.observation_id AS budget_observation_id,
  budget_observation.value_numeric AS budget_value,
  actual_observation.observation_id AS actual_observation_id,
  actual_observation.value_numeric AS actual_value,
  actual_observation.value_numeric-budget_observation.value_numeric AS variance,
  CASE WHEN budget_observation.value_numeric=0 THEN NULL
    ELSE (actual_observation.value_numeric-budget_observation.value_numeric)/abs(budget_observation.value_numeric)*100 END AS variance_percent,
  relationship.rationale AS relationship_rationale
FROM budget.financial_observation_relationship relationship
JOIN budget.v_published_financial_statement_observations budget_observation
  ON budget_observation.observation_id=relationship.source_observation_id
JOIN budget.v_published_financial_statement_observations actual_observation
  ON actual_observation.observation_id=relationship.target_observation_id
 AND actual_observation.snapshot_id=budget_observation.snapshot_id
WHERE relationship.relationship_type='budget_equivalent'
  AND relationship.review_status='approved';

CREATE VIEW budget.v_financial_position AS
SELECT observation.*,false AS cross_entity_addition_allowed,
  'Financial position values are non-additive across reporting entities.'::text AS scope_warning
FROM budget.v_published_financial_statement_observations observation
WHERE observation.statement_class='financial_position';

CREATE VIEW budget.v_cash_flow AS
SELECT observation.*,false AS cross_entity_addition_allowed,
  'Cash-flow values are non-additive across reporting entities.'::text AS scope_warning
FROM budget.v_published_financial_statement_observations observation
WHERE observation.statement_class='cash_flow';

CREATE VIEW budget.v_pension_position AS
SELECT observation.*,false AS cross_entity_addition_allowed,
  'Pension-plan values are related but non-additive to municipal and utility totals.'::text AS scope_warning
FROM budget.v_published_financial_statement_observations observation
WHERE observation.statement_class='financial_position'
  AND observation.reporting_entity_type='pension_plan';

CREATE VIEW budget.v_holistic_finance_coverage AS
SELECT document.id AS document_id,document.title,document.sha256,
  context.reporting_date,context.consolidation_scope,context.assurance_status,
  context.publication_status,context.review_status AS accounting_context_review_status,
  page_counts.page_count,table_counts.table_count,row_counts.row_count,cell_counts.cell_count,
  observation_counts.observation_count,observation_counts.mapped_observation_count,
  publication_counts.published_observation_count,
  observation_counts.blocked_observation_count,
  issue_counts.unresolved_issue_count
FROM budget.source_document document
JOIN budget.document_accounting_context context ON context.document_id=document.id
LEFT JOIN LATERAL (
  SELECT count(*) AS page_count FROM budget.source_page page WHERE page.document_id=document.id
) page_counts ON true
LEFT JOIN LATERAL (
  SELECT count(*) AS table_count FROM budget.source_table source_table WHERE source_table.document_id=document.id
) table_counts ON true
LEFT JOIN LATERAL (
  SELECT count(*) AS row_count FROM budget.source_table source_table
  JOIN budget.source_table_row source_row ON source_row.source_table_id=source_table.id
  WHERE source_table.document_id=document.id
) row_counts ON true
LEFT JOIN LATERAL (
  SELECT count(*) AS cell_count FROM budget.source_table source_table
  JOIN budget.source_table_row source_row ON source_row.source_table_id=source_table.id
  JOIN budget.source_table_cell source_cell ON source_cell.source_row_id=source_row.id
  WHERE source_table.document_id=document.id
) cell_counts ON true
LEFT JOIN LATERAL (
  SELECT count(*) AS observation_count,
    count(*) FILTER (WHERE line_item.normalized_category_id IS NOT NULL
      OR category_assignment.id IS NOT NULL) AS mapped_observation_count,
    count(*) FILTER (WHERE observation.review_status <> 'approved'
      OR statement.statement_class_id IS NULL) AS blocked_observation_count
  FROM budget.statement statement
  JOIN budget.line_item line_item ON line_item.statement_id=statement.id
  JOIN budget.financial_observation observation ON observation.line_item_id=line_item.id
  LEFT JOIN budget.financial_statement_line_category_assignment category_assignment
    ON category_assignment.line_item_id=line_item.id AND category_assignment.assignment_status='approved'
  WHERE statement.document_id=document.id
) observation_counts ON true
LEFT JOIN LATERAL (
  SELECT count(DISTINCT publication_observation.observation_id) AS published_observation_count
  FROM budget.statement statement
  JOIN budget.line_item line_item ON line_item.statement_id=statement.id
  JOIN budget.financial_observation observation ON observation.line_item_id=line_item.id
  JOIN budget.publication_observation publication_observation ON publication_observation.observation_id=observation.id
  JOIN budget.publication_snapshot snapshot ON snapshot.id=publication_observation.snapshot_id AND snapshot.status='published'
  WHERE statement.document_id=document.id
) publication_counts ON true
LEFT JOIN LATERAL (
  SELECT count(*) AS unresolved_issue_count FROM budget.review_issue issue
  WHERE issue.status IN ('open','in_review')
    AND (issue.subject_natural_key=document.sha256
      OR issue.subject_natural_key LIKE document.sha256 || ':%')
) issue_counts ON true;

CREATE INDEX idx_budget_financial_statement_category_line
ON budget.financial_statement_line_category_assignment (line_item_id,assignment_status);

COMMIT;
