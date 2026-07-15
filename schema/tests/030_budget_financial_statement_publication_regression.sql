\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='budget' AND table_name='financial_statement_line_category_assignment')
  THEN RAISE EXCEPTION 'financial statement category assignment table is missing'; END IF;
  IF (SELECT count(*) FROM information_schema.views WHERE table_schema='budget' AND table_name IN (
    'v_published_financial_statement_observations','v_budget_actual_comparison','v_financial_position',
    'v_cash_flow','v_pension_position','v_holistic_finance_coverage'
  )) <> 6 THEN RAISE EXCEPTION 'financial statement publication views are missing'; END IF;
END $$;

INSERT INTO budget.municipality (slug,legal_name,province_code,effective_from)
VALUES ('gate4-publication','Gate 4 Publication City','PE','2024-01-01');
INSERT INTO budget.source_document (municipality_id,title,document_kind,sha256,page_count,status)
VALUES
  ((SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'Legacy Budget Document','financial_plan',repeat('c',64),1,'reviewed'),
  ((SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'Financial Statement Document','financial_statements',repeat('d',64),1,'reviewed'),
  ((SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'Financial Statement Without Context','financial_statements',repeat('e',64),1,'reviewed');

INSERT INTO budget.publication_snapshot (municipality_id,release_label,taxonomy_version,source_document_ids,status)
VALUES (
  (SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'Legacy published snapshot','legacy-v1',
  ARRAY[(SELECT id FROM budget.source_document WHERE title='Legacy Budget Document')],'published'
);

INSERT INTO budget.document_accounting_context (
  document_id,reporting_framework,accounting_basis,reporting_date,assurance_status,audit_opinion,
  auditor_name,auditor_report_date,consolidation_scope,authority_rank,authority_basis,
  publication_status,review_status,reviewed_at
) VALUES (
  (SELECT id FROM budget.source_document WHERE title='Financial Statement Document'),
  'canadian_accounting_standards_for_the_public_sector','full_accrual','2025-03-31','audited','unmodified',
  'Gate 4 Auditor','2025-12-12','consolidated',50,'reviewed source copy','unknown','approved',now()
);
INSERT INTO budget.reporting_entity (municipality_id,slug,display_name,entity_type,effective_from)
VALUES ((SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'gate4-publication-city','Gate 4 Publication City','municipality','2024-01-01');
INSERT INTO budget.fiscal_period (municipality_id,label,start_date,end_date,period_kind)
VALUES ((SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'2024/2025','2024-04-01','2025-03-31','fiscal_year');
INSERT INTO budget.source_page (document_id,pdf_page_number,content_type,extraction_method,review_status)
VALUES ((SELECT id FROM budget.source_document WHERE title='Financial Statement Document'),1,'financial_statement','ocr','approved');
INSERT INTO budget.source_table (document_id,table_key,table_type,review_status)
VALUES ((SELECT id FROM budget.source_document WHERE title='Financial Statement Document'),'operations','financial_statement','approved');
INSERT INTO budget.source_table_column (source_table_id,column_key,column_index,raw_header,column_role,review_status)
VALUES
  ((SELECT id FROM budget.source_table WHERE table_key='operations'),'budget',1,'Budget 2025','amount','approved'),
  ((SELECT id FROM budget.source_table WHERE table_key='operations'),'actual',2,'Actual 2025','amount','approved');
INSERT INTO budget.source_table_row (source_table_id,row_key,row_index,raw_text,raw_label,indent_level)
VALUES ((SELECT id FROM budget.source_table WHERE table_key='operations'),'property-taxes',1,'Property taxes 100 110','Property taxes',0);
INSERT INTO budget.source_table_cell (source_row_id,source_table_column_id,raw_text,parsed_numeric,parse_status)
SELECT (SELECT id FROM budget.source_table_row WHERE row_key='property-taxes'),column_record.id,
  CASE column_record.column_key WHEN 'budget' THEN '100' ELSE '110' END,
  CASE column_record.column_key WHEN 'budget' THEN 100 ELSE 110 END,'parsed'
FROM budget.source_table_column column_record
WHERE column_record.source_table_id=(SELECT id FROM budget.source_table WHERE table_key='operations');
INSERT INTO budget.document_period (document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order,review_status)
SELECT (SELECT id FROM budget.source_document WHERE title='Financial Statement Document'),
  (SELECT id FROM budget.fiscal_period WHERE label='2024/2025'),column_record.id,'current',column_record.raw_header,column_record.column_index,'approved'
FROM budget.source_table_column column_record
WHERE column_record.source_table_id=(SELECT id FROM budget.source_table WHERE table_key='operations');
INSERT INTO budget.statement (document_id,reporting_entity_id,statement_key,statement_kind,title,source_table_id,statement_class_id)
VALUES (
  (SELECT id FROM budget.source_document WHERE title='Financial Statement Document'),
  (SELECT id FROM budget.reporting_entity WHERE slug='gate4-publication-city'),
  'operations','financial_statement','Statement of Operations',
  (SELECT id FROM budget.source_table WHERE table_key='operations'),
  (SELECT id FROM budget.statement_class WHERE code='operations')
);
INSERT INTO budget.line_item (statement_id,line_key,row_order,raw_label,line_kind,aggregation_role,source_row_id)
VALUES (
  (SELECT id FROM budget.statement WHERE statement_key='operations'),'property-taxes',1,'Property taxes','revenue','detail',
  (SELECT id FROM budget.source_table_row WHERE row_key='property-taxes')
);
INSERT INTO budget.financial_observation (
  line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_state,is_reported,review_status
)
SELECT (SELECT id FROM budget.line_item WHERE line_key='property-taxes'),document_period.id,
  (SELECT id FROM budget.amount_type WHERE code=source_column.column_key),
  (SELECT id FROM budget.measure_unit WHERE code='cad'),
  CASE source_column.column_key WHEN 'budget' THEN 100 ELSE 110 END,
  'reported',true,'approved'
FROM budget.document_period document_period
JOIN budget.source_table_column source_column ON source_column.id=document_period.source_table_column_id
WHERE document_period.document_id=(SELECT id FROM budget.source_document WHERE title='Financial Statement Document');
INSERT INTO budget.financial_observation_source (observation_id,source_cell_id,source_role,source_order)
SELECT observation.id,source_cell.id,'reported_value',0
FROM budget.financial_observation observation
JOIN budget.document_period document_period ON document_period.id=observation.document_period_id
JOIN budget.source_table_cell source_cell ON source_cell.source_table_column_id=document_period.source_table_column_id;

INSERT INTO budget.normalization_decision (
  source_entity_type,source_entity_key,target_entity_type,target_entity_id,decision,rationale,reviewer,taxonomy_version
) VALUES
  ('financial_observation','gate4-budget-actual','financial_observation',1,'approved','Reviewed Gate 4 equivalence','gate4-test',NULL),
  ('line_item','gate4-property-taxes','normalized_category',1,'approved','Reviewed Gate 4 category','gate4-test','gate4-fs-v1');
INSERT INTO budget.financial_observation_relationship (
  municipality_id,source_observation_id,target_observation_id,relationship_type,normalization_decision_id,review_status,rationale
)
SELECT (SELECT id FROM budget.municipality WHERE slug='gate4-publication'),
  max(observation.id) FILTER (WHERE amount_type.code='budget'),
  max(observation.id) FILTER (WHERE amount_type.code='actual'),
  'budget_equivalent',
  (SELECT id FROM budget.normalization_decision WHERE source_entity_key='gate4-budget-actual'),
  'approved','Reviewed Gate 4 equivalence'
FROM budget.financial_observation observation
JOIN budget.amount_type amount_type ON amount_type.id=observation.amount_type_id;

INSERT INTO budget.normalized_category (taxonomy_version,category_key,domain,display_name)
VALUES
  ('gate4-fs-v1','property-tax','revenue','Property tax'),
  ('gate4-fs-v2','property-tax','revenue','Property tax');

INSERT INTO budget.statement (document_id,reporting_entity_id,statement_key,statement_kind,title,statement_class_id)
VALUES (
  (SELECT id FROM budget.source_document WHERE title='Financial Statement Document'),
  (SELECT id FROM budget.reporting_entity WHERE slug='gate4-publication-city'),
  'gate4-position','financial_statement','Position control',
  (SELECT id FROM budget.statement_class WHERE code='financial_position')
);
INSERT INTO budget.line_item (statement_id,line_key,raw_label,display_label,row_order,line_kind,aggregation_role)
VALUES ((SELECT id FROM budget.statement WHERE statement_key='gate4-position'),'cash','Cash','Cash',1,'detail','detail');

DO $$
BEGIN
  BEGIN
    INSERT INTO budget.financial_statement_line_category_assignment (
      line_item_id,statement_class_id,normalized_category_id,taxonomy_version,assignment_status,mapping_basis,rationale
    ) VALUES (
      (SELECT id FROM budget.line_item WHERE line_key='cash'),
      (SELECT id FROM budget.statement_class WHERE code='financial_position'),
      (SELECT id FROM budget.normalized_category WHERE taxonomy_version='gate4-fs-v1' AND category_key='property-tax'),
      'gate4-fs-v1','proposed','manual_review','invalid position-category control'
    );
    RAISE EXCEPTION 'non-operations financial statement category assignment was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='non-operations financial statement category assignment was accepted' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.financial_statement_line_category_assignment (
  line_item_id,statement_class_id,normalized_category_id,taxonomy_version,assignment_status,mapping_basis,
  normalization_decision_id,rationale
) VALUES (
  (SELECT id FROM budget.line_item WHERE line_key='property-taxes'),
  (SELECT id FROM budget.statement_class WHERE code='operations'),
  (SELECT id FROM budget.normalized_category WHERE taxonomy_version='gate4-fs-v1' AND category_key='property-tax'),
  'gate4-fs-v1','approved','manual_review',
  (SELECT id FROM budget.normalization_decision WHERE source_entity_key='gate4-property-taxes'),
  'Reviewed Gate 4 category'
);

INSERT INTO budget.publication_snapshot (municipality_id,release_label,taxonomy_version,source_document_ids,status)
VALUES (
  (SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'Financial statement draft','gate4-fs-v1',
  ARRAY[(SELECT id FROM budget.source_document WHERE title='Financial Statement Document')],'draft'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO budget.publication_snapshot (municipality_id,release_label,taxonomy_version,source_document_ids,status)
    VALUES (
      (SELECT id FROM budget.municipality WHERE slug='gate4-publication'),'Missing context control','gate4-fs-v1',
      ARRAY[(SELECT id FROM budget.source_document WHERE title='Financial Statement Without Context')],'published'
    );
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION 'financial statement snapshot without accounting context was published';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='financial statement snapshot without accounting context was published' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.publication_observation (snapshot_id,observation_id)
SELECT (SELECT id FROM budget.publication_snapshot WHERE release_label='Financial statement draft'),id
FROM budget.financial_observation;
SET CONSTRAINTS ALL IMMEDIATE;

DO $$
BEGIN
  BEGIN
    UPDATE budget.publication_snapshot SET status='published' WHERE release_label='Financial statement draft';
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION 'financial statement snapshot with unknown publication authority was published';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='financial statement snapshot with unknown publication authority was published' THEN RAISE; END IF;
  END;
END $$;

UPDATE budget.document_accounting_context
SET publication_status='final_release',authority_rank=80,authority_basis='reviewed final release'
WHERE document_id=(SELECT id FROM budget.source_document WHERE title='Financial Statement Document');
UPDATE budget.publication_snapshot SET status='published' WHERE release_label='Financial statement draft';
SET CONSTRAINTS ALL IMMEDIATE;

DO $$
BEGIN
  BEGIN
    UPDATE budget.document_accounting_context SET publication_status='unknown'
    WHERE document_id=(SELECT id FROM budget.source_document WHERE title='Financial Statement Document');
    RAISE EXCEPTION 'published financial statement authority was weakened';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='published financial statement authority was weakened' THEN RAISE; END IF;
  END;
  BEGIN
    INSERT INTO budget.financial_statement_line_category_assignment (
      line_item_id,statement_class_id,normalized_category_id,taxonomy_version,assignment_status,mapping_basis,rationale
    ) VALUES (
      (SELECT id FROM budget.line_item WHERE line_key='property-taxes'),
      (SELECT id FROM budget.statement_class WHERE code='operations'),
      (SELECT id FROM budget.normalized_category WHERE taxonomy_version='gate4-fs-v2' AND category_key='property-tax'),
      'gate4-fs-v2','approved','manual_review','missing decision'
    );
    RAISE EXCEPTION 'approved category assignment without decision was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

DO $$
BEGIN
  IF (SELECT count(*) FROM budget.publication_snapshot WHERE release_label='Legacy published snapshot' AND status='published') <> 1
  THEN RAISE EXCEPTION 'legacy published snapshot changed'; END IF;
  IF (SELECT count(*) FROM budget.v_published_financial_statement_observations WHERE release_label='Financial statement draft') <> 2
  THEN RAISE EXCEPTION 'published financial statement observation view count differs'; END IF;
  IF (SELECT count(*) FROM budget.v_budget_actual_comparison WHERE release_label='Financial statement draft') <> 1
  THEN RAISE EXCEPTION 'budget-actual comparison must contain exactly one reviewed relationship'; END IF;
  IF (SELECT variance FROM budget.v_budget_actual_comparison WHERE release_label='Financial statement draft') <> 10
  THEN RAISE EXCEPTION 'budget-actual variance differs'; END IF;
  IF (SELECT count(*) FROM budget.v_holistic_finance_coverage WHERE title='Financial Statement Document') <> 1
  THEN RAISE EXCEPTION 'holistic finance coverage row is missing'; END IF;
  IF (SELECT count(*) FROM information_schema.columns WHERE table_schema='budget' AND table_name IN (
    'v_financial_position','v_cash_flow','v_pension_position'
  ) AND column_name IN ('cross_entity_addition_allowed','scope_warning')) <> 6
  THEN RAISE EXCEPTION 'non-additive scope controls are missing'; END IF;
END $$;

ROLLBACK;
