-- 016_spatial_layer_missing_source_status.sql
--
-- Defensive status normalization for Charlottetown spatial layers.
-- Migration 006 owns the rerunnable registration workflow; this migration
-- exists to normalize databases that applied the earlier 006 during the
-- empty-volume rebuild incident.

SET search_path = zoning, public;

UPDATE zoning.spatial_layer sl
   SET status = CASE
                  WHEN EXISTS (
                         SELECT 1
                           FROM zoning.spatial_feature sf
                          WHERE sf.spatial_layer_id = sl.spatial_layer_id
                       )
                    THEN 'loaded'
                  ELSE 'registered'
                END,
       metadata = CASE
                    WHEN EXISTS (
                           SELECT 1
                             FROM zoning.spatial_feature sf
                            WHERE sf.spatial_layer_id = sl.spatial_layer_id
                         )
                      THEN sl.metadata
                           - 'source_table_missing_at_migration'
                           - 'source_table_missing_checked_at'
                    WHEN sl.source_schema IS NOT NULL
                     AND sl.source_table IS NOT NULL
                     AND to_regclass(format('%I.%I', sl.source_schema, sl.source_table)) IS NULL
                      THEN sl.metadata
                           || jsonb_build_object(
                                'source_table_missing_at_migration', true,
                                'source_table_missing_checked_at', now()
                              )
                    ELSE sl.metadata
                  END
 WHERE sl.layer_key LIKE 'charlottetown_%';
