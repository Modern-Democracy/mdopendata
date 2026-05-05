-- 013_parcel_resolver_civic_address.sql
--
-- Replaces zoning.parcel_effective_zoning() to resolve a parcel's base
-- zone via the civic-address point layer instead of the not-yet-loaded
-- cadastral parcel layer. Closes the v1 limitation noted in migration
-- 012's header.
--
-- Resolution path (current bylaw):
--
--   PID -> spatial_feature (charlottetown_civic_addresses, attributes->>'PID')
--       -> point geometry (SRID 2954)
--       -> ST_Intersects against polygons of layer
--          charlottetown_current_zoning_boundaries
--       -> zone_spatial_feature.zone_code (canonical bylaw code, with
--          zone_code_crosswalk already applied at registration time).
--
--   Draft bylaw uses charlottetown_draft_zoning_boundaries the same way.
--
-- The function still surfaces Appendix C site-specific exemptions for the
-- parcel and now also intersects against the schedule-A wetlands overlay
-- via spatial_layer.layer_key='charlottetown_schedule_a_wetlands'.

SET search_path = zoning, public;

CREATE OR REPLACE FUNCTION zoning.parcel_effective_zoning(
    p_pid              text,
    p_document_family  text DEFAULT 'current'
) RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_revision_id      bigint;
    v_zoning_layer_key text;
    v_civic_points     jsonb;
    v_civic_geoms      geometry[];
    v_zones            text[];
    v_exemptions       jsonb;
    v_zone_payloads    jsonb;
    v_overlays         jsonb;
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

    v_zoning_layer_key := CASE
        WHEN p_document_family = 'draft' THEN 'charlottetown_draft_zoning_boundaries'
        ELSE 'charlottetown_current_zoning_boundaries'
    END;

    -- 1. Civic-address points carrying the PID.
    SELECT
        COALESCE(jsonb_agg(
                   jsonb_build_object(
                     'civic_address_id', sf.feature_key,
                     'street_no',        sf.attributes->>'STREET_NO',
                     'street_nm',        sf.attributes->>'STREET_NM',
                     'comm_nm',          sf.attributes->>'COMM_NM',
                     'centroid', jsonb_build_object(
                       'lon_4326', ST_X(ST_Transform(sf.geom, 4326)),
                       'lat_4326', ST_Y(ST_Transform(sf.geom, 4326))
                     )
                   )
                   ORDER BY sf.feature_key
                 ), '[]'::jsonb),
        array_agg(sf.geom)
      INTO v_civic_points, v_civic_geoms
      FROM zoning.spatial_feature sf
      JOIN zoning.spatial_layer sl USING (spatial_layer_id)
     WHERE sl.layer_key = 'charlottetown_civic_addresses'
       AND sf.attributes->>'PID' = p_pid;

    -- 2. Zones the civic points fall in, post-crosswalk via
    --    zone_spatial_feature.zone_code.
    IF v_civic_geoms IS NOT NULL AND array_length(v_civic_geoms, 1) > 0 THEN
        SELECT ARRAY(
            SELECT DISTINCT zsf.zone_code
              FROM unnest(v_civic_geoms) AS pt(geom)
              JOIN zoning.spatial_feature poly_sf
                ON ST_Intersects(pt.geom, poly_sf.geom)
              JOIN zoning.spatial_layer poly_sl
                ON poly_sl.spatial_layer_id = poly_sf.spatial_layer_id
               AND poly_sl.layer_key = v_zoning_layer_key
              JOIN zoning.zone_spatial_feature zsf
                ON zsf.spatial_feature_id = poly_sf.spatial_feature_id
               AND zsf.document_revision_id = v_revision_id
        ) INTO v_zones;
    ELSE
        v_zones := ARRAY[]::text[];
    END IF;

    -- 3. Appendix C exemptions tagged for this PID. Reuse the structure
    --    promoted by scripts/apply-charlottetown-appendix-c-exemptions.py.
    SELECT
        COALESCE(jsonb_agg(
                   sf.value_payload->'appendix_c_row'
                     || jsonb_build_object(
                          'structured_fact_id', sf.structured_fact_id,
                          'scope',      sf.value_payload->>'scope',
                          'confidence', sf.value_payload->>'confidence'
                        )
                   ORDER BY sf.value_payload->'appendix_c_row'->>'source_page'
                 ), '[]'::jsonb)
      INTO v_exemptions
      FROM zoning.structured_fact sf
     WHERE sf.is_active
       AND sf.fact_family = 'cross_references'
       AND sf.fact_type   = 'applies_to_parcel'
       AND sf.document_revision_id = v_revision_id
       AND sf.value_payload->'target_ref'->>'source_ref_id' = ('parcel:' || p_pid);

    -- If the parcel is unknown to BOTH the civic-address layer AND
    -- Appendix C, return NULL so callers can distinguish "no data" from
    -- "data with empty fields".
    IF v_civic_geoms IS NULL AND jsonb_array_length(v_exemptions) = 0 THEN
        RETURN NULL;
    END IF;

    -- 4. Effective payload per zone the parcel falls in.
    v_zone_payloads := COALESCE((
        SELECT jsonb_agg(zoning.zone_effective_payload(zone_code, v_revision_id))
          FROM unnest(v_zones) AS zone_code
         WHERE zone_code IS NOT NULL
    ), '[]'::jsonb);

    -- 5. Map overlays — every registered polygon layer the civic-address
    --    points intersect, except the zoning-boundary layers themselves
    --    (already represented by `zones`). For v1 the only overlay layer
    --    loaded is charlottetown_schedule_a_wetlands.
    IF v_civic_geoms IS NOT NULL AND array_length(v_civic_geoms, 1) > 0 THEN
        SELECT
            COALESCE(jsonb_agg(
                       jsonb_build_object(
                         'layer_key', layer_key,
                         'feature_keys', feature_keys
                       )
                       ORDER BY layer_key
                     ), '[]'::jsonb)
          INTO v_overlays
          FROM (
              SELECT poly_sl.layer_key,
                     jsonb_agg(DISTINCT poly_sf.feature_key
                               ORDER BY poly_sf.feature_key) AS feature_keys
                FROM unnest(v_civic_geoms) AS pt(geom)
                JOIN zoning.spatial_feature poly_sf
                  ON ST_Intersects(pt.geom, poly_sf.geom)
                JOIN zoning.spatial_layer poly_sl USING (spatial_layer_id)
               WHERE poly_sl.layer_key NOT IN (
                       'charlottetown_civic_addresses',
                       'charlottetown_current_zoning_boundaries',
                       'charlottetown_draft_zoning_boundaries',
                       'charlottetown_parcel_map',
                       'charlottetown_street_network'
                     )
                 AND poly_sl.expected_geometry_type IN ('POLYGON', 'MULTIPOLYGON')
               GROUP BY poly_sl.layer_key
          ) AS overlay_rollup;
    ELSE
        v_overlays := '[]'::jsonb;
    END IF;

    RETURN jsonb_build_object(
        'pid',                    p_pid,
        'document_family',        p_document_family,
        'document_revision_id',   v_revision_id,
        'civic_addresses',        v_civic_points,
        'zones',                  to_jsonb(COALESCE(v_zones, ARRAY[]::text[])),
        'site_specific_exemptions', v_exemptions,
        'zone_payloads',          v_zone_payloads,
        'map_overlays',           v_overlays,
        'resolution_method',      CASE
            WHEN v_civic_geoms IS NOT NULL THEN 'civic_address_intersect'
            ELSE 'appendix_c_only'
        END
    );
END;
$$;

COMMENT ON FUNCTION zoning.parcel_effective_zoning(text, text) IS
    'Returns a jsonb document for the given parcel PID. Resolves the base zone via the charlottetown_civic_addresses point layer (PID attribute) intersected against the appropriate zoning-boundary layer. Layers Appendix C site-specific exemptions and any overlay-layer intersections (e.g. charlottetown_schedule_a_wetlands) on top. Returns NULL only when the PID is unknown to both the civic-address layer and the Appendix C exemption set.';

-- ---------------------------------------------------------------------------
-- Smoke tests (run interactively after applying)
-- ---------------------------------------------------------------------------
-- 1. Appendix C parcel: PID 339994 (DMUN, current) — should now resolve
--    base zone via civic-address intersect AND surface the exemption.
-- SELECT (zoning.parcel_effective_zoning('339994'))->'zones',
--        (zoning.parcel_effective_zoning('339994'))->'resolution_method',
--        jsonb_array_length((zoning.parcel_effective_zoning('339994'))->'site_specific_exemptions') AS n_ex;
-- -- Expect: zones=["DMUN"], resolution_method="civic_address_intersect", n_ex=1.
--
-- 2. Non-Appendix-C parcel: PID 338129 (65 Great George St) — should now
--    resolve to its current zone with empty exemptions.
-- SELECT (zoning.parcel_effective_zoning('338129'))->'zones',
--        jsonb_array_length((zoning.parcel_effective_zoning('338129'))->'site_specific_exemptions');
-- -- Expect: zones=["DMUN"] (or similar), n_ex=0.
--
-- 3. Draft-family lookup uses the draft zoning boundary layer.
-- SELECT (zoning.parcel_effective_zoning('339994', 'draft'))->'zones';
-- -- Expect: a zone code from the draft taxonomy (e.g. "DMS").
--
-- 4. Truly unknown PID returns NULL.
-- SELECT zoning.parcel_effective_zoning('00000000');
-- -- Expect NULL.
