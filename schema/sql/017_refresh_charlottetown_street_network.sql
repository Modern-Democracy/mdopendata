BEGIN;

UPDATE zoning.spatial_layer
   SET srid = 2954,
       expected_geometry_type = 'MULTILINESTRING',
       feature_count_baseline = 2221,
       invalid_geometry_count = 0,
       status = CASE
                  WHEN to_regclass('public."CHTWN_Street_Network"') IS NULL
                    THEN 'registered'
                  ELSE 'loaded'
                END,
       metadata = metadata
                  || '{"approved_phase4_layer": true, "source": "city_official_street_network"}'::jsonb
                  - 'source_table_missing_at_migration'
                  - 'source_table_missing_checked_at'
 WHERE layer_key = 'charlottetown_street_network';

DO $$
BEGIN
  IF to_regclass('public."CHTWN_Street_Network"') IS NOT NULL THEN
    DELETE FROM zoning.spatial_feature sf
    USING zoning.spatial_layer l
    WHERE sf.spatial_layer_id = l.spatial_layer_id
      AND l.layer_key = 'charlottetown_street_network';

    INSERT INTO zoning.spatial_feature (
      spatial_layer_id,
      feature_key,
      attributes,
      geom,
      is_valid,
      validation_reason
    )
    SELECT
      l.spatial_layer_id,
      t.id::text,
      to_jsonb(t) - 'geom',
      ST_Transform(t.geom, 2954),
      ST_IsValid(t.geom),
      ST_IsValidReason(t.geom)
    FROM public."CHTWN_Street_Network" t
    JOIN zoning.spatial_layer l
      ON l.layer_key = 'charlottetown_street_network';
  END IF;
END $$;

REFRESH MATERIALIZED VIEW zoning.v_charlottetown_street_network;

COMMIT;
