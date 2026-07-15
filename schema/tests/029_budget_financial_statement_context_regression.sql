\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM information_schema.tables WHERE table_schema='budget' AND table_name IN (
    'document_accounting_context','statement_class','reporting_entity_relationship','financial_observation_relationship'
  )) <> 4 THEN RAISE EXCEPTION 'financial statement context tables are missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='budget' AND table_name='statement' AND column_name='statement_class_id')
  THEN RAISE EXCEPTION 'statement_class_id is missing'; END IF;
  IF (SELECT count(*) FROM budget.statement_class) <> 9 THEN RAISE EXCEPTION 'statement class seed count differs'; END IF;
  IF (SELECT count(*) FROM budget.review_issue_allowed_decision WHERE issue_code IN (
    'source_authority_conflict','filename_reporting_date_conflict','comparative_variance',
    'accounting_scope_mismatch','unsupported_statement_pattern'
  )) <> 12 THEN RAISE EXCEPTION 'financial statement review decisions are incomplete'; END IF;
END $$;

INSERT INTO budget.municipality (slug,legal_name,province_code,effective_from)
VALUES ('gate4-city','Gate 4 City','PE','2024-01-01'),('gate4-other','Gate 4 Other','PE','2024-01-01');

INSERT INTO budget.source_document (municipality_id,title,document_kind,sha256,page_count,status)
VALUES
  ((SELECT id FROM budget.municipality WHERE slug='gate4-city'),'Gate 4 Budget','financial_plan',repeat('a',64),1,'reviewed'),
  ((SELECT id FROM budget.municipality WHERE slug='gate4-city'),'Gate 4 Actual','financial_statements',repeat('b',64),1,'reviewed');

INSERT INTO budget.document_accounting_context (
  document_id,reporting_framework,accounting_basis,reporting_date,assurance_status,audit_opinion,
  auditor_name,auditor_report_date,consolidation_scope,authority_rank,authority_basis,publication_status,
  review_status,reviewed_at
)
SELECT id,'canadian_accounting_standards_for_the_public_sector','full_accrual','2025-03-31',
  'audited','unmodified','Gate 4 Auditor','2025-12-12','consolidated',50,
  'source-page assurance reviewed; publication authority pending','unknown','approved',now()
FROM budget.source_document WHERE title='Gate 4 Actual';

INSERT INTO budget.reporting_entity (municipality_id,slug,display_name,entity_type,effective_from)
VALUES
  ((SELECT id FROM budget.municipality WHERE slug='gate4-city'),'gate4-city','Gate 4 City','municipality','2024-01-01'),
  ((SELECT id FROM budget.municipality WHERE slug='gate4-city'),'gate4-utility','Gate 4 Utility','utility_corporation','2024-01-01'),
  ((SELECT id FROM budget.municipality WHERE slug='gate4-other'),'gate4-other','Gate 4 Other','municipality','2024-01-01');

INSERT INTO budget.normalization_decision (
  source_entity_type,source_entity_key,target_entity_type,target_entity_id,decision,rationale,reviewer
) VALUES
  ('reporting_entity','gate4-utility','reporting_entity',(SELECT id FROM budget.reporting_entity WHERE slug='gate4-utility'),'approved','Gate 4 relationship control','gate4-test'),
  ('financial_observation','gate4-budget-actual','financial_observation',1,'approved','Gate 4 observation relationship control','gate4-test');

INSERT INTO budget.reporting_entity_relationship (
  municipality_id,parent_entity_id,child_entity_id,relationship_type,effective_from,
  normalization_decision_id,review_status,rationale
) VALUES (
  (SELECT id FROM budget.municipality WHERE slug='gate4-city'),
  (SELECT id FROM budget.reporting_entity WHERE slug='gate4-city'),
  (SELECT id FROM budget.reporting_entity WHERE slug='gate4-utility'),
  'consolidated_component','2024-01-01',
  (SELECT id FROM budget.normalization_decision WHERE source_entity_key='gate4-utility'),
  'approved','Reviewed component relationship'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO budget.reporting_entity_relationship (
      municipality_id,parent_entity_id,child_entity_id,relationship_type,effective_from,review_status,rationale
    ) VALUES (
      (SELECT id FROM budget.municipality WHERE slug='gate4-city'),
      (SELECT id FROM budget.reporting_entity WHERE slug='gate4-city'),
      (SELECT id FROM budget.reporting_entity WHERE slug='gate4-utility'),
      'related_pension_plan','2024-01-01','approved','missing decision'
    );
    RAISE EXCEPTION 'approved entity relationship without decision was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO budget.reporting_entity_relationship (
      municipality_id,parent_entity_id,child_entity_id,relationship_type,effective_from,review_status,rationale
    ) VALUES (
      (SELECT id FROM budget.municipality WHERE slug='gate4-city'),
      (SELECT id FROM budget.reporting_entity WHERE slug='gate4-city'),
      (SELECT id FROM budget.reporting_entity WHERE slug='gate4-other'),
      'administrative_parent','2024-01-01','unreviewed','cross municipality'
    );
    RAISE EXCEPTION 'cross-municipality entity relationship was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='cross-municipality entity relationship was accepted' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.fiscal_period (municipality_id,label,start_date,end_date,period_kind)
VALUES ((SELECT id FROM budget.municipality WHERE slug='gate4-city'),'2024/2025','2024-04-01','2025-03-31','fiscal_year');

INSERT INTO budget.source_page (document_id,pdf_page_number,content_type,extraction_method,review_status)
SELECT id,1,'financial_statement','ocr','approved' FROM budget.source_document WHERE title IN ('Gate 4 Budget','Gate 4 Actual');
INSERT INTO budget.source_table (document_id,table_key,table_type,review_status)
SELECT id,'operations','financial_statement','approved' FROM budget.source_document WHERE title IN ('Gate 4 Budget','Gate 4 Actual');
INSERT INTO budget.source_table_column (source_table_id,column_key,column_index,raw_header,column_role,review_status)
SELECT id,'amount',1,CASE WHEN document_id=(SELECT id FROM budget.source_document WHERE title='Gate 4 Budget') THEN 'Budget 2025' ELSE 'Actual 2025' END,'amount','approved'
FROM budget.source_table WHERE table_key='operations';
INSERT INTO budget.source_table_row (source_table_id,row_key,row_index,raw_text,raw_label,indent_level)
SELECT id,'property-taxes',1,'Property taxes 100','Property taxes',0 FROM budget.source_table WHERE table_key='operations';
INSERT INTO budget.source_table_cell (source_row_id,source_table_column_id,raw_text,parsed_numeric,parse_status)
SELECT row.id,column_record.id,'100',100,'parsed'
FROM budget.source_table_row row
JOIN budget.source_table_column column_record ON column_record.source_table_id=row.source_table_id;
INSERT INTO budget.document_period (document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order,review_status)
SELECT source_table.document_id,(SELECT id FROM budget.fiscal_period WHERE label='2024/2025'),column_record.id,
  'current',column_record.raw_header,1,'approved'
FROM budget.source_table_column column_record
JOIN budget.source_table source_table ON source_table.id=column_record.source_table_id;

INSERT INTO budget.statement (document_id,reporting_entity_id,statement_key,statement_kind,title,source_table_id,statement_class_id)
SELECT source_table.document_id,(SELECT id FROM budget.reporting_entity WHERE slug='gate4-city'),
  'operations','financial_statement','Statement of Operations',source_table.id,
  (SELECT id FROM budget.statement_class WHERE code='operations')
FROM budget.source_table source_table WHERE source_table.table_key='operations';
INSERT INTO budget.line_item (statement_id,line_key,row_order,raw_label,line_kind,aggregation_role,source_row_id)
SELECT statement.id,'property-taxes',1,'Property taxes','revenue','detail',source_row.id
FROM budget.statement statement
JOIN budget.source_table_row source_row ON source_row.source_table_id=statement.source_table_id;
INSERT INTO budget.financial_observation (
  line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_state,is_reported,review_status
)
SELECT line_item.id,document_period.id,
  (SELECT id FROM budget.amount_type WHERE code=CASE WHEN source_document.title='Gate 4 Budget' THEN 'budget' ELSE 'actual' END),
  (SELECT id FROM budget.measure_unit WHERE code='cad'),100,'reported',true,'approved'
FROM budget.line_item line_item
JOIN budget.statement statement ON statement.id=line_item.statement_id
JOIN budget.source_document source_document ON source_document.id=statement.document_id
JOIN budget.document_period document_period ON document_period.document_id=source_document.id;
INSERT INTO budget.financial_observation_source (observation_id,source_cell_id,source_role,source_order)
SELECT observation.id,source_cell.id,'reported_value',0
FROM budget.financial_observation observation
JOIN budget.line_item line_item ON line_item.id=observation.line_item_id
JOIN budget.source_table_cell source_cell ON source_cell.source_row_id=line_item.source_row_id;
SET CONSTRAINTS ALL IMMEDIATE;

INSERT INTO budget.financial_observation_relationship (
  municipality_id,source_observation_id,target_observation_id,relationship_type,
  normalization_decision_id,review_status,rationale
)
VALUES (
  (SELECT id FROM budget.municipality WHERE slug='gate4-city'),
  (SELECT observation.id FROM budget.financial_observation observation
    JOIN budget.line_item line_item ON line_item.id=observation.line_item_id
    JOIN budget.statement statement ON statement.id=line_item.statement_id
    JOIN budget.source_document document ON document.id=statement.document_id WHERE document.title='Gate 4 Budget'),
  (SELECT observation.id FROM budget.financial_observation observation
    JOIN budget.line_item line_item ON line_item.id=observation.line_item_id
    JOIN budget.statement statement ON statement.id=line_item.statement_id
    JOIN budget.source_document document ON document.id=statement.document_id WHERE document.title='Gate 4 Actual'),
  'budget_equivalent',
  (SELECT id FROM budget.normalization_decision WHERE source_entity_key='gate4-budget-actual'),
  'approved','Compatible Gate 4 budget-to-actual control'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO budget.financial_observation_relationship (
      municipality_id,source_observation_id,target_observation_id,relationship_type,review_status,rationale
    ) SELECT (SELECT id FROM budget.municipality WHERE slug='gate4-city'),
      target_observation_id,source_observation_id,'budget_equivalent','unreviewed','reversed roles'
    FROM budget.financial_observation_relationship WHERE relationship_type='budget_equivalent';
    RAISE EXCEPTION 'incompatible budget-equivalent roles were accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='incompatible budget-equivalent roles were accepted' THEN RAISE; END IF;
  END;
  BEGIN
    INSERT INTO budget.financial_observation_relationship (
      municipality_id,source_observation_id,target_observation_id,relationship_type,review_status,rationale
    ) SELECT municipality_id,source_observation_id,target_observation_id,'comparative_of','approved','missing decision'
    FROM budget.financial_observation_relationship WHERE relationship_type='budget_equivalent';
    RAISE EXCEPTION 'approved observation relationship without decision was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

INSERT INTO budget.statement (document_id,reporting_entity_id,statement_key,statement_kind,title)
VALUES (
  (SELECT id FROM budget.source_document WHERE title='Gate 4 Budget'),
  (SELECT id FROM budget.reporting_entity WHERE slug='gate4-city'),
  'legacy-null-class','operating','Legacy statement without class'
);

DO $$
BEGIN
  IF (SELECT count(*) FROM budget.financial_observation_relationship WHERE relationship_type='budget_equivalent' AND review_status='approved') <> 1
  THEN RAISE EXCEPTION 'valid budget-equivalent relationship is missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM budget.statement WHERE statement_key='legacy-null-class' AND statement_class_id IS NULL)
  THEN RAISE EXCEPTION 'migration did not preserve nullable class compatibility for existing statements'; END IF;
END $$;

ROLLBACK;
