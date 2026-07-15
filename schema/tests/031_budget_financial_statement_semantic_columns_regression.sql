\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM information_schema.tables WHERE table_schema='budget' AND table_name IN (
    'semantic_table_column','source_cell_semantic_assignment'
  )) <> 2 THEN RAISE EXCEPTION 'semantic column tables are missing'; END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='budget' AND table_name='document_period' AND column_name='semantic_column_id'
  ) THEN RAISE EXCEPTION 'document period semantic column link is missing'; END IF;
END $$;

INSERT INTO budget.municipality (slug,legal_name,province_code,effective_from)
VALUES ('gate6-semantic','Gate 6 Semantic City','PE','2024-01-01');
INSERT INTO budget.source_document (municipality_id,title,document_kind,sha256,page_count,status)
VALUES
  ((SELECT id FROM budget.municipality WHERE slug='gate6-semantic'),'Gate 6 Source A','financial_statement',repeat('f',64),1,'extracted'),
  ((SELECT id FROM budget.municipality WHERE slug='gate6-semantic'),'Gate 6 Source B','financial_statement',repeat('0',64),1,'extracted');
INSERT INTO budget.source_table (document_id,table_key,table_type,review_status)
VALUES
  ((SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),'gate6-a','operations','unreviewed'),
  ((SELECT id FROM budget.source_document WHERE title='Gate 6 Source B'),'gate6-b','operations','unreviewed');
INSERT INTO budget.source_table_column (source_table_id,column_key,column_index,column_role,review_status)
VALUES
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'ocr-group-0',0,'unknown','needs_review'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'ocr-group-1',1,'unknown','needs_review'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-b'),'ocr-group-0',0,'unknown','needs_review');
INSERT INTO budget.source_table_row (source_table_id,row_key,row_index,raw_text,raw_label)
VALUES
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'merged-values',1,'Revenue $ 100 $ 110 $ 90','Revenue'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-b'),'other-row',1,'Other 1','Other');
INSERT INTO budget.source_table_cell (source_row_id,source_table_column_id,raw_text,parse_status)
VALUES
  ((SELECT id FROM budget.source_table_row WHERE row_key='merged-values'),
   (SELECT id FROM budget.source_table_column WHERE column_key='ocr-group-0' AND source_table_id=(SELECT id FROM budget.source_table WHERE table_key='gate6-a')),
   'Revenue','unparsed'),
  ((SELECT id FROM budget.source_table_row WHERE row_key='merged-values'),
   (SELECT id FROM budget.source_table_column WHERE column_key='ocr-group-1' AND source_table_id=(SELECT id FROM budget.source_table WHERE table_key='gate6-a')),
   '$ 100 $ 110 $ 90','unparsed'),
  ((SELECT id FROM budget.source_table_row WHERE row_key='other-row'),
   (SELECT id FROM budget.source_table_column WHERE column_key='ocr-group-0' AND source_table_id=(SELECT id FROM budget.source_table WHERE table_key='gate6-b')),
   '1','unparsed');

INSERT INTO budget.semantic_table_column (
  source_table_id,semantic_column_key,column_order,raw_header,column_role,review_status,rationale
) VALUES
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'label',0,NULL,'line_label','needs_review','Gate 6 label control'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'budget-current',1,'Budget 2025','period_value','needs_review','Gate 6 budget control'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'actual-current',2,'Actual 2025','period_value','needs_review','Gate 6 actual control'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'actual-prior',3,'Actual 2024','period_value','needs_review','Gate 6 comparative control'),
  ((SELECT id FROM budget.source_table WHERE table_key='gate6-b'),'other-period',1,'Actual 2025','period_value','needs_review','Gate 6 cross-table control');

INSERT INTO budget.normalization_decision (
  source_entity_type,source_entity_key,target_entity_type,target_entity_id,decision,rationale,reviewer
)
SELECT 'source_table',source_table.table_key,'semantic_table_column',semantic_column.id,
  'approved','Gate 6 reviewed semantic column','gate6-test'
FROM budget.semantic_table_column semantic_column
JOIN budget.source_table source_table ON source_table.id=semantic_column.source_table_id;
UPDATE budget.semantic_table_column semantic_column
SET normalization_decision_id=decision.id,review_status='approved'
FROM budget.normalization_decision decision
WHERE decision.target_entity_type='semantic_table_column'
  AND decision.target_entity_id=semantic_column.id;

INSERT INTO budget.source_cell_semantic_assignment (
  source_cell_id,semantic_column_id,fragment_key,fragment_order,raw_fragment_text,
  assignment_basis,review_status,rationale
)
SELECT source_cell.id,semantic_column.id,assignment.fragment_key,assignment.fragment_order,
  assignment.raw_fragment_text,'manual_review','needs_review','Gate 6 merged-cell fragment control'
FROM (VALUES
  ('budget-current',0,'budget-fragment','$ 100'),
  ('actual-current',1,'actual-fragment','$ 110'),
  ('actual-prior',2,'prior-fragment','$ 90')
) assignment(semantic_column_key,fragment_order,fragment_key,raw_fragment_text)
JOIN budget.semantic_table_column semantic_column
  ON semantic_column.semantic_column_key=assignment.semantic_column_key
JOIN budget.source_table_cell source_cell ON source_cell.raw_text='$ 100 $ 110 $ 90';

INSERT INTO budget.normalization_decision (
  source_entity_type,source_entity_key,target_entity_type,target_entity_id,decision,rationale,reviewer
)
SELECT 'source_table_cell',source_cell_id::text,'source_cell_semantic_assignment',id,
  'approved','Gate 6 reviewed cell fragment','gate6-test'
FROM budget.source_cell_semantic_assignment;
UPDATE budget.source_cell_semantic_assignment assignment
SET normalization_decision_id=decision.id,review_status='approved'
FROM budget.normalization_decision decision
WHERE decision.target_entity_type='source_cell_semantic_assignment'
  AND decision.target_entity_id=assignment.id;

INSERT INTO budget.fiscal_period (municipality_id,label,start_date,end_date,period_kind)
VALUES
  ((SELECT id FROM budget.municipality WHERE slug='gate6-semantic'),'2024/2025','2024-04-01','2025-03-31','fiscal_year'),
  ((SELECT id FROM budget.municipality WHERE slug='gate6-semantic'),'2023/2024','2023-04-01','2024-03-31','fiscal_year');

INSERT INTO budget.document_period (
  document_id,fiscal_period_id,semantic_column_id,period_role,raw_column_label,column_order,review_status
) VALUES
  ((SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
   (SELECT id FROM budget.fiscal_period WHERE label='2024/2025' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
   (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='budget-current'),'current_budget','Budget 2025',1,'approved'),
  ((SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
   (SELECT id FROM budget.fiscal_period WHERE label='2024/2025' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
   (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='actual-current'),'current_actual','Actual 2025',2,'approved'),
  ((SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
   (SELECT id FROM budget.fiscal_period WHERE label='2023/2024' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
   (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='actual-prior'),'comparative_actual','Actual 2024',3,'approved');

INSERT INTO budget.document_period (
  document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order,review_status
) VALUES (
  (SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
  (SELECT id FROM budget.fiscal_period WHERE label='2024/2025' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
  (SELECT id FROM budget.source_table_column WHERE column_key='ocr-group-1' AND source_table_id=(SELECT id FROM budget.source_table WHERE table_key='gate6-a')),
  'legacy_raw_column','OCR group 1',4,'unreviewed'
);
SET CONSTRAINTS ALL IMMEDIATE;

DO $$
BEGIN
  IF (SELECT count(*) FROM budget.source_cell_semantic_assignment assignment
      JOIN budget.source_table_cell cell ON cell.id=assignment.source_cell_id
      WHERE cell.raw_text='$ 100 $ 110 $ 90' AND assignment.review_status='approved') <> 3 THEN
    RAISE EXCEPTION 'one merged raw cell did not retain three reviewed semantic fragments';
  END IF;
  IF (SELECT count(*) FROM budget.document_period WHERE semantic_column_id IS NOT NULL) <> 3 THEN
    RAISE EXCEPTION 'semantic document periods are missing';
  END IF;
  IF (SELECT count(*) FROM budget.document_period WHERE source_table_column_id IS NOT NULL) <> 1 THEN
    RAISE EXCEPTION 'legacy raw-column document period compatibility failed';
  END IF;
END $$;

DO $$
BEGIN
  BEGIN
    INSERT INTO budget.semantic_table_column (
      source_table_id,semantic_column_key,column_order,column_role,review_status,rationale
    ) VALUES ((SELECT id FROM budget.source_table WHERE table_key='gate6-a'),'invalid-approved',9,'context','approved','Missing decision');
    RAISE EXCEPTION 'approved semantic column without decision was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  BEGIN
    INSERT INTO budget.source_cell_semantic_assignment (
      source_cell_id,semantic_column_id,fragment_key,fragment_order,raw_fragment_text,assignment_basis,review_status,rationale
    ) VALUES (
      (SELECT id FROM budget.source_table_cell WHERE raw_text='Revenue'),
      (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='label'),
      'approved-without-decision',0,'Revenue','manual_review','approved','Missing decision rejection control'
    );
    RAISE EXCEPTION 'approved semantic assignment without decision was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  BEGIN
    INSERT INTO budget.source_cell_semantic_assignment (
      source_cell_id,semantic_column_id,fragment_key,fragment_order,raw_fragment_text,assignment_basis,review_status,rationale
    ) VALUES (
      (SELECT id FROM budget.source_table_cell WHERE raw_text='$ 100 $ 110 $ 90'),
      (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='other-period'),
      'cross-table',9,'$ 100','manual_review','needs_review','Cross-table rejection control'
    );
    RAISE EXCEPTION 'cross-table semantic assignment was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='cross-table semantic assignment was accepted' THEN RAISE; END IF;
  END;

  BEGIN
    INSERT INTO budget.source_cell_semantic_assignment (
      source_cell_id,semantic_column_id,fragment_key,fragment_order,raw_fragment_text,assignment_basis,review_status,rationale
    ) VALUES (
      (SELECT id FROM budget.source_table_cell WHERE raw_text='$ 100 $ 110 $ 90'),
      (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='budget-current'),
      'invented-fragment',9,'999','manual_review','needs_review','Substring rejection control'
    );
    RAISE EXCEPTION 'non-source semantic fragment was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='non-source semantic fragment was accepted' THEN RAISE; END IF;
  END;

  BEGIN
    INSERT INTO budget.document_period (
      document_id,fiscal_period_id,source_table_column_id,semantic_column_id,period_role,raw_column_label,column_order
    ) VALUES (
      (SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
      (SELECT id FROM budget.fiscal_period WHERE label='2024/2025' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
      (SELECT id FROM budget.source_table_column WHERE column_key='ocr-group-0' AND source_table_id=(SELECT id FROM budget.source_table WHERE table_key='gate6-a')),
      (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='budget-current'),
      'invalid-both','Invalid',9
    );
    RAISE EXCEPTION 'document period with raw and semantic columns was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  BEGIN
    INSERT INTO budget.document_period (
      document_id,fiscal_period_id,semantic_column_id,period_role,raw_column_label,column_order
    ) VALUES (
      (SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
      (SELECT id FROM budget.fiscal_period WHERE label='2024/2025' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
      (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='label'),
      'invalid-label','Invalid',9
    );
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION 'document period accepted a non-period semantic column';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='document period accepted a non-period semantic column' THEN RAISE; END IF;
  END;

  BEGIN
    INSERT INTO budget.document_period (
      document_id,fiscal_period_id,semantic_column_id,period_role,raw_column_label,column_order
    ) VALUES (
      (SELECT id FROM budget.source_document WHERE title='Gate 6 Source A'),
      (SELECT id FROM budget.fiscal_period WHERE label='2024/2025' AND municipality_id=(SELECT id FROM budget.municipality WHERE slug='gate6-semantic')),
      (SELECT id FROM budget.semantic_table_column WHERE semantic_column_key='other-period'),
      'invalid-document','Invalid',9
    );
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION 'document period accepted a semantic column from another document';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='document period accepted a semantic column from another document' THEN RAISE; END IF;
  END;
END $$;

ROLLBACK;
