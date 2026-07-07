\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM pg_views WHERE schemaname = 'budget' AND viewname IN (
    'v_published_facts','v_operating_flow','v_capital_investment',
    'v_revenue_sources','v_period_comparison','v_extraction_coverage'
  )) <> 6 THEN RAISE EXCEPTION 'required budget views are missing'; END IF;
END $$;

-- Test data use negative IDs so this rollback-only control cannot collide with sequences.
INSERT INTO budget.municipality (id,slug,legal_name,province_code,effective_from) VALUES
  (-1,'test-one','Test One','PE','2026-01-01'), (-2,'test-two','Test Two','PE','2026-01-01');
INSERT INTO budget.source_document (id,municipality_id,title,document_kind,sha256) VALUES
  (-1,-1,'Test document one','budget',repeat('a',64)), (-2,-2,'Test document two','budget',repeat('b',64));
INSERT INTO budget.source_page (id,document_id,pdf_page_number) VALUES (-1,-1,1),(-2,-2,1);
INSERT INTO budget.source_table (id,document_id,table_key) VALUES (-1,-1,'table');

DO $$ BEGIN
  BEGIN
    INSERT INTO budget.source_table_page VALUES (-1,-2,1,'body',NULL,NULL);
    SET CONSTRAINTS budget.trg_budget_table_page_same_document IMMEDIATE;
    RAISE EXCEPTION 'cross-document table/page link was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'cross-document table/page link was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'source table and page must belong to the same document' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.reporting_entity (id,municipality_id,slug,display_name,entity_type,effective_from) VALUES
  (-1,-1,'entity-one','Entity One','municipal','2026-01-01'),
  (-2,-2,'entity-two','Entity Two','municipal','2026-01-01');
INSERT INTO budget.fiscal_period (id,municipality_id,label,start_date,end_date,period_kind) VALUES
  (-1,-1,'2026','2026-01-01','2026-12-31','annual');
INSERT INTO budget.source_table_column (id,source_table_id,column_key,column_index) VALUES (-1,-1,'amount',0);
INSERT INTO budget.document_period (id,document_id,fiscal_period_id,source_table_column_id,period_role,raw_column_label,column_order)
  VALUES (-1,-1,-1,-1,'current','2026',0);
INSERT INTO budget.source_table_row (id,source_table_id,row_key,row_index,raw_text) VALUES (-1,-1,'row',0,'Amount');
INSERT INTO budget.source_table_cell (id,source_row_id,source_table_column_id,raw_text) VALUES (-1,-1,-1,'1');
INSERT INTO budget.statement (id,document_id,reporting_entity_id,statement_key,statement_kind,title) VALUES
  (-1,-1,-1,'statement-one','operating','Statement One'),
  (-2,-2,-2,'statement-two','operating','Statement Two');
INSERT INTO budget.line_item (id,statement_id,line_key,row_order,raw_label,line_kind,aggregation_role) VALUES
  (-1,-1,'line-one',1,'Line One','amount','detail'),
  (-2,-2,'line-two',1,'Line Two','amount','detail');
INSERT INTO budget.fact (id,line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_state,is_reported,review_status)
  VALUES (-1,-1,-1,(SELECT id FROM budget.amount_type WHERE code='budget'),(SELECT id FROM budget.measure_unit WHERE code='cad'),1,'reported',true,'approved');
INSERT INTO budget.fact_derivation (id,formula_code,formula_text,software_version) VALUES (-1,'test','test','test');
INSERT INTO budget.fact (id,line_item_id,document_period_id,amount_type_id,measure_unit_id,value_numeric,value_state,is_reported,derivation_id,review_status)
  VALUES (-2,-2,-1,(SELECT id FROM budget.amount_type WHERE code='forecast'),(SELECT id FROM budget.measure_unit WHERE code='cad'),1,'reported',false,-1,'approved');
INSERT INTO budget.fact_source (fact_id,source_cell_id,source_role) VALUES (-1,-1,'reported_value'),(-1,-1,'label_context');

DO $$ BEGIN
  BEGIN
    UPDATE budget.fact_source SET fact_id = -2 WHERE fact_id = -1 AND source_role = 'reported_value';
    SET CONSTRAINTS budget.trg_budget_reported_fact_source_evidence IMMEDIATE;
    RAISE EXCEPTION 'reported evidence move was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'reported evidence move was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'reported fact -1 requires reported_value source evidence' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.review_issue (id,review_key,subject_record_type,subject_natural_key,issue_code,severity,status,title,description,publication_effect,required_resolution,prohibited_action)
VALUES (-1,'test-review','fact','test','reported_calculation_variance','high','open','Test','Test','warn','decision','rewrite');
INSERT INTO budget.review_decision (id,review_issue_id,decision_code,rationale,reviewer) VALUES
  (-1,-1,'accept_reported_with_warning','Test','test');
DO $$ BEGIN
  BEGIN
    DELETE FROM budget.review_decision WHERE id = -1;
    RAISE EXCEPTION 'review decision deletion was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'review decision deletion was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'review decisions are append-only; insert a superseding decision' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.publication_snapshot (id,municipality_id,release_label,taxonomy_version,source_document_ids,status)
VALUES (-1,-1,'test','test',ARRAY[-1]::bigint[],'draft');
DO $$ BEGIN
  BEGIN
    INSERT INTO budget.publication_fact VALUES (-1,-1);
    UPDATE budget.publication_snapshot SET municipality_id = -2 WHERE id = -1;
    SET CONSTRAINTS budget.trg_budget_publication_snapshot_municipality IMMEDIATE;
    RAISE EXCEPTION 'cross-municipality publication was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'cross-municipality publication was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'publication snapshot -1 contains an invalid source document' THEN RAISE; END IF;
  END;
END $$;

INSERT INTO budget.publication_fact VALUES (-1,-1);
DO $$ BEGIN
  BEGIN
    UPDATE budget.publication_snapshot SET source_document_ids = '{}'::bigint[] WHERE id = -1;
    SET CONSTRAINTS budget.trg_budget_publication_snapshot_municipality IMMEDIATE;
    RAISE EXCEPTION 'unlisted fact source document was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'unlisted fact source document was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'publication snapshot -1 contains a fact outside its municipality or source documents' THEN RAISE; END IF;
  END;
END $$;

UPDATE budget.fact SET review_status = 'unreviewed' WHERE id = -1;
DO $$ BEGIN
  BEGIN
    SET CONSTRAINTS budget.trg_budget_publication_fact_municipality IMMEDIATE;
    UPDATE budget.publication_fact SET fact_id = -1 WHERE snapshot_id = -1;
    SET CONSTRAINTS budget.trg_budget_publication_fact_municipality IMMEDIATE;
    RAISE EXCEPTION 'unapproved publication fact was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'unapproved publication fact was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'publication snapshot -1 contains an unapproved fact' THEN RAISE; END IF;
  END;
END $$;
UPDATE budget.fact SET review_status = 'approved' WHERE id = -1;
UPDATE budget.publication_snapshot SET status = 'published' WHERE id = -1;

DO $$ BEGIN
  IF (SELECT count(*) FROM budget.v_published_facts WHERE snapshot_id=-1 AND fact_id=-1) <> 1 THEN
    RAISE EXCEPTION 'published fact cardinality is not one row per fact';
  END IF;
END $$;

DO $$ BEGIN
  BEGIN
    UPDATE budget.fact SET value_numeric = 2 WHERE id = -1;
    RAISE EXCEPTION 'published fact mutation was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'published fact mutation was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'published facts are immutable' THEN RAISE; END IF;
  END;
END $$;

DO $$ BEGIN
  BEGIN
    UPDATE budget.source_table_row SET raw_text = 'Changed' WHERE id = -1;
    RAISE EXCEPTION 'raw source mutation was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'raw source mutation was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'raw source content is immutable' THEN RAISE; END IF;
  END;
END $$;

DO $$ BEGIN
  BEGIN
    UPDATE budget.reporting_entity SET parent_entity_id = -2 WHERE id = -1;
    UPDATE budget.reporting_entity SET parent_entity_id = -1 WHERE id = -2;
    SET CONSTRAINTS budget.trg_budget_reporting_entity_no_cycle IMMEDIATE;
    RAISE EXCEPTION 'hierarchy cycle was accepted';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM = 'hierarchy cycle was accepted' THEN RAISE;
    ELSIF SQLERRM <> 'hierarchy cycle detected in budget.reporting_entity' THEN RAISE; END IF;
  END;
END $$;

DO $$ BEGIN
  IF (SELECT count(*) FROM pg_indexes WHERE schemaname='budget' AND indexname IN (
    'idx_budget_source_document_municipality','idx_budget_fiscal_period_municipality_dates',
    'idx_budget_statement_entity_kind','idx_budget_capital_project_municipality',
    'idx_budget_capital_project_fact_project','idx_budget_publication_snapshot_municipality'
  )) <> 6 THEN RAISE EXCEPTION 'required budget query indexes are missing'; END IF;
END $$;

ROLLBACK;
