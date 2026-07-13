CREATE TABLE budget.budget_edition (
  document_id bigint PRIMARY KEY REFERENCES budget.source_document(id) ON DELETE CASCADE,
  primary_fiscal_period_id bigint NOT NULL REFERENCES budget.fiscal_period(id),
  subsequent_document_id bigint REFERENCES budget.source_document(id),
  edition_label text NOT NULL,
  review_status text NOT NULL DEFAULT 'approved'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  CHECK (subsequent_document_id IS NULL OR subsequent_document_id <> document_id)
);

CREATE TABLE budget.publication_snapshot_taxonomy_revision (
  snapshot_id bigint PRIMARY KEY REFERENCES budget.publication_snapshot(id) ON DELETE CASCADE,
  category_taxonomy_version text NOT NULL,
  rationale text NOT NULL,
  authorized_by text NOT NULL,
  revised_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE budget.normalized_category
  ADD CONSTRAINT normalized_category_id_taxonomy_version_key UNIQUE (id,taxonomy_version);

CREATE TABLE budget.line_item_category_assignment (
  id bigserial PRIMARY KEY,
  line_item_id bigint NOT NULL REFERENCES budget.line_item(id) ON DELETE CASCADE,
  normalized_category_id bigint NOT NULL,
  taxonomy_version text NOT NULL,
  assignment_status text NOT NULL
    CHECK (assignment_status IN ('proposed','approved','rejected','superseded')),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('structural','controlled_label','manual')),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (line_item_id,taxonomy_version,normalized_category_id),
  CHECK (assignment_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  FOREIGN KEY (normalized_category_id,taxonomy_version)
    REFERENCES budget.normalized_category(id,taxonomy_version)
);
CREATE UNIQUE INDEX uq_budget_line_category_active
  ON budget.line_item_category_assignment(line_item_id,taxonomy_version)
  WHERE assignment_status IN ('proposed','approved');

CREATE TABLE budget.capital_funding_category_assignment (
  id bigserial PRIMARY KEY,
  fact_id bigint NOT NULL REFERENCES budget.capital_project_fact(fact_id) ON DELETE CASCADE,
  normalized_category_id bigint NOT NULL,
  taxonomy_version text NOT NULL,
  assignment_status text NOT NULL
    CHECK (assignment_status IN ('proposed','approved','rejected','superseded')),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('structural','controlled_label','manual')),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (fact_id,taxonomy_version,normalized_category_id),
  CHECK (assignment_status <> 'approved' OR normalization_decision_id IS NOT NULL),
  FOREIGN KEY (normalized_category_id,taxonomy_version)
    REFERENCES budget.normalized_category(id,taxonomy_version)
);
CREATE UNIQUE INDEX uq_budget_capital_funding_category_active
  ON budget.capital_funding_category_assignment(fact_id,taxonomy_version)
  WHERE assignment_status IN ('proposed','approved');

CREATE TABLE budget.project_organization_assignment (
  id bigserial PRIMARY KEY,
  capital_project_id bigint NOT NULL REFERENCES budget.capital_project(id) ON DELETE CASCADE,
  organization_unit_id bigint NOT NULL REFERENCES budget.organization_unit(id),
  source_profile_id bigint REFERENCES budget.capital_project_profile(id),
  assignment_status text NOT NULL
    CHECK (assignment_status IN ('proposed','approved','rejected','superseded')),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('profile_department','source_heading','manual')),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (capital_project_id,organization_unit_id),
  CHECK (assignment_status <> 'approved' OR normalization_decision_id IS NOT NULL)
);
CREATE UNIQUE INDEX uq_budget_project_organization_active
  ON budget.project_organization_assignment(capital_project_id)
  WHERE assignment_status IN ('proposed','approved');

CREATE TABLE budget.capital_program (
  id bigserial PRIMARY KEY,
  municipality_id bigint NOT NULL REFERENCES budget.municipality(id),
  program_key text NOT NULL,
  display_name text NOT NULL,
  reporting_entity_id bigint REFERENCES budget.reporting_entity(id),
  organization_unit_id bigint REFERENCES budget.organization_unit(id),
  review_status text NOT NULL DEFAULT 'approved'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  UNIQUE (municipality_id,program_key)
);

CREATE TABLE budget.capital_program_line_assignment (
  line_item_id bigint PRIMARY KEY REFERENCES budget.line_item(id) ON DELETE CASCADE,
  capital_program_id bigint NOT NULL REFERENCES budget.capital_program(id),
  assignment_status text NOT NULL
    CHECK (assignment_status IN ('proposed','approved','rejected','superseded')),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('source_heading','manual')),
  normalization_decision_id bigint REFERENCES budget.normalization_decision(id),
  rationale text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (assignment_status <> 'approved' OR normalization_decision_id IS NOT NULL)
);

CREATE TABLE budget.fact_followup_observation (
  original_fact_id bigint NOT NULL REFERENCES budget.fact(id) ON DELETE CASCADE,
  subsequent_budget_fact_id bigint NOT NULL REFERENCES budget.fact(id),
  subsequent_observation_fact_id bigint NOT NULL REFERENCES budget.fact(id),
  observation_kind text NOT NULL CHECK (observation_kind IN ('forecast','actual','restated_budget')),
  mapping_basis text NOT NULL CHECK (mapping_basis IN ('exact_identity','reviewed_identity','manual')),
  review_status text NOT NULL DEFAULT 'approved'
    CHECK (review_status IN ('unreviewed','needs_review','approved','rejected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (original_fact_id,observation_kind),
  CHECK (original_fact_id <> subsequent_budget_fact_id),
  CHECK (subsequent_budget_fact_id <> subsequent_observation_fact_id)
);

CREATE INDEX idx_budget_edition_period ON budget.budget_edition(primary_fiscal_period_id);
CREATE INDEX idx_budget_line_category_taxonomy ON budget.line_item_category_assignment(taxonomy_version,assignment_status);
CREATE INDEX idx_budget_project_org_unit ON budget.project_organization_assignment(organization_unit_id,assignment_status);
CREATE INDEX idx_budget_capital_program_line_program ON budget.capital_program_line_assignment(capital_program_id,assignment_status);
CREATE INDEX idx_budget_followup_observation ON budget.fact_followup_observation(subsequent_observation_fact_id,observation_kind);
CREATE UNIQUE INDEX uq_budget_exact_followup_target
  ON budget.fact_followup_observation(subsequent_observation_fact_id,observation_kind)
  WHERE mapping_basis='exact_identity' AND review_status='approved';

CREATE OR REPLACE VIEW budget.v_published_facts AS
SELECT ps.id AS snapshot_id, ps.release_label,
  COALESCE(str.category_taxonomy_version,ps.taxonomy_version) AS taxonomy_version,
  m.id AS municipality_id, m.slug AS municipality_slug,
  re.id AS reporting_entity_id, re.display_name AS reporting_entity_name,
  fp.id AS fiscal_period_id, fp.label AS fiscal_period_label, fp.start_date, fp.end_date,
  s.id AS statement_id, s.statement_key, s.statement_kind, s.title AS statement_title,
  li.id AS line_item_id, li.line_key, li.parent_id AS parent_line_item_id, li.row_order,
  li.raw_label, li.display_label, li.line_kind, li.aggregation_role,
  li.organization_unit_id,
  CASE WHEN ca.assignment_status='approved' THEN ca.normalized_category_id ELSE li.normalized_category_id END AS normalized_category_id,
  CASE WHEN ca.assignment_status='approved' THEN ca.category_key ELSE legacy_nc.category_key END AS category_key,
  CASE WHEN ca.assignment_status='approved' THEN ca.category_domain ELSE legacy_nc.domain END AS category_domain,
  f.id AS fact_id, at.code AS amount_type, mu.code AS measure_unit,
  f.value_numeric, f.value_text, f.value_state, f.is_reported,
  evidence.source_cell_ids, evidence.source_roles,
  s.document_id AS source_document_id,
  ou.unit_key AS organization_unit_key, ou.display_name AS organization_unit_name, ou.unit_type AS organization_unit_type,
  ca.category_key AS category_candidate_key, ca.category_domain AS category_candidate_domain,
  ca.assignment_status AS category_assignment_status, ca.mapping_basis AS category_mapping_basis,
  cp.project_key, cp.name AS project_name,
  COALESCE(li.organization_unit_id,poa.organization_unit_id) AS effective_organization_unit_id,
  COALESCE(ou.unit_key,pou.unit_key) AS effective_organization_unit_key,
  COALESCE(ou.display_name,pou.display_name) AS effective_organization_unit_name,
  program.program_key, program.display_name AS program_name
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
LEFT JOIN budget.publication_snapshot_taxonomy_revision str ON str.snapshot_id=ps.id
LEFT JOIN budget.normalized_category legacy_nc ON legacy_nc.id = li.normalized_category_id
LEFT JOIN budget.organization_unit ou ON ou.id=li.organization_unit_id
LEFT JOIN budget.capital_project_fact cpf ON cpf.fact_id=f.id
LEFT JOIN budget.capital_project cp ON cp.id=cpf.capital_project_id
LEFT JOIN LATERAL (
  SELECT a.normalized_category_id,a.assignment_status,a.mapping_basis,nc.category_key,nc.domain AS category_domain
  FROM budget.line_item_category_assignment a
  JOIN budget.normalized_category nc ON nc.id=a.normalized_category_id
  WHERE a.line_item_id=li.id
    AND a.taxonomy_version=COALESCE(str.category_taxonomy_version,ps.taxonomy_version)
    AND a.assignment_status IN ('approved','proposed')
  ORDER BY CASE a.assignment_status WHEN 'approved' THEN 0 ELSE 1 END,a.id
  LIMIT 1
) ca ON true
LEFT JOIN LATERAL (
  SELECT a.organization_unit_id
  FROM budget.project_organization_assignment a
  WHERE a.capital_project_id=cp.id AND a.assignment_status='approved'
  ORDER BY a.id LIMIT 1
) poa ON true
LEFT JOIN budget.organization_unit pou ON pou.id=poa.organization_unit_id
LEFT JOIN LATERAL (
  SELECT p.program_key,p.display_name
  FROM budget.capital_program_line_assignment a
  JOIN budget.capital_program p ON p.id=a.capital_program_id
  WHERE a.line_item_id=li.id AND a.assignment_status='approved'
  LIMIT 1
) program ON true
LEFT JOIN LATERAL (
  SELECT array_agg(fs.source_cell_id ORDER BY fs.source_order, fs.source_cell_id) AS source_cell_ids,
    array_agg(fs.source_role ORDER BY fs.source_order, fs.source_cell_id) AS source_roles
  FROM budget.fact_source fs WHERE fs.fact_id = f.id
) evidence ON true
WHERE ps.status = 'published';
