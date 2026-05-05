-- 011_table_anchored_inheritance.sql
--
-- Single-purpose patch: teach the override-aware effective-rule views
-- (originally introduced in 010) to recognise table-anchored clause ids of
-- the form `zone-<code>-table-...` as zone-owned. The 008/010 base CTEs
-- only matched `zone-<code>-clause-...` and `zone-<code>-section-...`, so
-- requirements anchored on synthetic table-row ids (e.g.
-- `zone-i-table-regulations-for-permitted-uses-row-1`) had owner_zone=NULL
-- and were filtered out of `v_zone_effective_requirements` /
-- `v_zone_effective_uses`. Visible symptom: zone I returned 0 rows from
-- the effective-requirements view despite owning 41 active requirement
-- structured_facts.
--
-- This migration is the minimal regex-only fix called out in
-- `wiki/charlottetown/topics/zoning-data-layer-backlog.md` Task 5. The
-- broader Task 5 (importer-side raw_table provenance, audit-metric
-- simplification) remains backlog and does not gate this patch.
--
-- View signatures are unchanged from 010, so CREATE OR REPLACE is safe.

SET search_path = zoning, public;

-- ---------------------------------------------------------------------------
-- v_zone_effective_uses (regex extended to accept the `table` anchor)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_zone_effective_uses AS
WITH base_uses AS (
    SELECT
        sf.document_revision_id,
        UPPER(regexp_replace(sf.value_payload->>'source_clause_ref',
                             '^zone-([a-z0-9-]+?)-(?:clause|section|table)-.*$',
                             '\1')) AS owner_zone,
        sf.value_payload->>'use_name_raw'      AS use_name_raw,
        sf.value_payload->>'use_status'        AS use_status,
        sf.value_payload->>'source_clause_ref' AS source_clause_ref,
        sf.structured_fact_id
    FROM zoning.structured_fact sf
    WHERE sf.fact_family = 'uses'
      AND sf.is_active
      AND sf.value_payload->>'source_clause_ref' LIKE 'zone-%'
),
own_uses AS (
    SELECT
        bu.document_revision_id,
        bu.owner_zone                                    AS root_zone,
        bu.owner_zone                                    AS contributing_zone,
        0::int                                           AS depth,
        bu.use_name_raw,
        bu.use_status,
        bu.source_clause_ref                             AS use_clause_ref,
        NULL::text                                       AS via_clause_ref,
        bu.structured_fact_id
    FROM base_uses bu
),
inherited_uses AS (
    SELECT DISTINCT ON (cl.root_zone, bu.use_name_raw, bu.use_status, cl.document_revision_id)
        cl.document_revision_id,
        cl.root_zone,
        bu.owner_zone                                    AS contributing_zone,
        cl.depth,
        bu.use_name_raw,
        bu.use_status,
        bu.source_clause_ref                             AS use_clause_ref,
        cl.via_clause_ref,
        bu.structured_fact_id
    FROM zoning.v_zone_inheritance_closure cl
    JOIN base_uses bu
      ON bu.owner_zone           = cl.ancestor_zone
     AND bu.document_revision_id = cl.document_revision_id
    WHERE cl.depth > 0
      AND cl.relationship_type = 'inherits_uses'
    ORDER BY cl.root_zone, bu.use_name_raw, bu.use_status, cl.document_revision_id, cl.depth
),
flattened AS (
    SELECT * FROM own_uses
    UNION ALL
    SELECT * FROM inherited_uses
)
SELECT
    f.document_revision_id,
    f.root_zone,
    f.contributing_zone,
    f.depth,
    f.use_name_raw,
    f.use_status,
    f.use_clause_ref,
    f.via_clause_ref,
    f.structured_fact_id,
    EXISTS (
        SELECT 1 FROM zoning.v_zone_override_edge oe
        WHERE oe.document_revision_id = f.document_revision_id
          AND oe.join_behavior IN ('exclude_target_values', 'override_target_values')
          AND (
              (oe.target_kind = 'clause'  AND oe.target_id = f.use_clause_ref)
              OR (oe.target_kind = 'section' AND f.use_clause_ref IN (
                    SELECT csl.clause_source_id
                      FROM zoning.v_clause_section_lookup csl
                     WHERE csl.section_source_id = oe.target_id
                       AND csl.document_revision_id = oe.document_revision_id
                  ))
          )
    ) AS superseded_by_override,
    COALESCE((
        SELECT jsonb_agg(
                 jsonb_build_object(
                   'structured_fact_id', oe.structured_fact_id,
                   'relationship_type',  oe.relationship_type,
                   'join_behavior',      oe.join_behavior,
                   'target_kind',        oe.target_kind,
                   'target_id',          oe.target_id,
                   'source_ref_type',    oe.source_ref_type,
                   'source_ref_id',      oe.source_ref_id,
                   'scope',              oe.scope
                 )
                 ORDER BY oe.structured_fact_id
               )
        FROM zoning.v_zone_override_edge oe
        WHERE oe.document_revision_id = f.document_revision_id
          AND (
              (oe.target_kind = 'zone' AND oe.target_id = f.root_zone)
              OR oe.target_kind IN ('document', 'external_source')
              OR (oe.target_kind = 'clause'  AND oe.target_id = f.use_clause_ref)
              OR (oe.target_kind = 'section' AND f.use_clause_ref IN (
                    SELECT csl.clause_source_id
                      FROM zoning.v_clause_section_lookup csl
                     WHERE csl.section_source_id = oe.target_id
                       AND csl.document_revision_id = oe.document_revision_id
                  ))
          )
    ), '[]'::jsonb) AS applicable_overrides
FROM flattened f;

-- ---------------------------------------------------------------------------
-- v_zone_effective_requirements (regex extended to accept the `table` anchor)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_zone_effective_requirements AS
WITH base_reqs AS (
    SELECT
        sf.document_revision_id,
        UPPER(regexp_replace(
            COALESCE(
                sf.value_payload->'source_refs'->0->>'source_ref_id',
                sf.value_payload->>'source_clause_ref'
            ),
            '^zone-([a-z0-9-]+?)-(?:clause|section|table).*$', '\1')) AS owner_zone,
        COALESCE(
            sf.value_payload->'source_refs'->0->>'source_ref_id',
            sf.value_payload->>'source_clause_ref'
        )                                              AS source_clause_ref,
        sf.structured_fact_id,
        sf.fact_type                                   AS requirement_type,
        sf.value_payload->>'requirement_category'      AS requirement_category,
        sf.value_payload->>'requirement_label_raw'     AS requirement_label_raw,
        sf.value_payload->>'requirement_text_raw'      AS requirement_text_raw,
        sf.value_payload->'numeric_value_refs'         AS numeric_value_refs
    FROM zoning.structured_fact sf
    WHERE sf.fact_family = 'requirements'
      AND sf.is_active
),
own_reqs AS (
    SELECT
        br.document_revision_id,
        br.owner_zone                  AS root_zone,
        br.owner_zone                  AS contributing_zone,
        0::int                         AS depth,
        br.structured_fact_id,
        br.requirement_type,
        br.requirement_category,
        br.requirement_label_raw,
        br.requirement_text_raw,
        br.numeric_value_refs,
        br.source_clause_ref,
        NULL::text                     AS via_clause_ref
    FROM base_reqs br
    WHERE br.owner_zone IS NOT NULL
),
inherited_reqs AS (
    SELECT
        cl.document_revision_id,
        cl.root_zone,
        br.owner_zone                  AS contributing_zone,
        cl.depth,
        br.structured_fact_id,
        br.requirement_type,
        br.requirement_category,
        br.requirement_label_raw,
        br.requirement_text_raw,
        br.numeric_value_refs,
        br.source_clause_ref,
        cl.via_clause_ref
    FROM zoning.v_zone_inheritance_closure cl
    JOIN base_reqs br
      ON br.owner_zone           = cl.ancestor_zone
     AND br.document_revision_id = cl.document_revision_id
    WHERE cl.depth > 0
      AND cl.relationship_type = 'inherits_regulations'
),
flattened AS (
    SELECT * FROM own_reqs
    UNION ALL
    SELECT * FROM inherited_reqs
)
SELECT
    f.document_revision_id,
    f.root_zone,
    f.contributing_zone,
    f.depth,
    f.structured_fact_id,
    f.requirement_type,
    f.requirement_category,
    f.requirement_label_raw,
    f.requirement_text_raw,
    f.numeric_value_refs,
    f.source_clause_ref,
    f.via_clause_ref,
    EXISTS (
        SELECT 1 FROM zoning.v_zone_override_edge oe
        WHERE oe.document_revision_id = f.document_revision_id
          AND oe.join_behavior IN ('exclude_target_values', 'override_target_values')
          AND (
              (oe.target_kind = 'clause'  AND oe.target_id = f.source_clause_ref)
              OR (oe.target_kind = 'section' AND f.source_clause_ref IN (
                    SELECT csl.clause_source_id
                      FROM zoning.v_clause_section_lookup csl
                     WHERE csl.section_source_id = oe.target_id
                       AND csl.document_revision_id = oe.document_revision_id
                  ))
          )
    ) AS superseded_by_override,
    COALESCE((
        SELECT jsonb_agg(
                 jsonb_build_object(
                   'structured_fact_id', oe.structured_fact_id,
                   'relationship_type',  oe.relationship_type,
                   'join_behavior',      oe.join_behavior,
                   'target_kind',        oe.target_kind,
                   'target_id',          oe.target_id,
                   'source_ref_type',    oe.source_ref_type,
                   'source_ref_id',      oe.source_ref_id,
                   'scope',              oe.scope
                 )
                 ORDER BY oe.structured_fact_id
               )
        FROM zoning.v_zone_override_edge oe
        WHERE oe.document_revision_id = f.document_revision_id
          AND (
              (oe.target_kind = 'zone' AND oe.target_id = f.root_zone)
              OR oe.target_kind IN ('document', 'external_source')
              OR (oe.target_kind = 'clause'  AND oe.target_id = f.source_clause_ref)
              OR (oe.target_kind = 'section' AND f.source_clause_ref IN (
                    SELECT csl.clause_source_id
                      FROM zoning.v_clause_section_lookup csl
                     WHERE csl.section_source_id = oe.target_id
                       AND csl.document_revision_id = oe.document_revision_id
                  ))
          )
    ), '[]'::jsonb) AS applicable_overrides
FROM flattened f;

-- ---------------------------------------------------------------------------
-- Smoke test (run interactively after applying)
-- ---------------------------------------------------------------------------
-- Zone I now appears in the effective-requirements view (was 0 pre-011).
-- SELECT COUNT(*) FROM zoning.v_zone_effective_requirements
--  WHERE root_zone='I' AND document_revision_id=1;
-- -- Expect >= 41.
--
-- Task 2 smoke-test 3 now passes for `I`.
-- SELECT root_zone,
--        bool_and(jsonb_array_length(applicable_overrides) >= 1) AS every_row_has_override
--   FROM zoning.v_zone_effective_requirements
--  WHERE root_zone IN ('C-1','DC','WF','I') AND document_revision_id=1
--  GROUP BY root_zone ORDER BY root_zone;
-- -- Expect every_row_has_override=true for all four zones.
