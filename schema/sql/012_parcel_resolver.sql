-- 012_parcel_resolver.sql
--
-- Parcel-effective-zoning resolver (backlog Task 3, v1).
--
-- Adds two SQL functions composing the zoning layer's row-level views
-- into a single jsonb payload per parcel:
--
--   * zoning.zone_effective_payload(zone_code text, revision_id bigint)
--       returns jsonb — effective uses, effective requirements (with
--       override-aware columns from migration 011), and applicable
--       overrides for the zone, ready to embed in higher-level lookups.
--
--   * zoning.parcel_effective_zoning(pid text, document_family text)
--       returns jsonb — looks the PID up against the Appendix C
--       exemption rows promoted by
--       `scripts/apply-charlottetown-appendix-c-exemptions.py`,
--       resolves the parcel's zone from `zone_code_at_amendment`, and
--       layers the zone payload + exemption rows + spatial overlays
--       (where derivable) into one document.
--
-- Known v1 gap: `public.parcels` is currently empty and the
-- `charlottetown_parcel_map` spatial layer is a polygonized derivation
-- with no PID column. Consequently `parcel_effective_zoning` only
-- returns a non-NULL document for PIDs that appear in Appendix C
-- (the 36 high-confidence rows + any needs_review rows you opted in
-- via `--include-needs-review`). For non-Appendix-C PIDs the function
-- returns NULL and the caller should fall back to a geometry-based
-- lookup once cadastral data is loaded. Tracked as a follow-up in
-- `wiki/charlottetown/topics/zoning-data-layer-backlog.md` (Task 3
-- "Known limitations").

SET search_path = zoning, public;

-- ---------------------------------------------------------------------------
-- 1) Zone-effective payload
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION zoning.zone_effective_payload(
    p_zone_code     text,
    p_revision_id   bigint
) RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
    SELECT jsonb_build_object(
        'zone_code', p_zone_code,
        'document_revision_id', p_revision_id,
        'effective_uses', COALESCE((
            SELECT jsonb_agg(
                     jsonb_build_object(
                       'use_name_raw',           u.use_name_raw,
                       'use_status',             u.use_status,
                       'depth',                  u.depth,
                       'contributing_zone',      u.contributing_zone,
                       'use_clause_ref',         u.use_clause_ref,
                       'via_clause_ref',         u.via_clause_ref,
                       'superseded_by_override', u.superseded_by_override,
                       'applicable_overrides',   u.applicable_overrides
                     )
                     ORDER BY u.depth, u.use_status, u.use_name_raw
                   )
              FROM zoning.v_zone_effective_uses u
             WHERE u.root_zone = p_zone_code
               AND u.document_revision_id = p_revision_id
        ), '[]'::jsonb),
        'effective_requirements', COALESCE((
            SELECT jsonb_agg(
                     jsonb_build_object(
                       'requirement_label_raw', r.requirement_label_raw,
                       'requirement_type',      r.requirement_type,
                       'requirement_category',  r.requirement_category,
                       'requirement_text_raw',  r.requirement_text_raw,
                       'numeric_value_refs',    r.numeric_value_refs,
                       'depth',                 r.depth,
                       'contributing_zone',     r.contributing_zone,
                       'source_clause_ref',     r.source_clause_ref,
                       'via_clause_ref',        r.via_clause_ref,
                       'superseded_by_override', r.superseded_by_override,
                       'applicable_overrides',  r.applicable_overrides
                     )
                     ORDER BY r.depth, r.requirement_category, r.requirement_label_raw
                   )
              FROM zoning.v_zone_effective_requirements r
             WHERE r.root_zone = p_zone_code
               AND r.document_revision_id = p_revision_id
        ), '[]'::jsonb)
    );
$$;

COMMENT ON FUNCTION zoning.zone_effective_payload(text, bigint) IS
    'Returns a jsonb payload with effective_uses[] and effective_requirements[] for a zone, including the override-aware columns added by migration 010 + 011. Composable with parcel-level resolvers.';

-- ---------------------------------------------------------------------------
-- 2) Parcel-effective resolver
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION zoning.parcel_effective_zoning(
    p_pid              text,
    p_document_family  text DEFAULT 'current'
) RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_revision_id  bigint;
    v_target_id    text;
    v_exemptions   jsonb;
    v_zones        text[];
    v_payload      jsonb;
    v_overlays     jsonb;
BEGIN
    IF p_pid IS NULL OR length(trim(p_pid)) = 0 THEN
        RETURN NULL;
    END IF;

    SELECT MAX(dr.document_revision_id) INTO v_revision_id
      FROM zoning.document_revision dr
      JOIN zoning.bylaw_document bd USING (bylaw_document_id)
     WHERE bd.document_family = p_document_family;
    IF v_revision_id IS NULL THEN
        RETURN NULL;
    END IF;

    v_target_id := 'parcel:' || p_pid;

    -- Pull every Appendix C exemption row tagged for this parcel.
    SELECT
        jsonb_agg(
          sf.value_payload->'appendix_c_row'
            || jsonb_build_object(
                 'structured_fact_id', sf.structured_fact_id,
                 'scope', sf.value_payload->>'scope',
                 'confidence', sf.value_payload->>'confidence'
               )
          ORDER BY sf.value_payload->'appendix_c_row'->>'source_page'
        ),
        array_agg(DISTINCT sf.value_payload->'appendix_c_row'->>'zone_code_at_amendment')
    INTO v_exemptions, v_zones
      FROM zoning.structured_fact sf
     WHERE sf.is_active
       AND sf.fact_family = 'cross_references'
       AND sf.fact_type   = 'applies_to_parcel'
       AND sf.document_revision_id = v_revision_id
       AND sf.value_payload->'target_ref'->>'source_ref_id' = v_target_id;

    IF v_exemptions IS NULL THEN
        -- Not in Appendix C; without cadastral PID-to-geometry data we
        -- can't resolve the base zone here. See migration header for
        -- context.
        RETURN NULL;
    END IF;

    -- One zone-effective payload per distinct zone_code_at_amendment
    -- the exemptions name (almost always one).
    v_payload := COALESCE((
        SELECT jsonb_agg(zoning.zone_effective_payload(zone_code, v_revision_id))
          FROM unnest(v_zones) AS zone_code
         WHERE zone_code IS NOT NULL
    ), '[]'::jsonb);

    -- Map-overlay intersection placeholder. Without a PID-keyed parcel
    -- geometry we can only flag overlays the parcel _might_ touch by
    -- proxy of its civic address; leave empty for v1.
    v_overlays := '[]'::jsonb;

    RETURN jsonb_build_object(
        'pid',                   p_pid,
        'document_family',       p_document_family,
        'document_revision_id',  v_revision_id,
        'zones_at_amendment',    to_jsonb(v_zones),
        'site_specific_exemptions', v_exemptions,
        'zone_payloads',         v_payload,
        'map_overlays',          v_overlays,
        'resolution_method',     'appendix_c_pid_lookup'
    );
END;
$$;

COMMENT ON FUNCTION zoning.parcel_effective_zoning(text, text) IS
    'Returns a jsonb document for the given parcel PID by looking it up against the Appendix C site-specific exemption facts loaded by scripts/apply-charlottetown-appendix-c-exemptions.py. v1 limitation: returns NULL for PIDs that are not in Appendix C, because cadastral PID-to-geometry data is not yet loaded; once it is, extend this function to fall back on ST_Intersects against the cadastral layer.';

-- ---------------------------------------------------------------------------
-- Smoke tests (run interactively after applying)
-- ---------------------------------------------------------------------------
-- 1. Fitness Centre parcel — DMUN single-PID exemption.
-- SELECT jsonb_pretty(zoning.parcel_effective_zoning('339994'));
-- -- Expect: zones_at_amendment=["DMUN"], one site_specific_exemption, the
-- -- DMUN zone payload with effective_uses[] and effective_requirements[].
--
-- 2. C-1 dental clinic parcel.
-- SELECT zones_at_amendment, jsonb_array_length(site_specific_exemptions) AS n_exemptions
--   FROM jsonb_to_record(zoning.parcel_effective_zoning('669796'))
--     AS x(zones_at_amendment jsonb, site_specific_exemptions jsonb);
-- -- Expect: zones=["C-1"], n_exemptions=1.
--
-- 3. Multi-amendment parcel — PID 342790 (199 Grafton Street) has multiple
-- Appendix C entries on different pages.
-- SELECT jsonb_array_length(site_specific_exemptions) AS n
--   FROM jsonb_to_record(zoning.parcel_effective_zoning('342790'))
--     AS x(site_specific_exemptions jsonb);
-- -- Expect: 2 (the two high-confidence DMUN entries; the one needs_review
-- -- row is skipped unless --include-needs-review was passed to the applier).
--
-- 4. Non-Appendix-C PID returns NULL.
-- SELECT zoning.parcel_effective_zoning('00000000');
-- -- Expect NULL.
