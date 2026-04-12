CREATE OR REPLACE VIEW hrm.v_zone_geometry_matches AS
SELECT
  z.zone_pk,
  b.bylaw_slug,
  z.zone_code,
  z.zone_name,
  zsm.target_feature_id,
  hz.description AS target_description,
  hz.bylaw_id AS target_bylaw_id,
  hz.geom
FROM hrm.zone AS z
JOIN hrm.bylaw AS b
  ON b.bylaw_pk = z.bylaw_pk
JOIN hrm.zone_spatial_match AS zsm
  ON zsm.zone_pk = z.zone_pk
 AND zsm.target_schema = 'public'
 AND zsm.target_table = 'HFX_Halifax_Zoning_Boundaries'
JOIN public."HFX_Halifax_Zoning_Boundaries" AS hz
  ON hz.source_feature_id = zsm.target_feature_id;

CREATE OR REPLACE VIEW hrm.v_rule_atom_zone_geometry AS
SELECT
  ra.rule_atom_pk,
  ra.source_key AS rule_source_key,
  b.bylaw_slug,
  z.zone_code,
  ra.rule_type,
  ra.metric,
  ra.use_name,
  ra.numeric_value,
  ra.value_text,
  ra.unit,
  ra.comparator,
  ra.condition_text,
  ra.applicability_scope,
  ra.status,
  vzgm.target_feature_id,
  vzgm.target_description,
  vzgm.geom
FROM hrm.rule_atom AS ra
JOIN hrm.zone AS z
  ON z.zone_pk = ra.zone_pk
JOIN hrm.bylaw AS b
  ON b.bylaw_pk = z.bylaw_pk
JOIN hrm.v_zone_geometry_matches AS vzgm
  ON vzgm.zone_pk = z.zone_pk;
