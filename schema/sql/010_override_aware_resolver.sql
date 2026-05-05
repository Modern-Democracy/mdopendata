-- 010_override_aware_resolver.sql
--
-- Override-aware resolver views for the Charlottetown zoning data layer.
-- Builds on top of migration 008 (zone inheritance closure).
--
-- Adds one new view (`v_zone_override_edge`) and replaces the two effective-
-- regulation/use views with override-aware variants:
--
--   * v_zone_override_edge          one row per active override structured_fact
--                                   (cross_references with natural_key prefixed
--                                   `override|`), with derived source_zone /
--                                   target_kind / target_id columns.
--   * v_zone_effective_uses         (replaced) now carries
--                                   `applicable_overrides` jsonb +
--                                   `superseded_by_override` boolean.
--   * v_zone_effective_requirements (replaced) same.
--
-- Semantics (from wiki/charlottetown/topics/zoning-data-layer-backlog.md
-- Task 2 Open Decisions):
--   * `references_zone` edges are filtered out — they are rezoning permissions,
--     not inheritance or override edges.
--   * Source-zone derivation: parsed from the `zone-<code>-clause-...` /
--     `zone-<code>-section-...` prefix when the override is anchored on a zone-
--     specific clause/section. Document-anchored overrides (general provisions,
--     Appendix C) get NULL source_zone and surface against every zone via
--     `target_kind` matching.
--   * No physical filtering of superseded rows. We surface every applicable
--     override in `applicable_overrides[]` and set `superseded_by_override`
--     when there is a clause- or section-targeted override with
--     join_behavior IN ('exclude_target_values','override_target_values') that
--     hits the row's source clause. The visualization layer decides whether
--     to render the row, strike it through, or replace it.
--   * Zone-targeted, document-targeted, and external-source-targeted overrides
--     are surfaced in `applicable_overrides[]` only — they are too coarse to
--     auto-apply at row scope.

SET search_path = zoning, public;

-- ---------------------------------------------------------------------------
-- 1) Override edges projected into a uniform shape
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_zone_override_edge AS
WITH base AS (
    SELECT
        sf.structured_fact_id,
        sf.document_revision_id,
        sf.source_record_table,
        sf.source_record_key,
        sf.fact_type                                                  AS relationship_type,
        sf.value_payload->>'join_behavior'                            AS join_behavior,
        sf.value_payload->>'scope'                                    AS scope,
        sf.value_payload->'source_ref'->>'source_ref_type'            AS source_ref_type,
        sf.value_payload->'source_ref'->>'source_ref_id'              AS source_ref_id,
        sf.value_payload->'target_ref'->>'source_ref_type'            AS target_kind,
        sf.value_payload->'target_ref'->>'source_ref_id'              AS target_id
    FROM zoning.structured_fact sf
    WHERE sf.is_active
      AND sf.fact_family = 'cross_references'
      AND sf.natural_key LIKE 'override|%'
      AND sf.fact_type <> 'references_zone'   -- per Open Decision #3
)
SELECT
    b.structured_fact_id,
    b.document_revision_id,
    b.source_ref_type,
    b.source_ref_id,
    -- Source-zone is best-effort: anchored on a zone-specific clause/section,
    -- NULL for document-wide overrides.
    CASE
        WHEN b.source_ref_type = 'clause' AND b.source_ref_id LIKE 'zone-%'
            THEN UPPER(regexp_replace(b.source_ref_id,
                                      '^zone-([a-z0-9-]+?)-clause-.*$', '\1'))
        WHEN b.source_ref_type = 'section' AND b.source_ref_id LIKE 'zone-%'
            THEN UPPER(regexp_replace(b.source_ref_id,
                                      '^zone-([a-z0-9-]+?)-section-.*$', '\1'))
        ELSE NULL
    END                                                               AS source_zone,
    b.target_kind,
    b.target_id,
    CASE WHEN b.target_kind = 'zone' THEN b.target_id ELSE NULL END    AS target_zone,
    b.relationship_type,
    b.join_behavior,
    b.scope
FROM base b;

COMMENT ON VIEW zoning.v_zone_override_edge IS
    'Override edges projected from active cross_references structured_facts whose natural_key starts with `override|`. references_zone facts are filtered out. source_zone is parsed from the source clause/section id prefix when the override is anchored in a zone-specific clause; document-anchored overrides have NULL source_zone and surface via target_kind matching in v_zone_effective_uses / v_zone_effective_requirements.';

-- ---------------------------------------------------------------------------
-- Helper: clause -> section_source_id resolution for section-targeted matching
-- (used as a CTE inline in the views below; defined here as a view so the
-- subqueries stay readable.)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_clause_section_lookup AS
SELECT
    c.document_revision_id,
    c.clause_source_id,
    s.section_source_id
FROM zoning.clause c
JOIN zoning.section s ON s.section_id = c.section_id
WHERE c.is_active AND s.is_active;

COMMENT ON VIEW zoning.v_clause_section_lookup IS
    'Lookup from clause_source_id to section_source_id. Used by the override-aware effective-rule views to resolve section-targeted override matches.';

-- ---------------------------------------------------------------------------
-- 2) Override-aware effective uses
--
-- Same shape as the migration-008 view, plus:
--   * applicable_overrides   jsonb[] of override descriptors that target this
--                            zone, this row's source clause, this row's section,
--                            or the entire document.
--   * superseded_by_override boolean, true when an exclude/override override
--                            targets this row's source clause or section.
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS zoning.v_zone_effective_uses CASCADE;

CREATE VIEW zoning.v_zone_effective_uses AS
WITH base_uses AS (
    SELECT
        sf.document_revision_id,
        UPPER(regexp_replace(sf.value_payload->>'source_clause_ref',
                             '^zone-([a-z0-9-]+?)-clause-.*$', '\1')) AS owner_zone,
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

COMMENT ON VIEW zoning.v_zone_effective_uses IS
    'Override-aware effective uses per zone. Same own/inherited shape as in migration 008 with two additions: superseded_by_override (true when an exclude/override-targeted override hits this row''s source clause or section) and applicable_overrides (jsonb array of every override that targets this zone, the row''s clause/section, or the document as a whole). The view never physically filters rows; the visualization layer decides how to render superseded entries.';

-- ---------------------------------------------------------------------------
-- 3) Override-aware effective requirements
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS zoning.v_zone_effective_requirements CASCADE;

CREATE VIEW zoning.v_zone_effective_requirements AS
WITH base_reqs AS (
    SELECT
        sf.document_revision_id,
        UPPER(regexp_replace(
            COALESCE(
                sf.value_payload->'source_refs'->0->>'source_ref_id',
                sf.value_payload->>'source_clause_ref'
            ),
            '^zone-([a-z0-9-]+?)-(?:clause|section).*$', '\1')) AS owner_zone,
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

COMMENT ON VIEW zoning.v_zone_effective_requirements IS
    'Override-aware effective requirements per zone. Same own/inherited shape as in migration 008 with three additions: source_clause_ref (carried through so callers can match overrides back to the originating clause), superseded_by_override (true when an exclude/override-targeted override hits this row''s source clause or section), and applicable_overrides (jsonb array of every override that targets this zone, the row''s clause/section, or the document as a whole). Rows are not physically filtered; the visualization layer decides how to render superseded entries.';

-- ---------------------------------------------------------------------------
-- Smoke tests (run interactively after applying the migration)
-- ---------------------------------------------------------------------------
-- 1. WF FFE rule should be tagged superseded by the does_not_apply override on
--    zone-wf-clause-34-5-1 (zone-targeted; surfaces in applicable_overrides for
--    every WF row but not in superseded_by_override at row scope).
--
-- SELECT requirement_label_raw,
--        superseded_by_override,
--        jsonb_array_length(applicable_overrides) AS n_overrides
--   FROM zoning.v_zone_effective_requirements
--  WHERE root_zone='WF' AND document_revision_id=1
--    AND requirement_text_raw ILIKE '%finished floor elevation%';
-- -- Expect 1 row with n_overrides >= 1 (the does_not_apply edge surfaces).
--
-- 2. MUC inheritance topology unchanged.
--
-- SELECT MAX(depth) AS max_depth, COUNT(DISTINCT ancestor_zone) AS ancestors
--   FROM zoning.v_zone_inheritance_closure
--  WHERE root_zone='MUC' AND document_revision_id=1;
-- -- Expect (6, 10).
--
-- 3. Appendix C zone-targeted overrides surface in applicable_overrides for
--    every requirement of the affected zones.
--
-- SELECT root_zone,
--        bool_and(jsonb_array_length(applicable_overrides) >= 1) AS every_row_has_override,
--        COUNT(*) AS n_rows
--   FROM zoning.v_zone_effective_requirements
--  WHERE root_zone IN ('C-1','DC','WF','I') AND document_revision_id=1
--  GROUP BY root_zone ORDER BY root_zone;
-- -- Expect every_row_has_override=true for each zone listed.
--
-- 4. references_zone edges (RH -> GC, RH -> GN) are filtered out of override
--    edges entirely.
--
-- SELECT COUNT(*) FROM zoning.v_zone_override_edge WHERE relationship_type='references_zone';
-- -- Expect 0.
