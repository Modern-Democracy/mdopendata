-- 014_inherited_reqs_distinct_on.sql
--
-- Replaces zoning.v_zone_effective_requirements so inherited requirements
-- are projected once per underlying structured_fact on the shortest
-- inheritance path. This mirrors the inherited_uses de-duplication pattern
-- and prevents deep/branchy closures such as C-2 from emitting one copy of
-- the same requirement per ancestor path.

SET search_path = zoning, public;

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
    SELECT DISTINCT ON (cl.root_zone, br.structured_fact_id, cl.document_revision_id)
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
    ORDER BY cl.root_zone, br.structured_fact_id, cl.document_revision_id, cl.depth
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

COMMENT ON VIEW zoning.v_zone_effective_requirements IS
    'Effective requirements per zone, including inherited regulation requirements with override metadata. Inherited rows are de-duplicated by root zone, structured_fact_id, and document revision, keeping the shortest inheritance path.';

-- ---------------------------------------------------------------------------
-- Smoke tests (run interactively after applying)
-- ---------------------------------------------------------------------------
-- 1. C-2 duplicate inherited requirements are collapsed.
-- SELECT COUNT(*) FROM zoning.v_zone_effective_requirements
--  WHERE root_zone='C-2' AND document_revision_id=1;
-- -- Expect a few hundred, not 6923.
--
-- 2. C-2 parcel resolver performance target.
-- EXPLAIN (ANALYZE, BUFFERS)
-- SELECT zoning.parcel_effective_zoning('386557');
-- -- Expect execution time under 300 ms on the local dev DB.
--
-- 3. Spot-check distinct requirement identities for other zones.
-- SELECT root_zone,
--        COUNT(*) AS rows,
--        COUNT(DISTINCT structured_fact_id) AS distinct_facts
--   FROM zoning.v_zone_effective_requirements
--  WHERE root_zone IN ('C-1','DMUN','WF') AND document_revision_id=1
--  GROUP BY root_zone ORDER BY root_zone;
-- -- Expect rows = distinct_facts for each zone.
--
-- 4. Task 2 Appendix-C override visibility still holds.
-- SELECT root_zone,
--        bool_and(jsonb_array_length(applicable_overrides) >= 1) AS every_row_has_override
--   FROM zoning.v_zone_effective_requirements
--  WHERE root_zone IN ('C-1','DC','WF','I') AND document_revision_id=1
--  GROUP BY root_zone ORDER BY root_zone;
-- -- Expect every_row_has_override=true for all four zones.
