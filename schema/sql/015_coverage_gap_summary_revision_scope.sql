-- 015_coverage_gap_summary_revision_scope.sql
--
-- Fix the population-audit summary view so per-zone audit rows do not get
-- added to per-revision summary totals. The audit intentionally writes both
-- revision-scoped rows (e.g. logical_bylaw_part='raw_tables') and zone-scoped
-- rows (logical_bylaw_part='zone:<CODE>'). v_coverage_gap_summary should report
-- the revision-scoped baseline only; v_coverage_gap_by_zone remains the place
-- to inspect zone-scoped rows.

SET search_path = zoning, public;

CREATE OR REPLACE VIEW zoning.v_coverage_gap_summary AS
WITH parsed AS (
  SELECT
    cg.document_revision_id,
    cg.gap_type,
    cg.is_audit_generated,
    cg.status,
    NULLIF(substring(cg.notes FROM 'population_total=(\d+)'), '')::bigint
      AS population_total,
    NULLIF(substring(cg.notes FROM 'population_gap=(\d+)'), '')::bigint
      AS population_gap
  FROM zoning.coverage_gap cg
  WHERE cg.status <> 'resolved'
    AND (
      NOT cg.is_audit_generated
      OR cg.logical_bylaw_part NOT LIKE 'zone:%'
    )
)
SELECT
  document_revision_id,
  gap_type,
  COUNT(*) AS row_count,
  SUM(CASE WHEN is_audit_generated THEN 1 ELSE 0 END) AS audit_row_count,
  SUM(population_total) AS population_total,
  SUM(population_gap) AS population_gap,
  CASE
    WHEN COALESCE(SUM(population_total), 0) > 0
    THEN ROUND(100.0 * SUM(population_gap) / SUM(population_total), 2)
    ELSE NULL
  END AS gap_pct
FROM parsed
GROUP BY document_revision_id, gap_type
ORDER BY document_revision_id, gap_type;

COMMENT ON VIEW zoning.v_coverage_gap_summary IS
  'Revision-level coverage-gap rollup. Excludes zone-scoped audit rows (logical_bylaw_part LIKE zone:%) so per-zone diagnostics do not double-count into revision baselines; inspect zoning.v_coverage_gap_by_zone for zone-scoped details.';
