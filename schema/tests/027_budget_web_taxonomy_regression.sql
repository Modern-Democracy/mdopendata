\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM information_schema.tables WHERE table_schema='budget' AND table_name IN (
    'budget_edition','publication_snapshot_taxonomy_revision','line_item_category_assignment',
    'capital_funding_category_assignment','project_organization_assignment','capital_program',
    'capital_program_line_assignment','fact_followup_observation'
  )) <> 8 THEN RAISE EXCEPTION 'budget web taxonomy tables are missing'; END IF;

  IF (SELECT count(*) FROM information_schema.columns WHERE table_schema='budget' AND table_name='v_published_facts'
      AND column_name IN ('source_document_id','category_candidate_key','category_assignment_status',
        'effective_organization_unit_key','project_key','program_key')) <> 6
  THEN RAISE EXCEPTION 'published fact review columns are missing'; END IF;

  IF (SELECT count(*) FROM pg_indexes WHERE schemaname='budget' AND indexname IN (
    'uq_budget_line_category_active','uq_budget_capital_funding_category_active',
    'uq_budget_project_organization_active','idx_budget_followup_observation','uq_budget_exact_followup_target'
  )) <> 5 THEN RAISE EXCEPTION 'budget assignment indexes are missing'; END IF;

  IF (SELECT count(*) FROM pg_constraint
      WHERE contype='f' AND conrelid IN (
        'budget.line_item_category_assignment'::regclass,
        'budget.capital_funding_category_assignment'::regclass
      ) AND array_length(conkey,1)=2) <> 2
  THEN RAISE EXCEPTION 'category taxonomy composite foreign keys are missing'; END IF;
END $$;

ROLLBACK;
