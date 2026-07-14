BEGIN;

DROP VIEW IF EXISTS budget.v_extraction_coverage CASCADE;
DROP VIEW IF EXISTS budget.v_period_comparison CASCADE;
DROP VIEW IF EXISTS budget.v_revenue_sources CASCADE;
DROP VIEW IF EXISTS budget.v_capital_investment CASCADE;
DROP VIEW IF EXISTS budget.v_operating_flow CASCADE;
DROP VIEW IF EXISTS budget.v_published_facts CASCADE;

DROP TRIGGER IF EXISTS trg_budget_publication_fact_municipality ON budget.publication_fact;
DROP TRIGGER IF EXISTS trg_budget_publication_snapshot_municipality ON budget.publication_snapshot;
DROP TRIGGER IF EXISTS trg_budget_published_snapshot_immutable ON budget.publication_snapshot;
DROP TRIGGER IF EXISTS trg_budget_published_membership_immutable ON budget.publication_fact;
DROP TRIGGER IF EXISTS trg_budget_published_fact_immutable ON budget.fact;
DROP TRIGGER IF EXISTS trg_budget_published_fact_source_immutable ON budget.fact_source;
DROP TRIGGER IF EXISTS trg_budget_reported_fact_source_fact ON budget.fact;
DROP TRIGGER IF EXISTS trg_budget_reported_fact_source_evidence ON budget.fact_source;
DROP FUNCTION IF EXISTS budget.validate_publication_fact_municipality();
DROP FUNCTION IF EXISTS budget.prevent_published_snapshot_mutation();
DROP FUNCTION IF EXISTS budget.validate_reported_fact_source();
DROP FUNCTION IF EXISTS budget.assert_reported_fact_source(bigint);

ALTER TABLE budget.fact_derivation RENAME TO financial_observation_derivation;
ALTER TABLE budget.financial_observation_derivation RENAME COLUMN input_fact_ids TO input_observation_ids;

ALTER TABLE budget.fact RENAME TO financial_observation;
ALTER TABLE budget.financial_observation RENAME COLUMN derivation_id TO financial_observation_derivation_id;

ALTER TABLE budget.fact_source RENAME TO financial_observation_source;
ALTER TABLE budget.financial_observation_source RENAME COLUMN fact_id TO observation_id;

ALTER TABLE budget.capital_project_fact RENAME TO capital_project_observation;
ALTER TABLE budget.capital_project_observation RENAME COLUMN fact_id TO observation_id;

ALTER TABLE budget.rate_fact RENAME TO rate_observation;
ALTER TABLE budget.rate_observation RENAME COLUMN fact_id TO observation_id;

ALTER TABLE budget.debt_fact RENAME TO debt_observation;
ALTER TABLE budget.debt_observation RENAME COLUMN fact_id TO observation_id;

ALTER TABLE budget.reserve_fact RENAME TO reserve_observation;
ALTER TABLE budget.reserve_observation RENAME COLUMN fact_id TO observation_id;

ALTER TABLE budget.publication_fact RENAME TO publication_observation;
ALTER TABLE budget.publication_observation RENAME COLUMN fact_id TO observation_id;

ALTER TABLE budget.fact_followup_observation RENAME TO financial_observation_followup;
ALTER TABLE budget.financial_observation_followup RENAME COLUMN original_fact_id TO original_observation_id;
ALTER TABLE budget.financial_observation_followup RENAME COLUMN subsequent_budget_fact_id TO subsequent_budget_observation_id;
ALTER TABLE budget.financial_observation_followup RENAME COLUMN subsequent_observation_fact_id TO subsequent_observation_id;

ALTER TABLE budget.capital_funding_category_assignment RENAME COLUMN fact_id TO observation_id;
ALTER TABLE budget.reconciliation_result RENAME COLUMN input_fact_ids TO input_observation_ids;

CREATE FUNCTION budget.assert_reported_observation_source(checked_observation_id bigint) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM budget.financial_observation WHERE id = checked_observation_id AND is_reported)
     AND NOT EXISTS (
       SELECT 1 FROM budget.financial_observation_source
       WHERE observation_id = checked_observation_id AND source_role = 'reported_value'
     ) THEN
    RAISE EXCEPTION 'reported financial observation % requires reported_value source evidence', checked_observation_id;
  END IF;
END $$;

CREATE FUNCTION budget.validate_reported_observation_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME = 'financial_observation' THEN
    PERFORM budget.assert_reported_observation_source(NEW.id);
  ELSIF TG_OP = 'DELETE' THEN
    PERFORM budget.assert_reported_observation_source(OLD.observation_id);
  ELSIF TG_OP = 'UPDATE' THEN
    PERFORM budget.assert_reported_observation_source(OLD.observation_id);
    IF NEW.observation_id IS DISTINCT FROM OLD.observation_id THEN
      PERFORM budget.assert_reported_observation_source(NEW.observation_id);
    END IF;
  ELSE
    PERFORM budget.assert_reported_observation_source(NEW.observation_id);
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;

CREATE CONSTRAINT TRIGGER trg_budget_reported_observation_source_observation
AFTER INSERT OR UPDATE ON budget.financial_observation DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_reported_observation_source();
CREATE CONSTRAINT TRIGGER trg_budget_reported_observation_source_evidence
AFTER INSERT OR UPDATE OR DELETE ON budget.financial_observation_source DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_reported_observation_source();

ALTER INDEX IF EXISTS budget.idx_budget_followup_observation RENAME TO idx_budget_financial_observation_followup;
ALTER INDEX IF EXISTS budget.uq_budget_exact_followup_target RENAME TO uq_budget_exact_observation_followup_target;

CREATE TABLE budget.document_section (
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES budget.source_document(id) ON DELETE CASCADE,
  parent_id bigint REFERENCES budget.document_section(id) ON DELETE CASCADE,
  section_key text NOT NULL,
  canonical_role text NOT NULL CHECK (canonical_role IN (
    'front_matter','introduction','strategic_plan','budget_overview','operating_budget',
    'department','facility','capital_budget','capital_program','appendices','appendix','back_matter'
  )),
  title text NOT NULL,
  source_order integer NOT NULL CHECK (source_order >= 0),
  display_order integer NOT NULL CHECK (display_order >= 0),
  start_page integer CHECK (start_page > 0),
  end_page integer CHECK (end_page > 0),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('table_of_contents','source_headings','editorial')),
  review_status text NOT NULL DEFAULT 'unreviewed'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (document_id,section_key),
  CHECK (parent_id IS NULL OR parent_id <> id),
  CHECK (start_page IS NULL OR end_page IS NULL OR end_page >= start_page)
);

CREATE TABLE budget.fact (
  id bigserial PRIMARY KEY,
  municipality_id bigint NOT NULL REFERENCES budget.municipality(id),
  source_document_id bigint NOT NULL REFERENCES budget.source_document(id),
  fact_key text NOT NULL,
  fact_kind text NOT NULL CHECK (fact_kind IN ('narrative','attribute','list')),
  title text NOT NULL,
  body_text text,
  content_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  organization_unit_id bigint REFERENCES budget.organization_unit(id),
  capital_project_id bigint REFERENCES budget.capital_project(id),
  effective_from date,
  effective_to date,
  review_status text NOT NULL DEFAULT 'unreviewed'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (source_document_id,fact_key),
  CHECK (body_text IS NOT NULL OR content_json <> '{}'::jsonb),
  CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from)
);

CREATE TABLE budget.fact_source (
  fact_id bigint NOT NULL REFERENCES budget.fact(id) ON DELETE CASCADE,
  source_page_id bigint NOT NULL REFERENCES budget.source_page(id),
  source_row_id bigint REFERENCES budget.source_table_row(id),
  source_role text NOT NULL CHECK (source_role IN ('primary','supporting')),
  source_order integer NOT NULL DEFAULT 0 CHECK (source_order >= 0),
  PRIMARY KEY (fact_id,source_page_id,source_role,source_order)
);

CREATE TABLE budget.document_section_fact (
  document_section_id bigint NOT NULL REFERENCES budget.document_section(id) ON DELETE CASCADE,
  fact_id bigint NOT NULL REFERENCES budget.fact(id) ON DELETE CASCADE,
  display_order integer NOT NULL CHECK (display_order >= 0),
  PRIMARY KEY (document_section_id,fact_id),
  UNIQUE (document_section_id,display_order)
);

CREATE TABLE budget.document_section_observation (
  observation_id bigint PRIMARY KEY REFERENCES budget.financial_observation(id) ON DELETE CASCADE,
  document_section_id bigint NOT NULL REFERENCES budget.document_section(id) ON DELETE CASCADE,
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('source_page','statement_kind')),
  review_status text NOT NULL DEFAULT 'unreviewed'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected'))
);

CREATE TABLE budget.editorial_guide (
  id bigserial PRIMARY KEY,
  guide_key text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  title text NOT NULL,
  body_markdown text NOT NULL,
  review_status text NOT NULL DEFAULT 'unreviewed'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (guide_key,version)
);

CREATE TABLE budget.document_section_guide (
  document_section_id bigint NOT NULL REFERENCES budget.document_section(id) ON DELETE CASCADE,
  editorial_guide_id bigint NOT NULL REFERENCES budget.editorial_guide(id) ON DELETE CASCADE,
  display_order integer NOT NULL CHECK (display_order >= 0),
  PRIMARY KEY (document_section_id,editorial_guide_id),
  UNIQUE (document_section_id,display_order)
);

CREATE INDEX idx_budget_document_section_tree ON budget.document_section(document_id,parent_id,display_order);
CREATE INDEX idx_budget_section_observation_section ON budget.document_section_observation(document_section_id,observation_id);
CREATE INDEX idx_budget_fact_subject ON budget.fact(municipality_id,organization_unit_id,capital_project_id);
CREATE INDEX idx_budget_fact_source_page ON budget.fact_source(source_page_id,fact_id);

CREATE FUNCTION budget.validate_publication_observation_municipality() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE checked_snapshot_id bigint;
BEGIN
  IF TG_TABLE_NAME = 'publication_snapshot' THEN checked_snapshot_id := NEW.id;
  ELSE checked_snapshot_id := NEW.snapshot_id;
  END IF;
  IF EXISTS (
    SELECT 1 FROM budget.publication_snapshot ps
    CROSS JOIN LATERAL unnest(ps.source_document_ids) source_id
    LEFT JOIN budget.source_document d ON d.id=source_id
    WHERE ps.id=checked_snapshot_id AND (d.id IS NULL OR d.municipality_id<>ps.municipality_id)
  ) THEN RAISE EXCEPTION 'publication snapshot % contains an invalid source document', checked_snapshot_id;
  END IF;
  IF EXISTS (
    SELECT 1 FROM budget.publication_observation po
    JOIN budget.publication_snapshot ps ON ps.id=po.snapshot_id
    JOIN budget.financial_observation o ON o.id=po.observation_id
    JOIN budget.line_item li ON li.id=o.line_item_id
    JOIN budget.statement s ON s.id=li.statement_id
    JOIN budget.source_document d ON d.id=s.document_id
    WHERE po.snapshot_id=checked_snapshot_id
      AND (d.municipality_id<>ps.municipality_id OR NOT d.id=ANY(ps.source_document_ids))
  ) THEN RAISE EXCEPTION 'publication snapshot % contains an observation outside its municipality or source documents', checked_snapshot_id;
  END IF;
  IF EXISTS (
    SELECT 1 FROM budget.publication_observation po
    JOIN budget.financial_observation o ON o.id=po.observation_id
    WHERE po.snapshot_id=checked_snapshot_id AND o.review_status<>'approved'
  ) THEN RAISE EXCEPTION 'publication snapshot % contains an unapproved observation', checked_snapshot_id;
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER trg_budget_publication_observation_municipality
AFTER INSERT OR UPDATE ON budget.publication_observation DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_publication_observation_municipality();
CREATE CONSTRAINT TRIGGER trg_budget_publication_snapshot_municipality
AFTER INSERT OR UPDATE OF municipality_id,source_document_ids ON budget.publication_snapshot DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION budget.validate_publication_observation_municipality();

CREATE FUNCTION budget.prevent_published_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='publication_snapshot' THEN
    IF OLD.status='published' THEN RAISE EXCEPTION 'published snapshots are immutable'; END IF;
  ELSIF TG_TABLE_NAME='publication_observation' THEN
    IF EXISTS (SELECT 1 FROM budget.publication_snapshot WHERE id=COALESCE(NEW.snapshot_id,OLD.snapshot_id) AND status='published')
    THEN RAISE EXCEPTION 'published snapshot membership is immutable'; END IF;
  ELSIF TG_TABLE_NAME='financial_observation' THEN
    IF EXISTS (SELECT 1 FROM budget.publication_observation po JOIN budget.publication_snapshot ps ON ps.id=po.snapshot_id WHERE po.observation_id=OLD.id AND ps.status='published')
    THEN RAISE EXCEPTION 'published observations are immutable'; END IF;
  ELSE
    IF EXISTS (SELECT 1 FROM budget.publication_observation po JOIN budget.publication_snapshot ps ON ps.id=po.snapshot_id WHERE po.observation_id=OLD.observation_id AND ps.status='published')
    THEN RAISE EXCEPTION 'published observation provenance is immutable'; END IF;
  END IF;
  RETURN COALESCE(NEW,OLD);
END $$;

CREATE TRIGGER trg_budget_published_membership_immutable BEFORE INSERT OR UPDATE OR DELETE ON budget.publication_observation
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();
CREATE TRIGGER trg_budget_published_snapshot_immutable BEFORE UPDATE OR DELETE ON budget.publication_snapshot
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();
CREATE TRIGGER trg_budget_published_observation_immutable BEFORE UPDATE OR DELETE ON budget.financial_observation
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();
CREATE TRIGGER trg_budget_published_observation_source_immutable BEFORE UPDATE OR DELETE ON budget.financial_observation_source
FOR EACH ROW EXECUTE FUNCTION budget.prevent_published_snapshot_mutation();

CREATE VIEW budget.v_published_financial_observations AS
SELECT ps.id AS snapshot_id,ps.release_label,
  COALESCE(str.category_taxonomy_version,ps.taxonomy_version) AS taxonomy_version,
  m.id AS municipality_id,m.slug AS municipality_slug,
  re.id AS reporting_entity_id,re.display_name AS reporting_entity_name,
  fp.id AS fiscal_period_id,fp.label AS fiscal_period_label,fp.start_date,fp.end_date,
  s.id AS statement_id,s.statement_key,s.statement_kind,s.title AS statement_title,
  li.id AS line_item_id,li.line_key,li.parent_id AS parent_line_item_id,li.row_order,
  li.raw_label,li.display_label,li.line_kind,li.aggregation_role,li.organization_unit_id,
  CASE WHEN ca.assignment_status='approved' THEN ca.normalized_category_id ELSE li.normalized_category_id END AS normalized_category_id,
  CASE WHEN ca.assignment_status='approved' THEN ca.category_key ELSE legacy_nc.category_key END AS category_key,
  CASE WHEN ca.assignment_status='approved' THEN ca.category_domain ELSE legacy_nc.domain END AS category_domain,
  o.id AS observation_id,at.code AS amount_type,mu.code AS measure_unit,
  o.value_numeric,o.value_text,o.value_state,o.is_reported,
  evidence.source_cell_ids,evidence.source_roles,s.document_id AS source_document_id,
  ou.unit_key AS organization_unit_key,ou.display_name AS organization_unit_name,ou.unit_type AS organization_unit_type,
  ca.category_key AS category_candidate_key,ca.category_domain AS category_candidate_domain,
  ca.assignment_status AS category_assignment_status,ca.mapping_basis AS category_mapping_basis,
  cp.project_key,cp.name AS project_name,
  COALESCE(li.organization_unit_id,poa.organization_unit_id) AS effective_organization_unit_id,
  COALESCE(ou.unit_key,pou.unit_key) AS effective_organization_unit_key,
  COALESCE(ou.display_name,pou.display_name) AS effective_organization_unit_name,
  program.program_key,program.display_name AS program_name,
  mapped_section.id AS document_section_id,mapped_section.section_key,mapped_section.canonical_role AS section_role,
  mapped_section.title AS section_title
FROM budget.publication_snapshot ps
JOIN budget.municipality m ON m.id=ps.municipality_id
JOIN budget.publication_observation po ON po.snapshot_id=ps.id
JOIN budget.financial_observation o ON o.id=po.observation_id AND o.review_status='approved'
JOIN budget.line_item li ON li.id=o.line_item_id
JOIN budget.statement s ON s.id=li.statement_id
JOIN budget.reporting_entity re ON re.id=s.reporting_entity_id
JOIN budget.document_period dp ON dp.id=o.document_period_id
JOIN budget.fiscal_period fp ON fp.id=dp.fiscal_period_id
JOIN budget.amount_type at ON at.id=o.amount_type_id
JOIN budget.measure_unit mu ON mu.id=o.measure_unit_id
LEFT JOIN budget.publication_snapshot_taxonomy_revision str ON str.snapshot_id=ps.id
LEFT JOIN budget.normalized_category legacy_nc ON legacy_nc.id=li.normalized_category_id
LEFT JOIN budget.organization_unit ou ON ou.id=li.organization_unit_id
LEFT JOIN budget.capital_project_observation cpo ON cpo.observation_id=o.id
LEFT JOIN budget.capital_project cp ON cp.id=cpo.capital_project_id
LEFT JOIN LATERAL (
  SELECT a.normalized_category_id,a.assignment_status,a.mapping_basis,nc.category_key,nc.domain AS category_domain
  FROM budget.line_item_category_assignment a JOIN budget.normalized_category nc ON nc.id=a.normalized_category_id
  WHERE a.line_item_id=li.id AND a.taxonomy_version=COALESCE(str.category_taxonomy_version,ps.taxonomy_version)
    AND a.assignment_status IN ('approved','proposed')
  ORDER BY CASE a.assignment_status WHEN 'approved' THEN 0 ELSE 1 END,a.id LIMIT 1
) ca ON true
LEFT JOIN LATERAL (
  SELECT a.organization_unit_id FROM budget.project_organization_assignment a
  WHERE a.capital_project_id=cp.id AND a.assignment_status='approved' ORDER BY a.id LIMIT 1
) poa ON true
LEFT JOIN budget.organization_unit pou ON pou.id=poa.organization_unit_id
LEFT JOIN LATERAL (
  SELECT p.program_key,p.display_name FROM budget.capital_program_line_assignment a
  JOIN budget.capital_program p ON p.id=a.capital_program_id
  WHERE a.line_item_id=li.id AND a.assignment_status='approved' LIMIT 1
) program ON true
LEFT JOIN budget.document_section_observation dso ON dso.observation_id=o.id AND dso.review_status='approved'
LEFT JOIN budget.document_section mapped_section ON mapped_section.id=dso.document_section_id
LEFT JOIN LATERAL (
  SELECT array_agg(os.source_cell_id ORDER BY os.source_order,os.source_cell_id) AS source_cell_ids,
    array_agg(os.source_role ORDER BY os.source_order,os.source_cell_id) AS source_roles
  FROM budget.financial_observation_source os WHERE os.observation_id=o.id
) evidence ON true
WHERE ps.status='published';

CREATE VIEW budget.v_published_facts AS
SELECT DISTINCT ps.id AS snapshot_id,ps.release_label,m.id AS municipality_id,m.slug AS municipality_slug,
  ds.document_id AS edition_document_id,ds.id AS document_section_id,ds.section_key,ds.canonical_role,
  ds.title AS section_title,ds.display_order AS section_display_order,dsf.display_order AS fact_display_order,
  f.id AS fact_id,f.source_document_id,f.fact_key,f.fact_kind,f.title,f.body_text,f.content_json,
  f.organization_unit_id,ou.unit_key AS organization_unit_key,ou.display_name AS organization_unit_name,
  f.capital_project_id,cp.project_key,cp.name AS project_name,
  evidence.source_page_ids,evidence.source_pages
FROM budget.publication_snapshot ps
JOIN budget.municipality m ON m.id=ps.municipality_id
JOIN budget.document_section ds ON ds.document_id=ANY(ps.source_document_ids) AND ds.review_status='approved'
JOIN budget.document_section_fact dsf ON dsf.document_section_id=ds.id
JOIN budget.fact f ON f.id=dsf.fact_id AND f.review_status='approved' AND f.municipality_id=ps.municipality_id
LEFT JOIN budget.organization_unit ou ON ou.id=f.organization_unit_id
LEFT JOIN budget.capital_project cp ON cp.id=f.capital_project_id
LEFT JOIN LATERAL (
  SELECT array_agg(fs.source_page_id ORDER BY fs.source_order,fs.source_page_id) AS source_page_ids,
    array_agg(sp.pdf_page_number ORDER BY fs.source_order,sp.pdf_page_number) AS source_pages
  FROM budget.fact_source fs JOIN budget.source_page sp ON sp.id=fs.source_page_id WHERE fs.fact_id=f.id
) evidence ON true
WHERE ps.status='published';

CREATE VIEW budget.v_operating_flow AS SELECT * FROM budget.v_published_financial_observations
WHERE statement_kind IN ('operating','operating_detail','operating_statement','facility_operating_statement') AND aggregation_role='detail';

CREATE VIEW budget.v_capital_investment AS
SELECT po.*,cpo.capital_project_id,cpo.funding_source_category_id
FROM budget.v_published_financial_observations po
JOIN budget.capital_project_observation cpo ON cpo.observation_id=po.observation_id
WHERE po.amount_type IN ('gross','funding_deduction','net');

CREATE VIEW budget.v_revenue_sources AS SELECT * FROM budget.v_published_financial_observations
WHERE aggregation_role='detail' AND category_domain IN ('revenue','tax','rate','transfer','fee','financing');

CREATE VIEW budget.v_period_comparison AS
SELECT current_observation.snapshot_id,current_observation.taxonomy_version,current_observation.municipality_id,
  current_observation.reporting_entity_id,current_observation.statement_key,current_observation.line_key,current_observation.category_key,
  current_observation.amount_type,current_observation.measure_unit,
  prior_observation.fiscal_period_id AS prior_fiscal_period_id,prior_observation.fiscal_period_label AS prior_fiscal_period_label,
  prior_observation.value_numeric AS prior_value_numeric,current_observation.fiscal_period_id AS current_fiscal_period_id,
  current_observation.fiscal_period_label AS current_fiscal_period_label,current_observation.value_numeric AS current_value_numeric,
  current_observation.value_numeric-prior_observation.value_numeric AS numeric_change
FROM budget.v_published_financial_observations current_observation
JOIN budget.v_published_financial_observations prior_observation
  ON prior_observation.snapshot_id=current_observation.snapshot_id
 AND prior_observation.taxonomy_version=current_observation.taxonomy_version
 AND prior_observation.municipality_id=current_observation.municipality_id
 AND prior_observation.reporting_entity_id=current_observation.reporting_entity_id
 AND prior_observation.statement_key=current_observation.statement_key
 AND prior_observation.line_key=current_observation.line_key
 AND prior_observation.amount_type=current_observation.amount_type
 AND prior_observation.measure_unit=current_observation.measure_unit
 AND prior_observation.end_date<current_observation.start_date
WHERE prior_observation.value_numeric IS NOT NULL AND current_observation.value_numeric IS NOT NULL;

CREATE VIEW budget.v_extraction_coverage AS
SELECT d.id AS document_id,d.title,count(DISTINCT t.id) AS source_table_count,count(DISTINCT r.id) AS source_row_count,
  count(DISTINCT c.id) AS source_cell_count,count(DISTINCT o.id) AS observation_count,
  count(DISTINCT o.id) FILTER (WHERE o.review_status='approved') AS approved_observation_count,
  count(DISTINCT f.id) AS contextual_fact_count,
  count(DISTINCT i.id) FILTER (WHERE i.status IN ('open','in_review')) AS unresolved_issue_count
FROM budget.source_document d
LEFT JOIN budget.source_table t ON t.document_id=d.id
LEFT JOIN budget.source_table_row r ON r.source_table_id=t.id
LEFT JOIN budget.source_table_cell c ON c.source_row_id=r.id
LEFT JOIN budget.financial_observation_source os ON os.source_cell_id=c.id
LEFT JOIN budget.financial_observation o ON o.id=os.observation_id
LEFT JOIN budget.fact f ON f.source_document_id=d.id
LEFT JOIN budget.review_issue i ON i.subject_natural_key=d.sha256
GROUP BY d.id,d.title;

COMMIT;
