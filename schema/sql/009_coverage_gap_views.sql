-- 009_coverage_gap_views.sql
--
-- Population-audit support for the Charlottetown zoning data layer.
--
-- Two changes:
--
-- 1. Relax the `zoning.coverage_gap.gap_type` CHECK constraint so the
--    population-audit script (`scripts/audit-charlottetown-population.py`)
--    can record machine-derived structural gaps alongside the original
--    human-curated chapter/schedule gaps. The previous constraint covered
--    only manual triage categories; the new constraint extends that list
--    with the audit-derived families documented in
--    `wiki/charlottetown/topics/zoning-data-layer-backlog.md` (Task 1).
--
-- 2. Add `zoning.v_coverage_gap_summary` (rolls up open gaps by
--    `(document_revision_id, gap_type)` with counts and a percentage where
--    meaningful) and `zoning.v_coverage_gap_by_zone` (pivots zone-scoped
--    gap rows by `logical_bylaw_part`).
--
-- The audit script is idempotent: it deletes prior rows for the
-- `(bylaw_document_id, document_revision_id, gap_type, logical_bylaw_part)`
-- tuple before inserting fresh ones. Manual gap rows authored by humans use
-- the original `deferred_*`/`pdf_only_*`/`not_yet_digitized_*`/
-- `source_layout_limit` types and are untouched by the audit.

ALTER TABLE zoning.coverage_gap
  DROP CONSTRAINT IF EXISTS ck_zoning_coverage_gap_type;

ALTER TABLE zoning.coverage_gap
  ADD CONSTRAINT ck_zoning_coverage_gap_type
  CHECK (gap_type IN (
    -- Original manual-triage categories (kept verbatim for back-compat).
    'deferred_current_chapter',
    'deferred_current_appendix_table_rows',
    'pdf_only_schedule',
    'not_yet_digitized_map',
    'source_layout_limit',
    -- Audit-derived structural gap families.
    'requirement_without_numeric_value',
    'numeric_value_orphan',
    'relationship_in_text_not_extracted',
    'requirement_applicability_missing',
    'map_reference_not_linked',
    'use_without_term_id',
    'raw_table_no_structured_facts'
  ));

-- A column the audit can stamp so its rows are easy to filter from the
-- manual ones. Defaults to false; the audit sets it to true on insert.
ALTER TABLE zoning.coverage_gap
  ADD COLUMN IF NOT EXISTS is_audit_generated boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_zoning_coverage_gap_audit
  ON zoning.coverage_gap(document_revision_id, gap_type)
  WHERE is_audit_generated;

-- Roll-up: one row per (revision, gap_type) for any non-resolved row,
-- with the audit's `population_total` and `population_gap` parsed back out
-- of the diagnostics blob in `notes` so callers do not have to re-derive
-- them. Manual rows have no diagnostics blob, so their numeric columns are
-- NULL and `gap_pct` is NULL.
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

-- Zone-scoped pivot: any gap whose `logical_bylaw_part` looks like a zone
-- code (`zone:<code>`) is broken out per-zone for easy "which zones are
-- worst?" queries.
CREATE OR REPLACE VIEW zoning.v_coverage_gap_by_zone AS
SELECT
  cg.document_revision_id,
  substring(cg.logical_bylaw_part FROM '^zone:(.+)$') AS zone_code,
  cg.gap_type,
  cg.status,
  cg.is_audit_generated,
  cg.notes
FROM zoning.coverage_gap cg
WHERE cg.logical_bylaw_part LIKE 'zone:%';
