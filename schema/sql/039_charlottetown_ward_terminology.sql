BEGIN;

-- Canonical Charlottetown terminology:
--   electoral ward       = former voting district
--   polling division     = former voting area
DO $$
BEGIN
  IF to_regclass('public."CHTWN_Voting_Areas"') IS NOT NULL
     AND to_regclass('public."CHTWN_Polling_Divisions"') IS NULL THEN
    ALTER TABLE public."CHTWN_Voting_Areas" RENAME TO "CHTWN_Polling_Divisions";
  END IF;
  IF to_regclass('public."CHTWN_Voting_Districts"') IS NOT NULL
     AND to_regclass('public."CHTWN_Electoral_Wards"') IS NULL THEN
    ALTER TABLE public."CHTWN_Voting_Districts" RENAME TO "CHTWN_Electoral_Wards";
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'voting_area_code')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'polling_division_code') THEN
    ALTER TABLE public."CHTWN_Polling_Divisions" RENAME COLUMN voting_area_code TO polling_division_code;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'district_code')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'ward_code') THEN
    ALTER TABLE public."CHTWN_Polling_Divisions" RENAME COLUMN district_code TO ward_code;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'district_number')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'ward_number') THEN
    ALTER TABLE public."CHTWN_Polling_Divisions" RENAME COLUMN district_number TO ward_number;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'voting_area_number')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Polling_Divisions' AND column_name = 'polling_division_number') THEN
    ALTER TABLE public."CHTWN_Polling_Divisions" RENAME COLUMN voting_area_number TO polling_division_number;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Electoral_Wards' AND column_name = 'district_code')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Electoral_Wards' AND column_name = 'ward_code') THEN
    ALTER TABLE public."CHTWN_Electoral_Wards" RENAME COLUMN district_code TO ward_code;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Electoral_Wards' AND column_name = 'district_number')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Electoral_Wards' AND column_name = 'ward_number') THEN
    ALTER TABLE public."CHTWN_Electoral_Wards" RENAME COLUMN district_number TO ward_number;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Electoral_Wards' AND column_name = 'voting_area_count')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'CHTWN_Electoral_Wards' AND column_name = 'polling_division_count') THEN
    ALTER TABLE public."CHTWN_Electoral_Wards" RENAME COLUMN voting_area_count TO polling_division_count;
  END IF;
END $$;

UPDATE zoning.spatial_layer
SET layer_key = 'charlottetown_polling_divisions',
    source_path = 'data/spatial/charlottetown/charlottetown-wards-municipal-fit-topology-corrected.gpkg',
    source_table = 'CHTWN_Polling_Divisions',
    source_layer = 'polling_divisions_municipal_fit',
    primary_feature_key = 'polling_division_code',
    metadata = metadata || jsonb_build_object(
      'terminology', 'polling_divisions',
      'former_layer_key', 'charlottetown_voting_areas'
    )
WHERE layer_key = 'charlottetown_voting_areas';

UPDATE zoning.spatial_layer
SET layer_key = 'charlottetown_electoral_wards',
    source_path = 'data/spatial/charlottetown/charlottetown-wards-municipal-fit-topology-corrected.gpkg',
    source_table = 'CHTWN_Electoral_Wards',
    source_layer = 'electoral_wards_municipal_fit',
    primary_feature_key = 'ward_code',
    metadata = metadata || jsonb_build_object(
      'terminology', 'electoral_wards',
      'former_layer_key', 'charlottetown_voting_districts'
    )
WHERE layer_key = 'charlottetown_voting_districts';

DELETE FROM zoning.spatial_feature sf
USING zoning.spatial_layer sl
WHERE sf.spatial_layer_id = sl.spatial_layer_id
  AND sl.layer_key IN ('charlottetown_polling_divisions', 'charlottetown_electoral_wards');

DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_polling_divisions CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_electoral_wards CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_voting_areas CASCADE;
DROP MATERIALIZED VIEW IF EXISTS zoning.v_charlottetown_voting_districts CASCADE;

DO $$
BEGIN
  IF to_regclass('public."CHTWN_Polling_Divisions"') IS NOT NULL THEN
    INSERT INTO zoning.spatial_feature (
      spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason
    )
    SELECT sl.spatial_layer_id,
           t.polling_division_code,
           to_jsonb(t) - 'geom',
           t.geom::geometry(MultiPolygon, 2954),
           ST_IsValid(t.geom),
           ST_IsValidReason(t.geom)
    FROM public."CHTWN_Polling_Divisions" t
    JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_polling_divisions'
    ON CONFLICT (spatial_layer_id, feature_key) DO UPDATE SET
      attributes = EXCLUDED.attributes,
      geom = EXCLUDED.geom,
      is_valid = EXCLUDED.is_valid,
      validation_reason = EXCLUDED.validation_reason;
  END IF;

  IF to_regclass('public."CHTWN_Electoral_Wards"') IS NOT NULL THEN
    INSERT INTO zoning.spatial_feature (
      spatial_layer_id, feature_key, attributes, geom, is_valid, validation_reason
    )
    SELECT sl.spatial_layer_id,
           t.ward_code,
           to_jsonb(t) - 'geom',
           t.geom::geometry(MultiPolygon, 2954),
           ST_IsValid(t.geom),
           ST_IsValidReason(t.geom)
    FROM public."CHTWN_Electoral_Wards" t
    JOIN zoning.spatial_layer sl ON sl.layer_key = 'charlottetown_electoral_wards'
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
WHERE sl.layer_key IN ('charlottetown_polling_divisions', 'charlottetown_electoral_wards');

CREATE MATERIALIZED VIEW zoning.v_charlottetown_polling_divisions AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key AS polling_division_code,
  sf.attributes ->> 'ward_code' AS ward_code,
  (sf.attributes ->> 'ward_number')::integer AS ward_number,
  (sf.attributes ->> 'polling_division_number')::integer AS polling_division_number,
  sf.attributes ->> 'source_pdf' AS source_pdf,
  sf.attributes ->> 'source_fill_rgb' AS source_fill_rgb,
  (sf.attributes ->> 'area_m2')::double precision AS area_m2,
  (sf.attributes ->> 'label_match_distance_m')::double precision AS label_match_distance_m,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_polling_divisions'
WITH DATA;
CREATE UNIQUE INDEX ux_v_charlottetown_polling_divisions_id ON zoning.v_charlottetown_polling_divisions (spatial_feature_id);
CREATE UNIQUE INDEX ux_v_charlottetown_polling_divisions_code ON zoning.v_charlottetown_polling_divisions (polling_division_code);
CREATE INDEX ix_v_charlottetown_polling_divisions_ward ON zoning.v_charlottetown_polling_divisions (ward_code);
CREATE INDEX sidx_v_charlottetown_polling_divisions_geom ON zoning.v_charlottetown_polling_divisions USING gist (geom);

CREATE MATERIALIZED VIEW zoning.v_charlottetown_electoral_wards AS
SELECT
  sf.spatial_feature_id,
  sf.feature_key AS ward_code,
  (sf.attributes ->> 'ward_number')::integer AS ward_number,
  (sf.attributes ->> 'polling_division_count')::integer AS polling_division_count,
  sf.attributes ->> 'source_pdf' AS source_pdf,
  sf.attributes ->> 'source_fill_rgb' AS source_fill_rgb,
  (sf.attributes ->> 'area_m2')::double precision AS area_m2,
  sf.attributes,
  sf.is_valid,
  sf.validation_reason,
  sf.geom::geometry(MultiPolygon, 2954) AS geom
FROM zoning.spatial_feature sf
JOIN zoning.spatial_layer sl ON sl.spatial_layer_id = sf.spatial_layer_id
WHERE sl.layer_key = 'charlottetown_electoral_wards'
WITH DATA;
CREATE UNIQUE INDEX ux_v_charlottetown_electoral_wards_id ON zoning.v_charlottetown_electoral_wards (spatial_feature_id);
CREATE UNIQUE INDEX ux_v_charlottetown_electoral_wards_code ON zoning.v_charlottetown_electoral_wards (ward_code);
CREATE INDEX sidx_v_charlottetown_electoral_wards_geom ON zoning.v_charlottetown_electoral_wards USING gist (geom);

COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_polling_divisions IS
  'GIS-facing 69-feature Charlottetown polling-division layer extracted from maps/Chtown_All_Wards.pdf.';
COMMENT ON MATERIALIZED VIEW zoning.v_charlottetown_electoral_wards IS
  'GIS-facing 10-feature Charlottetown electoral-ward layer dissolved from the extracted polling divisions.';

COMMIT;
