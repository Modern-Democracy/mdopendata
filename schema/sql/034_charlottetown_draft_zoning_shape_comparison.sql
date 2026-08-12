-- Updated-map-shape-based zoning comparison.
-- Original Conservancy (C) shapes are excluded from the comparison.

BEGIN;

DROP VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_shape_comparison_qa CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_changed_shapes_significant CASCADE;
DROP VIEW IF EXISTS zoning.v_charlottetown_draft_zoning_changed_shapes CASCADE;

CREATE VIEW zoning.v_charlottetown_draft_zoning_changed_shapes AS
WITH old_zoning AS (
  SELECT
    fid AS old_fid,
    zone_code AS old_zone_code,
    zone_name AS old_zone_name,
    CASE WHEN upper(trim(zone_code)) = 'H' THEN 'HI' ELSE upper(trim(zone_code)) END AS old_zone_code_canonical,
    geom AS old_geom
  FROM public."CHTWN_Draft_Zoning_Boundaries"
  WHERE upper(trim(zone_code)) <> 'C'
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
    n.new_fid,
    n.new_zone_code,
    n.new_zone_name,
    n.new_zone_code_canonical,
    o.old_zone_code,
    o.old_zone_name,
    o.old_zone_code_canonical,
    o.old_fid,
    n.new_geom,
    ST_Intersection(n.new_geom, o.old_geom) AS intersection_geom
  FROM new_zoning n
  JOIN old_zoning o
    ON n.new_geom && o.old_geom
   AND ST_Intersects(n.new_geom, o.old_geom)
),
grouped AS (
  SELECT
    new_fid,
    new_zone_code,
    new_zone_name,
    new_zone_code_canonical,
    old_zone_code,
    old_zone_name,
    old_zone_code_canonical,
    COUNT(DISTINCT old_fid)::integer AS original_shape_count,
    ARRAY_AGG(DISTINCT old_fid ORDER BY old_fid) AS original_fids,
    MAX(ST_Area(new_geom)) AS new_zone_area_m2,
    ST_UnaryUnion(ST_Collect(intersection_geom)) AS grouped_geom
  FROM pairs
  WHERE ST_Area(intersection_geom) > 0
  GROUP BY new_fid, new_zone_code, new_zone_name, new_zone_code_canonical,
           old_zone_code, old_zone_name, old_zone_code_canonical
)
SELECT
  format('%s:%s', new_fid, old_zone_code) AS comparison_id,
  new_fid,
  new_zone_code,
  new_zone_name,
  new_zone_code_canonical,
  old_zone_code,
  old_zone_name,
  old_zone_code_canonical,
  original_shape_count,
  original_fids,
  new_zone_area_m2,
  ST_Area(grouped_geom) AS comparison_area_m2,
  ST_Area(grouped_geom) AS intersection_area_m2,
  ST_Area(grouped_geom) / NULLIF(new_zone_area_m2, 0) AS comparison_fraction_updated,
  CASE
    WHEN old_zone_code_canonical IS NOT DISTINCT FROM new_zone_code_canonical
      THEN 'code_normalization_only'
    ELSE 'zone_code_changed'
  END AS change_class,
  ST_Area(grouped_geom) < 1.0 AS is_sub_square_metre_sliver,
  ST_Area(grouped_geom) >= 1000.0 AS is_screening_candidate_1000m2,
  ST_Multi(ST_CollectionExtract(grouped_geom, 3))::geometry(MultiPolygon, 2954) AS geom
FROM grouped
WHERE old_zone_code IS DISTINCT FROM new_zone_code;

COMMENT ON VIEW zoning.v_charlottetown_draft_zoning_changed_shapes IS
  'Updated-map-shape-based zoning changes. Original Conservancy (C) shapes are excluded. One row is emitted per updated feature and original zone code, dissolving multiple original shapes with the same code.';

CREATE VIEW zoning.v_charlottetown_draft_zoning_changed_shapes_significant AS
SELECT *
FROM zoning.v_charlottetown_draft_zoning_changed_shapes
WHERE is_screening_candidate_1000m2;

COMMENT ON VIEW zoning.v_charlottetown_draft_zoning_changed_shapes_significant IS
  'Updated-map-shape-based zoning changes at or above 1000 m2.';

CREATE VIEW zoning.v_charlottetown_draft_zoning_shape_comparison_qa AS
WITH source_stats AS (
  SELECT 'CHTWN_Draft_Zoning_Boundaries'::text AS source_layer, COUNT(*)::numeric AS feature_count,
         COUNT(*) FILTER (WHERE geom IS NULL)::numeric AS null_geometry_count,
         COUNT(*) FILTER (WHERE NOT ST_IsValid(geom))::numeric AS invalid_geometry_count
    FROM public."CHTWN_Draft_Zoning_Boundaries"
  UNION ALL
  SELECT 'CHTWN_Draft_Zoning_Boundaries_Update', COUNT(*)::numeric,
         COUNT(*) FILTER (WHERE geom IS NULL)::numeric,
         COUNT(*) FILTER (WHERE NOT ST_IsValid(geom))::numeric
    FROM public."CHTWN_Draft_Zoning_Boundaries_Update"
),
comparison_metrics AS (
  SELECT
    COUNT(*)::numeric AS changed_shape_rows,
    COUNT(DISTINCT new_fid)::numeric AS updated_shapes_with_changes,
    COUNT(*) FILTER (WHERE original_shape_count >= 2)::numeric AS many_original_shapes_same_code_rows,
    COUNT(*) FILTER (WHERE change_class = 'code_normalization_only')::numeric AS normalization_only_rows,
    COUNT(*) FILTER (WHERE change_class = 'zone_code_changed')::numeric AS substantive_change_rows,
    COALESCE(SUM(intersection_area_m2), 0)::numeric AS total_changed_area_m2,
    COALESCE(SUM(intersection_area_m2) FILTER (WHERE change_class = 'zone_code_changed'), 0)::numeric AS substantive_change_area_m2,
    COUNT(*) FILTER (WHERE is_screening_candidate_1000m2)::numeric AS rows_ge_1000m2,
    COALESCE(SUM(intersection_area_m2) FILTER (WHERE is_screening_candidate_1000m2), 0)::numeric AS area_ge_1000m2
  FROM zoning.v_charlottetown_draft_zoning_changed_shapes
)
SELECT 'source_layer'::text AS metric_group, source_layer AS metric_name,
       feature_count AS metric_value_numeric,
       format('null_geometries=%s; invalid_geometries=%s', null_geometry_count, invalid_geometry_count) AS metric_value_text
FROM source_stats
UNION ALL SELECT 'zoning_shape_comparison', 'changed_shape_rows', changed_shape_rows, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'updated_shapes_with_changes', updated_shapes_with_changes, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'many_original_shapes_same_code_rows', many_original_shapes_same_code_rows, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'normalization_only_rows', normalization_only_rows, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'substantive_change_rows', substantive_change_rows, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'total_changed_area_m2', total_changed_area_m2, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'substantive_change_area_m2', substantive_change_area_m2, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'rows_ge_1000m2', rows_ge_1000m2, NULL FROM comparison_metrics
UNION ALL SELECT 'zoning_shape_comparison', 'area_ge_1000m2', area_ge_1000m2, NULL FROM comparison_metrics
UNION ALL
SELECT 'zoning_inventory', 'original_non_conservancy_zone_codes', COUNT(DISTINCT zone_code)::numeric,
       string_agg(DISTINCT zone_code, ', ' ORDER BY zone_code)
FROM public."CHTWN_Draft_Zoning_Boundaries"
WHERE upper(trim(zone_code)) <> 'C'
UNION ALL
SELECT 'zoning_inventory', 'updated_zone_codes', COUNT(DISTINCT zone_code)::numeric,
       string_agg(DISTINCT zone_code, ', ' ORDER BY zone_code)
FROM public."CHTWN_Draft_Zoning_Boundaries_Update";

COMMENT ON VIEW zoning.v_charlottetown_draft_zoning_shape_comparison_qa IS
  'QA metrics for updated-map-shape-based zoning comparison with original Conservancy excluded.';

COMMIT;
