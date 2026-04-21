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

CREATE OR REPLACE VIEW hrm.v_geometry_registry_qgis AS
SELECT
  gr.geometry_registry_pk,
  gr.source_schema,
  gr.source_table,
  gr.source_identifier,
  gr.feature_class,
  gr.feature_key,
  gr.feature_name,
  gr.bylaw_slug,
  gr.jurisdiction,
  gr.source_label_raw,
  gr.match_method,
  gr.confidence,
  gr.status,
  gr.attributes,
  gr.geom
FROM hrm.geometry_registry AS gr;

CREATE OR REPLACE VIEW hrm.v_spatial_reference_geometry AS
SELECT
  sr.spatial_ref_pk,
  sr.source_key AS spatial_source_key,
  b.bylaw_slug AS spatial_reference_bylaw_slug,
  z.zone_code AS spatial_reference_zone_code,
  sr.feature_key,
  sr.feature_class,
  sr.source_type,
  sr.source_label_raw,
  sr.schedule_file,
  sr.extraction_status,
  sr.target_schema,
  sr.target_table,
  sr.target_identifier,
  sr.join_method,
  sr.metadata AS spatial_reference_metadata,
  gr.geometry_registry_pk,
  gr.source_schema,
  gr.source_table,
  gr.source_identifier,
  gr.feature_name,
  gr.bylaw_slug AS geometry_bylaw_slug,
  gr.jurisdiction,
  gr.match_method,
  gr.confidence,
  gr.status AS geometry_status,
  gr.attributes AS geometry_attributes,
  gr.geom
FROM hrm.spatial_reference AS sr
LEFT JOIN hrm.bylaw AS b
  ON b.bylaw_pk = sr.bylaw_pk
LEFT JOIN hrm.zone AS z
  ON z.zone_pk = sr.zone_pk
LEFT JOIN hrm.geometry_registry AS gr
  ON gr.source_schema = sr.target_schema
 AND gr.source_table = sr.target_table
 AND gr.source_identifier = sr.target_identifier;

CREATE OR REPLACE VIEW hrm.v_rule_atom_spatial_geometry AS
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
  ra.status AS rule_status,
  rsa.rule_spatial_applicability_pk,
  rsa.source_key AS applicability_source_key,
  rsa.applicability_type,
  rsa.priority_order,
  rsa.notes,
  vsrg.spatial_ref_pk,
  vsrg.spatial_source_key,
  vsrg.feature_key,
  vsrg.feature_class,
  vsrg.source_type,
  vsrg.source_label_raw,
  vsrg.schedule_file,
  vsrg.extraction_status,
  vsrg.target_schema,
  vsrg.target_table,
  vsrg.target_identifier,
  vsrg.join_method,
  vsrg.geometry_registry_pk,
  vsrg.feature_name,
  vsrg.geometry_bylaw_slug,
  vsrg.jurisdiction,
  vsrg.match_method,
  vsrg.confidence,
  vsrg.geometry_status,
  vsrg.geometry_attributes,
  vsrg.geom
FROM hrm.rule_spatial_applicability AS rsa
JOIN hrm.rule_atom AS ra
  ON ra.rule_atom_pk = rsa.rule_atom_pk
LEFT JOIN hrm.zone AS z
  ON z.zone_pk = ra.zone_pk
LEFT JOIN hrm.bylaw AS b
  ON b.bylaw_pk = z.bylaw_pk
LEFT JOIN hrm.v_spatial_reference_geometry AS vsrg
  ON vsrg.spatial_ref_pk = rsa.spatial_ref_pk;

CREATE OR REPLACE VIEW hrm.v_permitted_use_zone_geometry AS
SELECT
  vrazg.rule_atom_pk,
  vrazg.rule_source_key,
  vrazg.bylaw_slug,
  vrazg.zone_code,
  vrazg.rule_type,
  vrazg.metric,
  vrazg.use_name,
  vrazg.numeric_value,
  vrazg.value_text,
  vrazg.unit,
  vrazg.comparator,
  vrazg.condition_text,
  vrazg.applicability_scope,
  vrazg.status,
  vrazg.target_feature_id,
  vrazg.target_description,
  vrazg.geom
FROM hrm.v_rule_atom_zone_geometry AS vrazg
WHERE vrazg.rule_type IN (
  'principal_use',
  'residential_use',
  'accessory_use',
  'ancillary_nonresidential_use',
  'institutional_or_open_space_use',
  'recreation_use',
  'site_specific_residential_use',
  'use_with_specific_standard'
);

CREATE OR REPLACE VIEW hrm.v_prohibited_use_zone_geometry AS
SELECT
  vrazg.rule_atom_pk,
  vrazg.rule_source_key,
  vrazg.bylaw_slug,
  vrazg.zone_code,
  vrazg.rule_type,
  vrazg.metric,
  vrazg.use_name,
  vrazg.numeric_value,
  vrazg.value_text,
  vrazg.unit,
  vrazg.comparator,
  vrazg.condition_text,
  vrazg.applicability_scope,
  vrazg.status,
  vrazg.target_feature_id,
  vrazg.target_description,
  vrazg.geom
FROM hrm.v_rule_atom_zone_geometry AS vrazg
WHERE vrazg.rule_type IN (
  'use_prohibition',
  'development_prohibition'
);

CREATE OR REPLACE VIEW hrm.v_use_rules_zone_geometry AS
SELECT
  vrazg.rule_atom_pk,
  vrazg.rule_source_key,
  vrazg.bylaw_slug,
  vrazg.zone_code,
  vrazg.rule_type,
  CASE
    WHEN vrazg.rule_type IN ('use_prohibition', 'development_prohibition') THEN 'prohibited'
    ELSE 'permitted'
  END AS rule_intent,
  lower(trim(vrazg.use_name)) AS use_name_normalized,
  vrazg.use_name,
  vrazg.metric,
  vrazg.numeric_value,
  vrazg.value_text,
  vrazg.unit,
  vrazg.comparator,
  vrazg.condition_text,
  vrazg.applicability_scope,
  vrazg.status,
  vrazg.target_feature_id,
  vrazg.target_description,
  vrazg.geom
FROM hrm.v_rule_atom_zone_geometry AS vrazg
WHERE vrazg.use_name IS NOT NULL
  AND btrim(vrazg.use_name) <> '';

CREATE OR REPLACE VIEW hrm.v_use_conflict_candidates AS
WITH use_rules AS (
  SELECT
    v.rule_atom_pk,
    v.rule_source_key,
    v.bylaw_slug,
    v.zone_code,
    v.rule_type,
    v.rule_intent,
    v.use_name,
    v.use_name_normalized,
    v.condition_text,
    v.target_feature_id,
    v.target_description,
    v.geom
  FROM hrm.v_use_rules_zone_geometry AS v
)
SELECT
  p.bylaw_slug,
  p.zone_code,
  p.use_name_normalized,
  p.use_name AS permitted_use_name,
  x.use_name AS prohibited_use_name,
  p.rule_atom_pk AS permitted_rule_atom_pk,
  x.rule_atom_pk AS prohibited_rule_atom_pk,
  p.rule_source_key AS permitted_rule_source_key,
  x.rule_source_key AS prohibited_rule_source_key,
  p.rule_type AS permitted_rule_type,
  x.rule_type AS prohibited_rule_type,
  p.condition_text AS permitted_condition_text,
  x.condition_text AS prohibited_condition_text,
  p.target_feature_id,
  p.target_description,
  p.geom
FROM use_rules AS p
JOIN use_rules AS x
  ON x.bylaw_slug = p.bylaw_slug
 AND x.zone_code = p.zone_code
 AND x.target_feature_id = p.target_feature_id
 AND x.use_name_normalized = p.use_name_normalized
WHERE p.rule_intent = 'permitted'
  AND x.rule_intent = 'prohibited'
  AND p.rule_atom_pk <> x.rule_atom_pk;

CREATE OR REPLACE VIEW hrm.v_zone_rule_counts AS
SELECT
  vzgm.zone_pk,
  vzgm.bylaw_slug,
  vzgm.zone_code,
  vzgm.zone_name,
  vzgm.target_feature_id,
  vzgm.target_description,
  count(ra.rule_atom_pk) AS total_rule_count,
  count(*) FILTER (
    WHERE ra.rule_type IN (
      'principal_use',
      'residential_use',
      'accessory_use',
      'ancillary_nonresidential_use',
      'institutional_or_open_space_use',
      'recreation_use',
      'site_specific_residential_use',
      'use_with_specific_standard'
    )
  ) AS permitted_use_count,
  count(*) FILTER (
    WHERE ra.rule_type IN ('use_prohibition', 'development_prohibition')
  ) AS prohibited_use_count,
  count(DISTINCT lower(trim(ra.use_name))) FILTER (
    WHERE ra.use_name IS NOT NULL
      AND btrim(ra.use_name) <> ''
  ) AS distinct_use_name_count,
  vzgm.geom
FROM hrm.v_zone_geometry_matches AS vzgm
LEFT JOIN hrm.rule_atom AS ra
  ON ra.zone_pk = vzgm.zone_pk
GROUP BY
  vzgm.zone_pk,
  vzgm.bylaw_slug,
  vzgm.zone_code,
  vzgm.zone_name,
  vzgm.target_feature_id,
  vzgm.target_description,
  vzgm.geom;

CREATE OR REPLACE VIEW hrm.v_spatial_applicability_rules AS
SELECT
  vrasg.rule_atom_pk,
  vrasg.rule_source_key,
  vrasg.bylaw_slug,
  vrasg.zone_code,
  vrasg.rule_type,
  vrasg.metric,
  vrasg.use_name,
  vrasg.numeric_value,
  vrasg.value_text,
  vrasg.unit,
  vrasg.comparator,
  vrasg.condition_text,
  vrasg.applicability_scope,
  vrasg.rule_status,
  vrasg.rule_spatial_applicability_pk,
  vrasg.applicability_source_key,
  vrasg.applicability_type,
  vrasg.priority_order,
  vrasg.notes,
  vrasg.spatial_ref_pk,
  vrasg.spatial_source_key,
  vrasg.feature_key,
  vrasg.feature_class,
  vrasg.source_type,
  vrasg.source_label_raw,
  vrasg.schedule_file,
  vrasg.extraction_status,
  vrasg.target_schema,
  vrasg.target_table,
  vrasg.target_identifier,
  vrasg.join_method,
  vrasg.geometry_registry_pk,
  vrasg.feature_name,
  vrasg.geometry_bylaw_slug,
  vrasg.jurisdiction,
  vrasg.match_method,
  vrasg.confidence,
  vrasg.geometry_status,
  vrasg.geometry_attributes,
  vrasg.geom
FROM hrm.v_rule_atom_spatial_geometry AS vrasg;
