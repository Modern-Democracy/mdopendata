BEGIN;

-- Refresh the district registration after the ward-map extraction removes
-- sub-threshold source slivers from dissolved district interior rings.
UPDATE zoning.spatial_layer
SET source_path = 'data/spatial/charlottetown/charlottetown-wards-municipal-fit-clean.gpkg',
    metadata = metadata || jsonb_build_object(
      'district_hole_cleanup_min_area_m2', 1000.0,
      'district_hole_cleanup_rule', 'retain interior rings at or above threshold; remove smaller source slivers'
    )
WHERE layer_key = 'charlottetown_voting_districts';

DELETE FROM zoning.spatial_feature sf
USING zoning.spatial_layer sl
WHERE sf.spatial_layer_id = sl.spatial_layer_id
  AND sl.layer_key = 'charlottetown_voting_districts';

DO $$
BEGIN
  IF to_regclass('public."CHTWN_Voting_Districts"') IS NOT NULL THEN
    INSERT INTO zoning.spatial_feature (
      spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason
    )
    SELECT sl.spatial_layer_id,
           t.district_code,
           to_jsonb(t) - 'geom',
           t.geom::geometry(MultiPolygon, 2954),
           ST_IsValid(t.geom),
           ST_IsValidReason(t.geom)
    FROM public."CHTWN_Voting_Districts" t
    JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_voting_districts'
    ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
      attributes = EXCLUDED.attributes,
      geom = EXCLUDED.geom,
      is_valid = EXCLUDED.is_valid,
      validation_reason = EXCLUDED.validation_reason;
  END IF;
END $$;

UPDATE zoning.spatial_layer sl
SET status = CASE WHEN EXISTS (
                  SELECT 1 FROM zoning.spatial_feature sf
                  WHERE sf.spatial_layer_id = sl.spatial_layer_id
                ) THEN 'loaded' ELSE 'registered' END
WHERE sl.layer_key = 'charlottetown_voting_districts';

REFRESH MATERIALIZED VIEW zoning.v_charlottetown_voting_districts;

COMMIT;
