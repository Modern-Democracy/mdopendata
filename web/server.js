import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const { Pool } = pg;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = process.env.REPO_ROOT || path.resolve(__dirname, "..");
const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT || 3000);

const publicDir = path.join(__dirname, "public");
const pool = new Pool({
  host: process.env.PGHOST || "localhost",
  port: Number(process.env.PGPORT || 54329),
  database: process.env.PGDATABASE || "mdopendata",
  user: process.env.PGUSER || "mdopendata",
  password: process.env.PGPASSWORD || "mdopendata_dev",
});

function toStringValue(value) {
  return value === null || value === undefined ? "" : String(value);
}

function toJsonValue(value) {
  return value ?? {};
}

function compactText(value) {
  const text = toStringValue(value).trim();
  return text.length === 0 ? null : text;
}

function normalizeLimit(value, fallback, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return Math.min(Math.trunc(parsed), max);
}

function parseBbox(value) {
  if (!value) {
    return null;
  }
  const parts = value.split(",").map((part) => Number(part.trim()));
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) {
    const error = new Error("bbox must be west,south,east,north.");
    error.statusCode = 400;
    throw error;
  }

  const [west, south, east, north] = parts;
  if (west >= east || south >= north) {
    const error = new Error("bbox west/south must be less than east/north.");
    error.statusCode = 400;
    throw error;
  }
  if (west < -180 || east > 180 || south < -90 || north > 90) {
    const error = new Error("bbox coordinates must be WGS84 longitude/latitude values.");
    error.statusCode = 400;
    throw error;
  }
  return { west, south, east, north };
}

function reviewDecision(row) {
  const status = row.db_review_status || row.review_status;
  if (status === "accepted") {
    return "accepted";
  }
  if (status === "rejected") {
    return "rejected";
  }
  return "needs_review";
}

function mapReviewRow(row, index) {
  return {
    row_index: index,
    review_batch: "database",
    review_decision: reviewDecision(row),
    review_decision_source: "zoning.section_equivalence",
    section_equivalence_id: toStringValue(row.section_equivalence_id),
    candidate_method: toStringValue(row.candidate_method),
    candidate_topic: toStringValue(row.candidate_topic),
    db_equivalence_type: toStringValue(row.db_equivalence_type),
    db_review_status: toStringValue(row.db_review_status),
    title_similarity: toStringValue(row.title_similarity),
    text_similarity: toStringValue(row.text_similarity),
    current_section_id: toStringValue(row.current_section_id),
    current_section_key: toStringValue(row.current_section_key),
    current_section_label: toStringValue(row.current_section_label),
    current_section_title: toStringValue(row.current_section_title),
    current_document_type: toStringValue(row.current_document_type),
    current_zone_code: toStringValue(row.current_zone_code),
    current_citations: toJsonValue(row.current_citations),
    draft_section_id: toStringValue(row.draft_section_id),
    draft_section_key: toStringValue(row.draft_section_key),
    draft_section_label: toStringValue(row.draft_section_label),
    draft_section_title: toStringValue(row.draft_section_title),
    draft_document_type: toStringValue(row.draft_document_type),
    draft_zone_code: toStringValue(row.draft_zone_code),
    draft_citations: toJsonValue(row.draft_citations),
    reviewer_notes: toStringValue(row.reviewer_notes),
    updated_at: toStringValue(row.updated_at),
  };
}

async function readRequestJson(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  const body = Buffer.concat(chunks).toString("utf8").trim();
  return body ? JSON.parse(body) : {};
}

async function loadReviewRows() {
  const { rows } = await pool.query(`
    SELECT
      se.section_equivalence_id,
      se.current_section_id,
      se.draft_section_id,
      se.current_section_key,
      se.draft_section_key,
      se.candidate_method,
      se.assigned_topic AS candidate_topic,
      se.equivalence_type AS db_equivalence_type,
      se.review_status AS db_review_status,
      se.title_similarity,
      se.text_similarity,
      se.reviewer_notes,
      se.updated_at,
      cs.section_label_raw AS current_section_label,
      cs.section_title_raw AS current_section_title,
      cs.document_type AS current_document_type,
      cs.zone_code AS current_zone_code,
      cs.citations AS current_citations,
      ds.section_label_raw AS draft_section_label,
      ds.section_title_raw AS draft_section_title,
      ds.document_type AS draft_document_type,
      ds.zone_code AS draft_zone_code,
      ds.citations AS draft_citations
    FROM zoning.section_equivalence se
    JOIN zoning.section cs
      ON cs.section_id = se.current_section_id
    JOIN zoning.section ds
      ON ds.section_id = se.draft_section_id
    ORDER BY cs.source_order, ds.source_order, se.section_equivalence_id
  `);
  return rows.map(mapReviewRow);
}

async function updateReviewDecision(sectionEquivalenceId, decision) {
  if (!["accepted", "rejected"].includes(decision)) {
    const error = new Error("Decision must be accepted or rejected.");
    error.statusCode = 400;
    throw error;
  }

  const accepted = decision === "accepted";
  const { rows } = await pool.query(
    `
    UPDATE zoning.section_equivalence
    SET review_status = $2,
        equivalence_type = CASE WHEN $2 = 'rejected' THEN 'not_equivalent' ELSE equivalence_type END,
        reviewer_notes = concat_ws(
          E'\n',
          nullif(reviewer_notes, ''),
          $3::text
        ),
        updated_at = now()
    WHERE section_equivalence_id = $1
    RETURNING section_equivalence_id
    `,
    [
      sectionEquivalenceId,
      accepted ? "accepted" : "rejected",
      `Web review ${new Date().toISOString()}: ${decision}.`,
    ],
  );
  if (rows.length === 0) {
    const error = new Error("Review row not found.");
    error.statusCode = 404;
    throw error;
  }
}

async function loadSection(sectionId) {
  const sectionResult = await pool.query(
    `
    SELECT
      s.section_id,
      s.section_source_id,
      s.section_label_raw,
      s.section_title_raw,
      s.natural_key,
      s.citations,
      sf.repo_relpath
    FROM zoning.section s
    JOIN zoning.source_file sf
      ON sf.source_file_id = s.source_file_id
    WHERE s.section_id = $1
    `,
    [sectionId],
  );
  const section = sectionResult.rows[0];
  if (!section) {
    return null;
  }

  const [clausesResult, tablesResult] = await Promise.all([
    pool.query(
      `
      SELECT clause_label_raw, clause_text_raw, citations, source_order
      FROM zoning.clause
      WHERE section_id = $1
        AND is_active
      ORDER BY source_order, clause_id
      `,
      [sectionId],
    ),
    pool.query(
      `
      SELECT
        rt.raw_table_id,
        rt.table_title_raw,
        rt.source_order AS table_source_order,
        rtc.row_order,
        rtc.column_order,
        rtc.column_id,
        rtc.cell_text_raw
      FROM zoning.raw_table rt
      LEFT JOIN zoning.raw_table_cell rtc
        ON rtc.raw_table_id = rt.raw_table_id
       AND rtc.is_active
      WHERE (rt.section_id = $1 OR rt.natural_key LIKE $2 || '|table|%')
        AND rt.is_active
      ORDER BY rt.source_order, rt.raw_table_id, rtc.row_order, rtc.column_order
      `,
      [sectionId, section.natural_key],
    ),
  ]);

  const tables = [];
  const tableById = new Map();
  for (const row of tablesResult.rows) {
    if (!tableById.has(row.raw_table_id)) {
      const table = {
        title: row.table_title_raw,
        sourceOrder: row.table_source_order,
        rows: [],
      };
      tableById.set(row.raw_table_id, table);
      tables.push(table);
    }
    if (row.row_order === null) {
      continue;
    }
    const table = tableById.get(row.raw_table_id);
    let tableRow = table.rows.find((candidate) => candidate.sourceOrder === row.row_order);
    if (!tableRow) {
      tableRow = { sourceOrder: row.row_order, cells: [] };
      table.rows.push(tableRow);
    }
    tableRow.cells.push({
      columnId: row.column_id,
      text: row.cell_text_raw,
    });
  }

  return {
    filePath: section.repo_relpath,
    sectionId: section.section_source_id,
    label: section.section_label_raw,
    title: section.section_title_raw,
    citations: toJsonValue(section.citations),
    clauses: clausesResult.rows.map((clause) => ({
      label: clause.clause_label_raw,
      text: clause.clause_text_raw,
      citations: toJsonValue(clause.citations),
      sourceOrder: clause.source_order,
    })),
    tables,
  };
}

function summarizeRows(rows) {
  return rows.map((row) => ({
    row_index: row.row_index,
    section_equivalence_id: row.section_equivalence_id,
    review_decision: row.review_decision,
    db_review_status: row.db_review_status,
    candidate_method: row.candidate_method,
    candidate_topic: row.candidate_topic,
    db_equivalence_type: row.db_equivalence_type,
    title_similarity: row.title_similarity,
    text_similarity: row.text_similarity,
    current_section_label: row.current_section_label,
    current_section_title: row.current_section_title,
    current_document_type: row.current_document_type,
    current_zone_code: row.current_zone_code,
    draft_section_label: row.draft_section_label,
    draft_section_title: row.draft_section_title,
    draft_document_type: row.draft_document_type,
    draft_zone_code: row.draft_zone_code,
    review_batch: row.review_batch,
    reviewer_notes: row.reviewer_notes,
  }));
}

async function sendJson(response, payload) {
  response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function sendGeoJson(response, payload) {
  response.writeHead(200, { "content-type": "application/geo+json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

function mapAddressRow(row) {
  return {
    addressId: toStringValue(row.address_id),
    label: row.label,
    streetNumber: row.street_number,
    streetName: row.street_name,
    unit: row.unit,
    community: row.community,
    pid: row.pid === null || row.pid === undefined ? null : toStringValue(row.pid),
    coordinate: row.lon === null || row.lat === null ? null : {
      lon: Number(row.lon),
      lat: Number(row.lat),
    },
    confidence: row.confidence,
    source: {
      table: "zoning.v_charlottetown_civic_addresses",
      spatialFeatureId: row.spatial_feature_id,
      featureKey: row.feature_key,
      isValid: row.is_valid,
      validationReason: row.validation_reason,
    },
  };
}

function mapZoneRow(row) {
  if (!row) {
    return null;
  }
  return {
    code: compactText(row.zone_code),
    name: compactText(row.zone_name),
    normalizedCode: compactText(row.zone_code_normalized),
    bylawZoneCode: compactText(row.bylaw_zone_code),
    overlapAreaM2: row.overlap_area_m2 === null ? null : Number(row.overlap_area_m2),
    source: {
      table: row.source_table,
      spatialFeatureId: row.spatial_feature_id,
      featureKey: row.feature_key,
      matchMethod: compactText(row.match_method),
      isValid: row.is_valid,
      validationReason: row.validation_reason,
    },
  };
}

function mapZoneSectionRow(row) {
  return {
    sectionId: toStringValue(row.section_source_id),
    label: compactText(row.section_label_raw),
    title: compactText(row.section_title_raw),
    citations: toJsonValue(row.citations),
    filePath: compactText(row.repo_relpath),
  };
}

function zoneChanged(currentZone, draftZone) {
  const currentCode = currentZone?.bylawZoneCode || currentZone?.normalizedCode || currentZone?.code || "";
  const draftCode = draftZone?.bylawZoneCode || draftZone?.normalizedCode || draftZone?.code || "";
  if (!currentCode && !draftCode) {
    return "pending";
  }
  if (!currentCode) {
    return "added";
  }
  if (!draftCode) {
    return "removed";
  }
  return currentCode === draftCode ? "same" : "changed";
}

async function loadZoneSections(zoneCode, sourceKind) {
  if (!zoneCode) {
    return [];
  }
  const sourcePathPattern = sourceKind === "draft"
    ? "data/zoning/charlottetown-draft/%"
    : "data/zoning/charlottetown/%";
  const { rows } = await pool.query(
    `
    SELECT
      s.section_source_id,
      s.section_label_raw,
      s.section_title_raw,
      s.citations,
      sf.repo_relpath
    FROM zoning.section s
    JOIN zoning.source_file sf
      ON sf.source_file_id = s.source_file_id
    WHERE s.is_active
      AND s.document_type = 'zone'
      AND s.zone_code = $1
      AND sf.repo_relpath LIKE $2
    ORDER BY s.source_order, s.section_id
    LIMIT 12
    `,
    [zoneCode, sourcePathPattern],
  );
  return rows.map(mapZoneSectionRow);
}

async function loadZoningComparisonByPid(pid) {
  const parcel = await loadParcelByPid(pid);
  if (!parcel) {
    return null;
  }

  const currentZone = parcel.zones.current;
  const draftZone = parcel.zones.draft;
  const currentLookupCode = currentZone?.bylawZoneCode || currentZone?.normalizedCode || currentZone?.code;
  const draftLookupCode = draftZone?.bylawZoneCode || draftZone?.normalizedCode || draftZone?.code;
  const [currentSections, draftSections] = await Promise.all([
    loadZoneSections(currentLookupCode, "current"),
    loadZoneSections(draftLookupCode, "draft"),
  ]);

  return {
    pid,
    address: parcel.address,
    parcel: parcel.parcel,
    zones: parcel.zones,
    status: zoneChanged(currentZone, draftZone),
    rows: [
      {
        label: "Zone code",
        current: currentZone?.code || null,
        draft: draftZone?.code || null,
        status: zoneChanged(currentZone, draftZone),
      },
      {
        label: "Zone name",
        current: currentZone?.name || currentZone?.code || null,
        draft: draftZone?.name || draftZone?.code || null,
        status: currentZone?.name === draftZone?.name ? "same" : zoneChanged(currentZone, draftZone),
      },
      {
        label: "Current overlap",
        current: currentZone?.overlapAreaM2 ?? null,
        draft: null,
        status: currentZone?.overlapAreaM2 === null || currentZone?.overlapAreaM2 === undefined ? "pending" : "source",
      },
      {
        label: "Draft overlap",
        current: null,
        draft: draftZone?.overlapAreaM2 ?? null,
        status: draftZone?.overlapAreaM2 === null || draftZone?.overlapAreaM2 === undefined ? "pending" : "source",
      },
    ],
    citations: {
      current: currentSections,
      draft: draftSections,
      status: currentSections.length || draftSections.length ? "available" : "pending",
      note: currentSections.length || draftSections.length
        ? "Zone section citations are linked by matched zone code."
        : "Rule-level comparison is pending because no zone-section citations matched the parcel zones.",
    },
    resolution: parcel.resolution,
    source: {
      ...parcel.source,
      currentZoneSections: currentSections.length ? "zoning.section" : null,
      draftZoneSections: draftSections.length ? "zoning.section" : null,
    },
  };
}

async function loadParcelGeoJson(bbox, limit) {
  const params = [limit];
  let bboxFilter = "";
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    bboxFilter = `
      WHERE p.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
        AND ST_Intersects(p.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `;
  }

  const { rows } = await pool.query(
    `
    WITH selected AS (
      SELECT
        p.spatial_feature_id,
        p.feature_key,
        p.attributes,
        p.is_valid,
        p.validation_reason,
        ST_Area(p.geom) AS area_m2,
        p.geom
      FROM zoning.v_charlottetown_parcel_map p
      ${bboxFilter}
      ORDER BY p.spatial_feature_id
      LIMIT $1
    ),
    features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
        'properties', jsonb_build_object(
          'parcelId', feature_key,
          'areaM2', area_m2,
          'attributes', attributes,
          'source', jsonb_build_object(
            'table', 'zoning.v_charlottetown_parcel_map',
            'spatialFeatureId', spatial_feature_id,
            'featureKey', feature_key,
            'isValid', is_valid,
            'validationReason', validation_reason
          )
        )
      ) AS feature
      FROM selected
    )
    SELECT COALESCE(jsonb_agg(feature), '[]'::jsonb) AS features
    FROM features
    `,
    params,
  );

  return {
    type: "FeatureCollection",
    features: rows[0].features,
    metadata: {
      source: "zoning.v_charlottetown_parcel_map",
      bbox,
      limit,
      count: rows[0].features.length,
      geometrySrid: 4326,
      sourceSrid: 2954,
    },
  };
}

async function loadCurrentZoningGeoJson(bbox, limit) {
  const params = [limit];
  let bboxFilter = "";
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    bboxFilter = `
      WHERE z.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
        AND ST_Intersects(z.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `;
  }

  const { rows } = await pool.query(
    `
    WITH selected AS (
      SELECT
        z.spatial_feature_id,
        z.feature_key,
        z."ZONING",
        z.zone_code_raw,
        z.zone_code_normalized,
        z.bylaw_zone_code,
        z.match_method,
        z.attributes,
        z.is_valid,
        z.validation_reason,
        ST_Area(z.geom) AS area_m2,
        z.geom
      FROM zoning.v_charlottetown_current_zoning_boundaries z
      ${bboxFilter}
      ORDER BY z.spatial_feature_id
      LIMIT $1
    ),
    features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
        'properties', jsonb_build_object(
          'zoneCode', COALESCE(bylaw_zone_code, zone_code_normalized, zone_code_raw, "ZONING"),
          'zoneCodeRaw', zone_code_raw,
          'zoneCodeNormalized', zone_code_normalized,
          'bylawZoneCode', bylaw_zone_code,
          'matchMethod', match_method,
          'areaM2', area_m2,
          'attributes', attributes,
          'source', jsonb_build_object(
            'table', 'zoning.v_charlottetown_current_zoning_boundaries',
            'spatialFeatureId', spatial_feature_id,
            'featureKey', feature_key,
            'isValid', is_valid,
            'validationReason', validation_reason
          )
        )
      ) AS feature
      FROM selected
    )
    SELECT COALESCE(jsonb_agg(feature), '[]'::jsonb) AS features
    FROM features
    `,
    params,
  );

  return {
    type: "FeatureCollection",
    features: rows[0].features,
    metadata: {
      source: "zoning.v_charlottetown_current_zoning_boundaries",
      bbox,
      limit,
      count: rows[0].features.length,
      geometrySrid: 4326,
      sourceSrid: 2954,
    },
  };
}

async function loadDraftZoningGeoJson(bbox, limit) {
  const params = [limit];
  let bboxFilter = "";
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    bboxFilter = `
      WHERE z.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
        AND ST_Intersects(z.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `;
  }

  const { rows } = await pool.query(
    `
    WITH selected AS (
      SELECT
        z.spatial_feature_id,
        z.feature_key,
        z.zone_code,
        z.zone_name,
        z.zone_code_raw,
        z.zone_code_normalized,
        z.bylaw_zone_code,
        z.match_method,
        z.attributes,
        z.is_valid,
        z.validation_reason,
        ST_Area(z.geom) AS area_m2,
        z.geom
      FROM zoning.v_charlottetown_draft_zoning_boundaries z
      ${bboxFilter}
      ORDER BY z.spatial_feature_id
      LIMIT $1
    ),
    features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
        'properties', jsonb_build_object(
          'zoneCode', COALESCE(bylaw_zone_code, zone_code_normalized, zone_code_raw, zone_code),
          'zoneName', zone_name,
          'zoneCodeRaw', zone_code_raw,
          'zoneCodeNormalized', zone_code_normalized,
          'bylawZoneCode', bylaw_zone_code,
          'matchMethod', match_method,
          'areaM2', area_m2,
          'attributes', attributes,
          'source', jsonb_build_object(
            'table', 'zoning.v_charlottetown_draft_zoning_boundaries',
            'spatialFeatureId', spatial_feature_id,
            'featureKey', feature_key,
            'isValid', is_valid,
            'validationReason', validation_reason
          )
        )
      ) AS feature
      FROM selected
    )
    SELECT COALESCE(jsonb_agg(feature), '[]'::jsonb) AS features
    FROM features
    `,
    params,
  );

  return {
    type: "FeatureCollection",
    features: rows[0].features,
    metadata: {
      source: "zoning.v_charlottetown_draft_zoning_boundaries",
      bbox,
      limit,
      count: rows[0].features.length,
      geometrySrid: 4326,
      sourceSrid: 2954,
    },
  };
}

async function searchAddresses(query, limit) {
  const normalizedQuery = query.trim();
  if (normalizedQuery.length < 2) {
    return [];
  }

  const { rows } = await pool.query(
    `
    WITH address_rows AS (
      SELECT
        spatial_feature_id,
        feature_key,
        attributes,
        is_valid,
        validation_reason,
        geom,
        NULLIF(trim(attributes ->> 'APT_NO'), '') AS unit,
        NULLIF(trim(attributes ->> 'COMM_NM'), '') AS community,
        NULLIF(trim(attributes ->> 'STREET_NM'), '') AS street_name,
        NULLIF(trim(attributes ->> 'STREET_NO'), '') AS street_number,
        NULLIF(trim(attributes ->> 'PID'), '') AS pid
      FROM zoning.v_charlottetown_civic_addresses
    ),
    labelled AS (
      SELECT
        *,
        concat_ws(
          ', ',
          concat_ws(
            ' ',
            street_number,
            street_name,
            CASE WHEN unit IS NOT NULL THEN 'Unit ' || unit END
          ),
          community,
          CASE WHEN pid IS NOT NULL THEN 'PID ' || pid END
        ) AS label
      FROM address_rows
    )
    SELECT
      spatial_feature_id,
      feature_key,
      is_valid,
      validation_reason,
      feature_key AS address_id,
      label,
      street_number,
      street_name,
      unit,
      community,
      pid,
      ST_X(ST_Transform(geom, 4326)) AS lon,
      ST_Y(ST_Transform(geom, 4326)) AS lat,
      CASE
        WHEN label ILIKE $1 || '%' THEN 'high'
        WHEN label ILIKE '%' || $1 || '%' THEN 'medium'
        ELSE 'low'
      END AS confidence
    FROM labelled
    WHERE label ILIKE '%' || $1 || '%'
       OR pid = $1
    ORDER BY
      CASE
        WHEN pid = $1 THEN 0
        WHEN label ILIKE $1 || '%' THEN 1
        WHEN label ILIKE '%' || $1 || '%' THEN 2
        ELSE 3
      END,
      label,
      spatial_feature_id
    LIMIT $2
    `,
    [normalizedQuery, limit],
  );
  return rows.map(mapAddressRow);
}

async function loadParcelByPid(pid) {
  const { rows } = await pool.query(
    `
    WITH selected_address AS (
      SELECT
        spatial_feature_id,
        feature_key,
        attributes,
        is_valid,
        validation_reason,
        geom,
        NULLIF(trim(attributes ->> 'APT_NO'), '') AS unit,
        NULLIF(trim(attributes ->> 'COMM_NM'), '') AS community,
        NULLIF(trim(attributes ->> 'STREET_NM'), '') AS street_name,
        NULLIF(trim(attributes ->> 'STREET_NO'), '') AS street_number,
        NULLIF(trim(attributes ->> 'PID'), '') AS pid
      FROM zoning.v_charlottetown_civic_addresses
      WHERE NULLIF(trim(attributes ->> 'PID'), '') = $1
         OR NULLIF(trim(attributes ->> 'pid2'), '') = $1
      ORDER BY spatial_feature_id
      LIMIT 1
    ),
    selected_parcel AS (
      SELECT
        p.spatial_feature_id,
        p.feature_key,
        p.attributes,
        p.is_valid,
        p.validation_reason,
        p.geom
      FROM selected_address a
      JOIN zoning.v_charlottetown_parcel_map p
        ON ST_Covers(p.geom, a.geom)
      ORDER BY ST_Area(p.geom), p.spatial_feature_id
      LIMIT 1
    ),
    current_zone AS (
      SELECT
        'zoning.v_charlottetown_current_zoning_boundaries' AS source_table,
        z.spatial_feature_id,
        z.feature_key,
        COALESCE(z.bylaw_zone_code, z.zone_code_normalized, z.zone_code_raw, z."ZONING") AS zone_code,
        NULL::text AS zone_name,
        z.zone_code_normalized,
        z.bylaw_zone_code,
        z.match_method,
        z.is_valid,
        z.validation_reason,
        ST_Area(ST_Intersection(z.geom, p.geom)) AS overlap_area_m2
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_current_zoning_boundaries z
        ON ST_Intersects(z.geom, p.geom)
      ORDER BY overlap_area_m2 DESC NULLS LAST, z.spatial_feature_id
      LIMIT 1
    ),
    draft_zone AS (
      SELECT
        'zoning.v_charlottetown_draft_zoning_boundaries' AS source_table,
        z.spatial_feature_id,
        z.feature_key,
        COALESCE(z.bylaw_zone_code, z.zone_code_normalized, z.zone_code_raw, z.zone_code) AS zone_code,
        z.zone_name,
        z.zone_code_normalized,
        z.bylaw_zone_code,
        z.match_method,
        z.is_valid,
        z.validation_reason,
        ST_Area(ST_Intersection(z.geom, p.geom)) AS overlap_area_m2
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_draft_zoning_boundaries z
        ON ST_Intersects(z.geom, p.geom)
      ORDER BY overlap_area_m2 DESC NULLS LAST, z.spatial_feature_id
      LIMIT 1
    )
    SELECT
      jsonb_build_object(
        'address', (
          SELECT jsonb_build_object(
            'spatial_feature_id', spatial_feature_id,
            'feature_key', feature_key,
            'address_id', feature_key,
            'label', concat_ws(
              ', ',
              concat_ws(
                ' ',
                street_number,
                street_name,
                CASE WHEN unit IS NOT NULL THEN 'Unit ' || unit END
              ),
              community,
              CASE WHEN pid IS NOT NULL THEN 'PID ' || pid END
            ),
            'street_number', street_number,
            'street_name', street_name,
            'unit', unit,
            'community', community,
            'pid', pid,
            'lon', ST_X(ST_Transform(geom, 4326)),
            'lat', ST_Y(ST_Transform(geom, 4326)),
            'is_valid', is_valid,
            'validation_reason', validation_reason
          )
          FROM selected_address
        ),
        'parcel', (
          SELECT jsonb_build_object(
            'spatial_feature_id', spatial_feature_id,
            'feature_key', feature_key,
            'attributes', attributes,
            'area_m2', ST_Area(geom),
            'is_valid', is_valid,
            'validation_reason', validation_reason,
            'centroid', jsonb_build_object(
              'lon', ST_X(ST_Transform(ST_Centroid(geom), 4326)),
              'lat', ST_Y(ST_Transform(ST_Centroid(geom), 4326))
            ),
            'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb
          )
          FROM selected_parcel
        ),
        'current_zone', (SELECT to_jsonb(current_zone) FROM current_zone),
        'draft_zone', (SELECT to_jsonb(draft_zone) FROM draft_zone)
      ) AS payload
    `,
    [pid],
  );

  const payload = rows[0]?.payload;
  if (!payload?.address) {
    return null;
  }

  return {
    pid,
    address: mapAddressRow({ ...payload.address, confidence: "pid" }),
    parcel: payload.parcel
      ? {
          parcelId: toStringValue(payload.parcel.feature_key),
          areaM2: Number(payload.parcel.area_m2),
          centroid: payload.parcel.centroid,
          geometry: payload.parcel.geometry,
          attributes: payload.parcel.attributes,
          source: {
            table: "zoning.v_charlottetown_parcel_map",
            spatialFeatureId: payload.parcel.spatial_feature_id,
            featureKey: payload.parcel.feature_key,
            isValid: payload.parcel.is_valid,
            validationReason: payload.parcel.validation_reason,
          },
        }
      : null,
    zones: {
      current: mapZoneRow(payload.current_zone),
      draft: mapZoneRow(payload.draft_zone),
    },
    resolution: {
      method: payload.parcel ? "address_pid_to_point_in_parcel" : "address_pid_only",
      parcelPidNative: false,
      status: payload.parcel ? "resolved" : "address_found_no_containing_parcel",
    },
    source: {
      freshness: "database",
      addressTable: "zoning.v_charlottetown_civic_addresses",
      parcelTable: "zoning.v_charlottetown_parcel_map",
      currentZoningTable: "zoning.v_charlottetown_current_zoning_boundaries",
      draftZoningTable: "zoning.v_charlottetown_draft_zoning_boundaries",
    },
  };
}

async function loadParcelAtPoint(lon, lat) {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
    const error = new Error("lon and lat must be valid numbers.");
    error.statusCode = 400;
    throw error;
  }
  if (lon < -180 || lon > 180 || lat < -90 || lat > 90) {
    const error = new Error("lon and lat must be WGS84 longitude/latitude values.");
    error.statusCode = 400;
    throw error;
  }

  const { rows } = await pool.query(
    `
    WITH click_point AS (
      SELECT ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 2954) AS geom
    ),
    selected_parcel AS (
      SELECT
        p.spatial_feature_id,
        p.feature_key,
        p.attributes,
        p.is_valid,
        p.validation_reason,
        p.geom
      FROM zoning.v_charlottetown_parcel_map p
      JOIN click_point c
        ON ST_Covers(p.geom, c.geom)
      ORDER BY ST_Area(p.geom), p.spatial_feature_id
      LIMIT 1
    ),
    selected_address AS (
      SELECT
        a.spatial_feature_id,
        a.feature_key,
        a.attributes,
        a.is_valid,
        a.validation_reason,
        a.geom,
        NULLIF(trim(a.attributes ->> 'APT_NO'), '') AS unit,
        NULLIF(trim(a.attributes ->> 'COMM_NM'), '') AS community,
        NULLIF(trim(a.attributes ->> 'STREET_NM'), '') AS street_name,
        NULLIF(trim(a.attributes ->> 'STREET_NO'), '') AS street_number,
        NULLIF(trim(a.attributes ->> 'PID'), '') AS pid
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_civic_addresses a
        ON ST_Covers(p.geom, a.geom)
      WHERE NULLIF(trim(a.attributes ->> 'PID'), '') IS NOT NULL
      ORDER BY
        ST_Distance(a.geom, (SELECT geom FROM click_point)),
        a.spatial_feature_id
      LIMIT 1
    )
    SELECT jsonb_build_object(
      'address', (
        SELECT jsonb_build_object(
          'spatial_feature_id', spatial_feature_id,
          'feature_key', feature_key,
          'address_id', feature_key,
          'label', concat_ws(
            ', ',
            concat_ws(
              ' ',
              street_number,
              street_name,
              CASE WHEN unit IS NOT NULL THEN 'Unit ' || unit END
            ),
            community,
            CASE WHEN pid IS NOT NULL THEN 'PID ' || pid END
          ),
          'street_number', street_number,
          'street_name', street_name,
          'unit', unit,
          'community', community,
          'pid', pid,
          'lon', ST_X(ST_Transform(geom, 4326)),
          'lat', ST_Y(ST_Transform(geom, 4326)),
          'is_valid', is_valid,
          'validation_reason', validation_reason
        )
        FROM selected_address
      ),
      'parcel', (
        SELECT jsonb_build_object(
          'spatial_feature_id', spatial_feature_id,
          'feature_key', feature_key,
          'attributes', attributes,
          'area_m2', ST_Area(geom),
          'is_valid', is_valid,
          'validation_reason', validation_reason,
          'centroid', jsonb_build_object(
            'lon', ST_X(ST_Transform(ST_Centroid(geom), 4326)),
            'lat', ST_Y(ST_Transform(ST_Centroid(geom), 4326))
          ),
          'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb
        )
        FROM selected_parcel
      )
    ) AS payload
    `,
    [lon, lat],
  );

  const payload = rows[0]?.payload;
  if (!payload?.parcel) {
    return null;
  }

  return {
    coordinate: { lon, lat },
    address: payload.address ? mapAddressRow({ ...payload.address, confidence: "parcel_click" }) : null,
    parcel: {
      parcelId: toStringValue(payload.parcel.feature_key),
      areaM2: Number(payload.parcel.area_m2),
      centroid: payload.parcel.centroid,
      geometry: payload.parcel.geometry,
      attributes: payload.parcel.attributes,
      source: {
        table: "zoning.v_charlottetown_parcel_map",
        spatialFeatureId: payload.parcel.spatial_feature_id,
        featureKey: payload.parcel.feature_key,
        isValid: payload.parcel.is_valid,
        validationReason: payload.parcel.validation_reason,
      },
    },
    resolution: {
      method: payload.address ? "parcel_click_to_address_pid" : "parcel_click_no_address_pid",
      parcelPidNative: false,
      status: payload.address?.pid ? "resolved" : "parcel_found_no_address_pid",
    },
    source: {
      freshness: "database",
      addressTable: "zoning.v_charlottetown_civic_addresses",
      parcelTable: "zoning.v_charlottetown_parcel_map",
    },
  };
}

const routeEntrypoints = new Map([
  ["/", { file: "/ui_kits/parcel-lookup/index.html", baseHref: "/ui_kits/parcel-lookup/" }],
  ["/parcel-lookup", { file: "/ui_kits/parcel-lookup/index.html", baseHref: "/ui_kits/parcel-lookup/" }],
  ["/parcel-lookup/", { file: "/ui_kits/parcel-lookup/index.html", baseHref: "/ui_kits/parcel-lookup/" }],
  ["/map-explorer", { file: "/ui_kits/map-explorer/index.html", baseHref: "/ui_kits/map-explorer/" }],
  ["/map-explorer/", { file: "/ui_kits/map-explorer/index.html", baseHref: "/ui_kits/map-explorer/" }],
  ["/city-view", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/city-view/", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/map", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/map/", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/zoning-comparison", { file: "/ui_kits/zoning-comparison/index.html", baseHref: "/ui_kits/zoning-comparison/" }],
  ["/zoning-comparison/", { file: "/ui_kits/zoning-comparison/index.html", baseHref: "/ui_kits/zoning-comparison/" }],
]);

function htmlWithBase(body, baseHref) {
  if (!baseHref || !body.includes("<head>")) {
    return body;
  }
  return body.replace("<head>", `<head>\n<base href="${baseHref}">`);
}

async function serveStatic(response, requestPath) {
  const routeEntrypoint = routeEntrypoints.get(requestPath);
  const safePath = routeEntrypoint?.file || (requestPath === "/" ? "/index.html" : requestPath);
  const absolute = path.resolve(publicDir, `.${safePath}`);
  if (!absolute.startsWith(publicDir)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  const ext = path.extname(absolute);
  const contentTypes = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
  };

  try {
    let body = await readFile(absolute);
    if (routeEntrypoint?.baseHref && ext === ".html") {
      body = htmlWithBase(body.toString("utf8"), routeEntrypoint.baseHref);
    }
    response.writeHead(200, { "content-type": contentTypes[ext] || "application/octet-stream" });
    response.end(body);
  } catch {
    response.writeHead(404);
    response.end("Not found");
  }
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host}`);
    if (url.pathname === "/api/section-equivalence") {
      const rows = await loadReviewRows();
      await sendJson(response, { source: "zoning.section_equivalence", rows: summarizeRows(rows) });
      return;
    }

    if (url.pathname === "/api/addresses") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const query = url.searchParams.get("q") || "";
      const limit = normalizeLimit(url.searchParams.get("limit"), 10, 25);
      const rows = await searchAddresses(query, limit);
      await sendJson(response, {
        source: "zoning.v_charlottetown_civic_addresses",
        query: query.trim(),
        rows,
      });
      return;
    }

    if (url.pathname === "/api/parcels.geojson") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const bbox = parseBbox(url.searchParams.get("bbox"));
      const limit = normalizeLimit(url.searchParams.get("limit"), 1000, 5000);
      await sendGeoJson(response, await loadParcelGeoJson(bbox, limit));
      return;
    }

    if (url.pathname === "/api/zoning/current.geojson") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const bbox = parseBbox(url.searchParams.get("bbox"));
      const limit = normalizeLimit(url.searchParams.get("limit"), 1000, 5000);
      await sendGeoJson(response, await loadCurrentZoningGeoJson(bbox, limit));
      return;
    }

    if (url.pathname === "/api/zoning/draft.geojson") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const bbox = parseBbox(url.searchParams.get("bbox"));
      const limit = normalizeLimit(url.searchParams.get("limit"), 1000, 5000);
      await sendGeoJson(response, await loadDraftZoningGeoJson(bbox, limit));
      return;
    }

    if (url.pathname === "/api/parcels/point") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const lon = Number(url.searchParams.get("lon"));
      const lat = Number(url.searchParams.get("lat"));
      const parcel = await loadParcelAtPoint(lon, lat);
      if (!parcel) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "No parcel found at point.", lon, lat }));
        return;
      }
      await sendJson(response, parcel);
      return;
    }

    const comparisonMatch = url.pathname.match(/^\/api\/zoning-comparison\/([^/]+)$/);
    if (comparisonMatch) {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const pid = decodeURIComponent(comparisonMatch[1]).trim();
      const comparison = await loadZoningComparisonByPid(pid);
      if (!comparison) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "Parcel PID not found.", pid }));
        return;
      }
      await sendJson(response, comparison);
      return;
    }

    const parcelMatch = url.pathname.match(/^\/api\/parcels\/([^/]+)$/);
    if (parcelMatch) {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const pid = decodeURIComponent(parcelMatch[1]).trim();
      const parcel = await loadParcelByPid(pid);
      if (!parcel) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "Parcel PID not found.", pid }));
        return;
      }
      await sendJson(response, parcel);
      return;
    }

    const decisionMatch = url.pathname.match(/^\/api\/section-equivalence\/(\d+)\/decision$/);
    if (decisionMatch && request.method === "POST") {
      const sectionEquivalenceId = Number(decisionMatch[1]);
      const body = await readRequestJson(request);
      await updateReviewDecision(sectionEquivalenceId, body.decision);
      const rows = await loadReviewRows();
      const row = rows.find(
        (candidate) => Number(candidate.section_equivalence_id) === sectionEquivalenceId,
      );
      if (!row) {
        response.writeHead(404);
        response.end("Review row not found");
        return;
      }
      const [currentSection, draftSection] = await Promise.all([
        loadSection(row.current_section_id),
        loadSection(row.draft_section_id),
      ]);
      await sendJson(response, {
        row,
        rows: summarizeRows(rows),
        currentSection,
        draftSection,
      });
      return;
    }

    if (url.pathname.startsWith("/api/section-equivalence/")) {
      const rowIndex = Number(url.pathname.split("/").at(-1));
      const rows = await loadReviewRows();
      const row = rows.find((candidate) => candidate.row_index === rowIndex);
      if (!row) {
        response.writeHead(404);
        response.end("Review row not found");
        return;
      }
      const [currentSection, draftSection] = await Promise.all([
        loadSection(row.current_section_id),
        loadSection(row.draft_section_id),
      ]);
      await sendJson(response, { row, currentSection, draftSection });
      return;
    }

    await serveStatic(response, url.pathname);
  } catch (error) {
    response.writeHead(error.statusCode || 500, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ error: error.message }));
  }
});

server.listen(port, host, () => {
  console.log(`mdopendata web listening on http://${host}:${port}`);
});
