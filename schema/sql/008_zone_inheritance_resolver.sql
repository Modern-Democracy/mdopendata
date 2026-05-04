-- 008_zone_inheritance_resolver.sql
--
-- Zone inheritance resolver for the bylaw structured data.
--
-- Builds four views on top of zoning.structured_fact:
--   * v_zone_inheritance_edge       direct source -> target inheritance edges
--   * v_zone_inheritance_closure    transitive closure with full ancestry path
--   * v_zone_effective_uses         flattened "own + inherited" uses per zone
--   * v_zone_effective_requirements analogous for regulation inheritance
--
-- Edge recovery
-- -------------
-- The preferred path is a direct read of source_ref_id and target_ref_id from
-- structured_fact.value_payload (typed `zone` on both ends). A text-recovery
-- fallback is retained for any rows where the importer landed an extraction
-- without the natural-key ids: the source zone is parsed from the
-- source_clause_ref prefix (e.g. "zone-muc-clause-24-1-1" -> "MUC") and the
-- target zone is matched against zone_code tokens in the clause text, preferring
-- the longest match so "ER-MUVC" wins over "I". The recovery_source column
-- flags which path produced each edge so callers can audit completeness.

SET search_path = zoning, public;

-- ---------------------------------------------------------------------------
-- 1) Direct edges: one row per inheritance fact
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_zone_inheritance_edge AS
WITH
zone_codes AS (
    SELECT DISTINCT zone_code, document_revision_id
    FROM zoning.section
    WHERE document_type = 'zone'
      AND zone_code IS NOT NULL
      AND is_active
),
base AS (
    SELECT
        sf.structured_fact_id,
        sf.document_revision_id,
        sf.fact_type                                                 AS relationship_type,
        sf.value_payload->>'source_clause_ref'                       AS source_clause_ref,
        sf.value_payload->>'join_behavior'                           AS join_behavior,
        sf.value_payload->'source_ref'->>'source_ref_type'           AS source_ref_type,
        sf.value_payload->'source_ref'->>'source_ref_id'             AS source_ref_id,
        sf.value_payload->'target_ref'->>'source_ref_type'           AS target_ref_type,
        sf.value_payload->'target_ref'->>'source_ref_id'             AS target_ref_id
    FROM zoning.structured_fact sf
    WHERE sf.fact_family = 'zone_relationships'
      AND sf.is_active
),
direct AS (
    -- Preferred path: both endpoints are stored on the fact and typed `zone`.
    -- Document-sourced rows (e.g. general provisions referencing a zone) are
    -- intentionally excluded from the inheritance graph.
    SELECT
        b.structured_fact_id,
        b.document_revision_id,
        b.source_ref_id  AS source_zone,
        b.target_ref_id  AS target_zone,
        b.relationship_type,
        b.join_behavior,
        b.source_clause_ref,
        'direct'::text   AS recovery_source
    FROM base b
    WHERE b.source_ref_type = 'zone'
      AND b.target_ref_type = 'zone'
      AND b.source_ref_id IS NOT NULL
      AND b.target_ref_id IS NOT NULL
),
needs_recovery AS (
    -- Defensive fallback: any zone-source row missing a natural-key id.
    SELECT
        b.*,
        UPPER(regexp_replace(b.source_clause_ref,
                             '^zone-([a-z0-9-]+?)-clause-.*$', '\1')) AS source_zone_guess
    FROM base b
    WHERE b.source_clause_ref LIKE 'zone-%'
      AND (
            b.source_ref_id IS NULL
         OR b.target_ref_id IS NULL
         OR b.source_ref_type <> 'zone'
         OR b.target_ref_type <> 'zone'
      )
),
recovered AS (
    SELECT
        nr.structured_fact_id,
        nr.document_revision_id,
        nr.source_zone_guess  AS source_zone,
        z.zone_code           AS target_zone,
        nr.relationship_type,
        nr.join_behavior,
        nr.source_clause_ref,
        'text_recovery'::text AS recovery_source,
        ROW_NUMBER() OVER (
            PARTITION BY nr.structured_fact_id
            ORDER BY LENGTH(z.zone_code) DESC
        ) AS rn
    FROM needs_recovery nr
    JOIN zoning.clause c
      ON c.clause_source_id     = nr.source_clause_ref
     AND c.document_revision_id = nr.document_revision_id
     AND c.is_active
    JOIN zone_codes z
      ON z.document_revision_id = nr.document_revision_id
     AND z.zone_code           <> nr.source_zone_guess
     AND (
            c.clause_text_raw ~* ('\(' || z.zone_code || '\)')
         OR c.clause_text_raw ~* ('\m' || regexp_replace(z.zone_code, '-', '\\-', 'g') || '\s+Zone\M')
         )
)
SELECT structured_fact_id, document_revision_id, source_zone, target_zone,
       relationship_type, join_behavior, source_clause_ref, recovery_source
FROM direct
UNION ALL
SELECT structured_fact_id, document_revision_id, source_zone, target_zone,
       relationship_type, join_behavior, source_clause_ref, recovery_source
FROM recovered
WHERE rn = 1;

COMMENT ON VIEW zoning.v_zone_inheritance_edge IS
    'Direct inheritance edges between zones. Reads source_ref_id and target_ref_id directly from structured_fact.value_payload when both are populated and typed `zone`; falls back to text recovery (clause id prefix + clause-text token match) for rows missing the natural-key ids. recovery_source column flags which path produced each row so downstream queries can audit completeness.';

-- ---------------------------------------------------------------------------
-- 2) Transitive closure: every (root, ancestor) pair with the full path
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_zone_inheritance_closure AS
WITH RECURSIVE
zone_codes AS (
    SELECT DISTINCT zone_code, document_revision_id
    FROM zoning.section
    WHERE document_type = 'zone' AND zone_code IS NOT NULL AND is_active
),
walk AS (
    -- depth 0: every zone is its own ancestor
    SELECT
        z.zone_code               AS root_zone,
        z.zone_code               AS ancestor_zone,
        0::int                    AS depth,
        ARRAY[z.zone_code]        AS path,
        NULL::text                AS relationship_type,
        NULL::text                AS via_clause_ref,
        z.document_revision_id
    FROM zone_codes z

    UNION ALL

    SELECT
        w.root_zone,
        e.target_zone,
        w.depth + 1,
        w.path || e.target_zone,
        e.relationship_type,
        e.source_clause_ref,
        w.document_revision_id
    FROM walk w
    JOIN zoning.v_zone_inheritance_edge e
      ON e.source_zone           = w.ancestor_zone
     AND e.document_revision_id  = w.document_revision_id
    WHERE NOT (e.target_zone = ANY (w.path))   -- cycle guard
      AND w.depth < 10                         -- safety bound
)
SELECT
    root_zone,
    ancestor_zone,
    depth,
    relationship_type,
    via_clause_ref,
    path,
    document_revision_id
FROM walk;

COMMENT ON VIEW zoning.v_zone_inheritance_closure IS
    'Transitive inheritance closure. depth=0 rows are the zones themselves (no edge). depth>0 rows include the relationship_type used to step from path[depth-1] to ancestor_zone, and via_clause_ref pinpoints the bylaw clause that authorized the step. Multiple rows per (root, ancestor) when more than one path exists.';

-- ---------------------------------------------------------------------------
-- 3) Effective uses per zone (own + inherited via inherits_uses)
--    Each row carries provenance back to the source clause and immediate
--    ancestor that contributed it. Use DISTINCT ON for a single-row-per-use
--    "shortest path" projection.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zoning.v_zone_effective_uses AS
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
)
SELECT * FROM own_uses
UNION ALL
SELECT * FROM inherited_uses;

COMMENT ON VIEW zoning.v_zone_effective_uses IS
    'Flattened effective uses per zone. depth=0 rows are uses defined directly on the zone; depth>0 rows are uses inherited via inherits_uses edges, with use_clause_ref pointing at the originating clause and via_clause_ref at the inheritance clause that brought the use in.';

-- ---------------------------------------------------------------------------
-- 4) Effective regulations per zone (own + inherited via inherits_regulations)
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
            '^zone-([a-z0-9-]+?)-(?:clause|section).*$', '\1')) AS owner_zone,
        sf.structured_fact_id,
        sf.fact_type                                  AS requirement_type,
        sf.value_payload->>'requirement_category'     AS requirement_category,
        sf.value_payload->>'requirement_label_raw'    AS requirement_label_raw,
        sf.value_payload->>'requirement_text_raw'     AS requirement_text_raw,
        sf.value_payload->'numeric_value_refs'        AS numeric_value_refs,
        sf.value_payload                              AS value_payload
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
        cl.via_clause_ref
    FROM zoning.v_zone_inheritance_closure cl
    JOIN base_reqs br
      ON br.owner_zone           = cl.ancestor_zone
     AND br.document_revision_id = cl.document_revision_id
    WHERE cl.depth > 0
      AND cl.relationship_type = 'inherits_regulations'
)
SELECT * FROM own_reqs
UNION ALL
SELECT * FROM inherited_reqs;

COMMENT ON VIEW zoning.v_zone_effective_requirements IS
    'Flattened effective requirements per zone, including those inherited via inherits_regulations edges. owner_zone is the zone the requirement is defined on; contributing_zone is identical for own rules and is the immediate ancestor for inherited rules. Override semantics (notwithstanding, exception_to) are not yet applied.';

-- ---------------------------------------------------------------------------
-- Quick smoke tests (run interactively)
-- ---------------------------------------------------------------------------
-- SELECT * FROM zoning.v_zone_inheritance_edge WHERE source_zone='MUC' AND document_revision_id=1;
-- SELECT root_zone, ancestor_zone, depth, relationship_type,
--        array_to_string(path,' -> ') AS chain
--   FROM zoning.v_zone_inheritance_closure
--  WHERE root_zone='MUC' AND document_revision_id=1
--  ORDER BY depth, ancestor_zone;
-- SELECT root_zone, contributing_zone, depth, use_name_raw, use_status
--   FROM zoning.v_zone_effective_uses
--  WHERE root_zone='MUC' AND document_revision_id=1
--  ORDER BY depth, contributing_zone, use_name_raw;
