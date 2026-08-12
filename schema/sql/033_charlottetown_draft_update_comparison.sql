-- Comparison views for the April draft spatial layers and the July 2026 update.
-- Prerequisite: the four manually managed public source tables must exist.
-- The source tables are not created or modified here.
--
-- parcel_candidate_id is unique within each source layer but is not stable
-- across the two extractions. Parcel comparison therefore uses dissolved
-- coverage with a 1 m grid, not an ID join.

BEGIN;

CREATE INDEX IF NOT EXISTS chtwn_parcel_map_update_geom_gix
  ON public."CHTWN_Parcel_Map_Update" USING gist (geom);

CREATE INDEX IF NOT EXISTS chtwn_draft_zoning_boundaries_update_geom_gix
  ON public."CHTWN_Draft_Zoning_Boundaries_Update" USING gist (geom);

DROP VIEW IF EXISTS zoning.v_charlottetown_draft_update_qa CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_intersections_significant CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_intersections CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_parcel_coverage_changes_significant CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_parcel_coverage_changes CASCADE;

CREATE VIEW zoning.v_charlottetown_parcel_coverage_changes AS
WITH old_coverage AS (
  SELECT ST_Union(geom, 1.0) AS geom
  FROM public."CHTWN_Parcel_Map"
),
new_coverage AS (
  SELECT ST_Union(geom, 1.0) AS geom
  FROM public."CHTWN_Parcel_Map_Update"
),
parts AS (
  SELECT
    ROW_NUMBER() OVER ()::bigint AS change_id,
    (ST_Dump(ST_CollectionExtract(ST_SymDifference(o.geom, n.geom), 3))).geom AS geom,
    o.geom AS old_coverage_geom,
    n.geom AS new_coverage_geom
  FROM old_coverage o
  CROSS JOIN new_coverage n
)
SELECT
  change_id,
  CASE
    WHEN ST_Area(ST_Intersection(geom, old_coverage_geom)) > 0 THEN 'old_only'
    ELSE 'new_only'
  END AS change_side,
  ST_Area(geom) AS change_area_m2,
  ST_Area(geom) >= 100.0 AS is_screening_candidate_100m2,
  ST_Area(geom) >= 1000.0 AS is_screening_candidate_1000m2,
  1.0::numeric AS comparison_grid_size_m,
  geom::geometry(MultiPolygon, 2954) AS geom
FROM parts
WHERE NOT ST_IsEmpty(geom);

COMMENT ON VIEW zoning.v_charlottetown_parcel_coverage_changes IS
  'Dissolved parcel-coverage differences after 1 m grid comparison. The 100 m2 and 1000 m2 flags are screening thresholds, not legal significance classifications.';

CREATE VIEW zoning.v_charlottetown_parcel_coverage_changes_significant AS
SELECT *
FROM zoning.v_charlottetown_parcel_coverage_changes
WHERE is_screening_candidate_1000m2;

COMMENT ON VIEW zoning.v_charlottetown_parcel_coverage_changes_significant IS
  'Screening view of dissolved parcel-coverage differences at or above 1000 m2. An empty result means no coverage change meets this screening threshold.';

CREATE VIEW zoning.v_charlottetown_draft_zoning_intersections AS
WITH old_zoning AS (
  SELECT
    fid AS old_fid,
    zone_code AS old_zone_code,
    zone_name AS old_zone_name,
    CASE WHEN upper(trim(zone_code)) = 'H' THEN 'HI' ELSE upper(trim(zone_code)) END AS old_zone_code_canonical,
    geom AS old_geom
  FROM public."CHTWN_Draft_Zoning_Boundaries"
),
new_zoning AS (
  SELECT
    fid AS new_fid,
    zone_code AS new_zone_code,
    zone_name AS new_zone_name,
    CASE WHEN upper(trim(zone_code)) = 'H' THEN 'HI' ELSE upper(trim(zone_code)) END AS new_zone_code_canonical,
    geom AS new_geom
  FROM public."CHTWN_Draft_Zoning_Boundaries_Update"
),
pairs AS (
  SELECT
    o.old_fid,
    n.new_fid,
    o.old_zone_code,
    n.new_zone_code,
    o.old_zone_name,
    n.new_zone_name,
    o.old_zone_code_canonical,
    n.new_zone_code_canonical,
    ST_Area(o.old_geom) AS old_zone_area_m2,
    ST_Area(n.new_geom) AS new_zone_area_m2,
    ST_Intersection(o.old_geom, n.new_geom) AS intersection_geom
  FROM old_zoning o
  JOIN new_zoning n
    ON o.old_geom && n.new_geom
   AND ST_Intersects(o.old_geom, n.new_geom)
  WHERE o.old_zone_code IS DISTINCT FROM n.new_zone_code
)
SELECT
  format('%s:%s', old_fid, new_fid) AS comparison_id,
  old_fid,
  new_fid,
  old_zone_code,
  new_zone_code,
  old_zone_name,
  new_zone_name,
  old_zone_code_canonical,
  new_zone_code_canonical,
  CASE
    WHEN old_zone_code_canonical IS NOT DISTINCT FROM new_zone_code_canonical
      THEN 'code_normalization_only'
    ELSE 'zone_code_changed'
  END AS change_class,
  ST_Area(intersection_geom) AS intersection_area_m2,
  old_zone_area_m2,
  new_zone_area_m2,
  ST_Area(intersection_geom) / NULLIF(old_zone_area_m2, 0) AS intersection_fraction_old,
  ST_Area(intersection_geom) / NULLIF(new_zone_area_m2, 0) AS intersection_fraction_new,
  ST_Area(intersection_geom) < 1.0 AS is_sub_square_metre_sliver,
  ST_Area(intersection_geom) >= 1000.0 AS is_screening_candidate_1000m2,
  ST_Multi(ST_CollectionExtract(intersection_geom, 3))::geometry(MultiPolygon, 2954) AS geom
FROM pairs
WHERE ST_Area(intersection_geom) > 0;

COMMENT ON VIEW zoning.v_charlottetown_draft_zoning_intersections IS
  'Positive-area intersections where original and updated draft zoning codes differ. H-to-HI normalization is retained separately from substantive canonical changes.';

CREATE VIEW zoning.v_charlottetown_draft_zoning_intersections_significant AS
SELECT *
FROM zoning.v_charlottetown_draft_zoning_intersections
WHERE change_class = 'zone_code_changed'
  AND is_screening_candidate_1000m2;

COMMENT ON VIEW zoning.v_charlottetown_draft_zoning_intersections_significant IS
  'Screening view of substantive canonical zoning-code intersections at or above 1000 m2.';

CREATE VIEW zoning.v_charlottetown_draft_update_qa AS
WITH source_stats AS (
  SELECT 'CHTWN_Parcel_Map'::text AS source_layer, COUNT(*)::numeric AS feature_count,
         COUNT(*) FILTER (WHERE geom IS NULL)::numeric AS null_geometry_count,
         COUNT(*) FILTER (WHERE NOT ST_IsValid(geom))::numeric AS invalid_geometry_count
    FROM public."CHTWN_Parcel_Map"
  UNION ALL
  SELECT 'CHTWN_Parcel_Map_Update', COUNT(*)::numeric,
         COUNT(*) FILTER (WHERE geom IS NULL)::numeric,
         COUNT(*) FILTER (WHERE NOT ST_IsValid(geom))::numeric
    FROM public."CHTWN_Parcel_Map_Update"
  UNION ALL
  SELECT 'CHTWN_Draft_Zoning_Boundaries', COUNT(*)::numeric,
         COUNT(*) FILTER (WHERE geom IS NULL)::numeric,
         COUNT(*) FILTER (WHERE NOT ST_IsValid(geom))::numeric
    FROM public."CHTWN_Draft_Zoning_Boundaries"
  UNION ALL
  SELECT 'CHTWN_Draft_Zoning_Boundaries_Update', COUNT(*)::numeric,
         COUNT(*) FILTER (WHERE geom IS NULL)::numeric,
         COUNT(*) FILTER (WHERE NOT ST_IsValid(geom))::numeric
    FROM public."CHTWN_Draft_Zoning_Boundaries_Update"
),
parcel_metrics AS (
  SELECT
    COUNT(*)::numeric AS coverage_change_parts,
    COALESCE(SUM(change_area_m2), 0)::numeric AS total_coverage_change_area_m2,
    COALESCE(MAX(change_area_m2), 0)::numeric AS maximum_coverage_change_part_m2,
    COUNT(*) FILTER (WHERE is_screening_candidate_100m2)::numeric AS coverage_parts_ge_100m2,
    COUNT(*) FILTER (WHERE is_screening_candidate_1000m2)::numeric AS coverage_parts_ge_1000m2,
    COALESCE(SUM(change_area_m2) FILTER (WHERE is_screening_candidate_100m2), 0)::numeric AS coverage_area_ge_100m2
  FROM zoning.v_charlottetown_parcel_coverage_changes
),
zoning_metrics AS (
  SELECT
    COUNT(*)::numeric AS changed_intersection_rows,
    COALESCE(SUM(intersection_area_m2), 0)::numeric AS changed_intersection_area_m2,
    COUNT(*) FILTER (WHERE change_class = 'code_normalization_only')::numeric AS normalization_only_rows,
    COALESCE(SUM(intersection_area_m2) FILTER (WHERE change_class = 'code_normalization_only'), 0)::numeric AS normalization_only_area_m2,
    COUNT(*) FILTER (WHERE change_class = 'zone_code_changed')::numeric AS canonical_zone_change_rows,
    COALESCE(SUM(intersection_area_m2) FILTER (WHERE change_class = 'zone_code_changed'), 0)::numeric AS canonical_zone_change_area_m2,
    COUNT(*) FILTER (WHERE change_class = 'zone_code_changed' AND is_screening_candidate_1000m2)::numeric AS significant_zone_change_rows,
    COALESCE(SUM(intersection_area_m2) FILTER (WHERE change_class = 'zone_code_changed' AND is_screening_candidate_1000m2), 0)::numeric AS significant_zone_change_area_m2,
    COUNT(*) FILTER (WHERE is_sub_square_metre_sliver)::numeric AS sub_square_metre_sliver_rows
  FROM zoning.v_charlottetown_draft_zoning_intersections
)
SELECT 'source_layer'::text AS metric_group, source_layer AS metric_name,
       feature_count AS metric_value_numeric,
       format('null_geometries=%s; invalid_geometries=%s', null_geometry_count, invalid_geometry_count) AS metric_value_text
FROM source_stats
UNION ALL SELECT 'parcel_comparison', 'coverage_change_parts', coverage_change_parts, NULL FROM parcel_metrics
UNION ALL SELECT 'parcel_comparison', 'total_coverage_change_area_m2', total_coverage_change_area_m2, NULL FROM parcel_metrics
UNION ALL SELECT 'parcel_comparison', 'maximum_coverage_change_part_m2', maximum_coverage_change_part_m2, NULL FROM parcel_metrics
UNION ALL SELECT 'parcel_comparison', 'coverage_parts_ge_100m2', coverage_parts_ge_100m2, NULL FROM parcel_metrics
UNION ALL SELECT 'parcel_comparison', 'coverage_parts_ge_1000m2', coverage_parts_ge_1000m2, NULL FROM parcel_metrics
UNION ALL SELECT 'parcel_comparison', 'coverage_area_ge_100m2', coverage_area_ge_100m2, NULL FROM parcel_metrics
UNION ALL SELECT 'zoning_comparison', 'changed_intersection_rows', changed_intersection_rows, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'changed_intersection_area_m2', changed_intersection_area_m2, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'normalization_only_rows', normalization_only_rows, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'normalization_only_area_m2', normalization_only_area_m2, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'canonical_zone_change_rows', canonical_zone_change_rows, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'canonical_zone_change_area_m2', canonical_zone_change_area_m2, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'significant_zone_change_rows', significant_zone_change_rows, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'significant_zone_change_area_m2', significant_zone_change_area_m2, NULL FROM zoning_metrics
UNION ALL SELECT 'zoning_comparison', 'sub_square_metre_sliver_rows', sub_square_metre_sliver_rows, NULL FROM zoning_metrics
UNION ALL
SELECT 'zoning_inventory', 'original_zone_codes', COUNT(DISTINCT zone_code)::numeric,
       string_agg(DISTINCT zone_code, ', ' ORDER BY zone_code)
FROM public."CHTWN_Draft_Zoning_Boundaries"
UNION ALL
SELECT 'zoning_inventory', 'updated_zone_codes', COUNT(DISTINCT zone_code)::numeric,
       string_agg(DISTINCT zone_code, ', ' ORDER BY zone_code)
FROM public."CHTWN_Draft_Zoning_Boundaries_Update"
UNION ALL
SELECT 'comparison_contract', 'parcel_identifier_status', NULL,
       'parcel_candidate_id is not stable across layers; parcel comparison uses dissolved coverage at 1 m grid size';

COMMENT ON VIEW zoning.v_charlottetown_draft_update_qa IS
  'QA metrics for the original and updated Charlottetown draft parcel and zoning layers.';

COMMIT;
