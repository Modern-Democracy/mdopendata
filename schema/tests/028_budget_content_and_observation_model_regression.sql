\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM information_schema.tables WHERE table_schema='budget' AND table_name IN (
    'financial_observation','financial_observation_source','financial_observation_derivation',
    'publication_observation','capital_project_observation','rate_observation','debt_observation',
    'reserve_observation','financial_observation_followup','document_section','fact','fact_source',
    'document_section_fact','document_section_observation','editorial_guide','document_section_guide'
  )) <> 16 THEN RAISE EXCEPTION 'budget content or observation tables are missing'; END IF;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='budget' AND table_name IN (
    'publication_fact','capital_project_fact','rate_fact','debt_fact','reserve_fact','fact_followup_observation'
  )) THEN RAISE EXCEPTION 'legacy numeric fact tables remain'; END IF;

  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='budget'
    AND table_name IN ('financial_observation','financial_observation_source','publication_observation',
      'capital_project_observation','rate_observation','debt_observation','reserve_observation',
      'financial_observation_followup','capital_funding_category_assignment','reconciliation_result')
    AND column_name LIKE '%fact%') THEN RAISE EXCEPTION 'legacy numeric fact columns remain'; END IF;

  IF (SELECT count(*) FROM information_schema.views WHERE table_schema='budget' AND table_name IN (
    'v_published_financial_observations','v_published_facts','v_operating_flow','v_capital_investment',
    'v_revenue_sources','v_period_comparison','v_extraction_coverage'
  )) <> 7 THEN RAISE EXCEPTION 'budget publication views are missing'; END IF;

  IF (SELECT count(*) FROM information_schema.columns WHERE table_schema='budget'
    AND table_name='v_published_financial_observations'
    AND column_name IN ('observation_id','source_document_id','project_key','program_key','document_section_id','section_key')) <> 6
  THEN RAISE EXCEPTION 'published observation view contract is incomplete'; END IF;

  IF (SELECT count(*) FROM information_schema.columns WHERE table_schema='budget'
    AND table_name='v_published_facts'
    AND column_name IN ('fact_id','fact_kind','body_text','content_json','document_section_id','source_pages')) <> 6
  THEN RAISE EXCEPTION 'published contextual fact view contract is incomplete'; END IF;
END $$;

ROLLBACK;
