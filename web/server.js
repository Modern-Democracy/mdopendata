import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import pg from "pg";

const { Pool } = pg;
const execFileAsync = promisify(execFile);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = process.env.REPO_ROOT || path.resolve(__dirname, "..");
const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT || 3000);
const defaultGdalTranslatePath = process.platform === "win32"
  ? "C:\\Program Files\\GDAL\\gdal_translate.exe"
  : "gdal_translate";
const gdalTranslatePath = process.env.GDAL_TRANSLATE_PATH || defaultGdalTranslatePath;
const terrainDemPath = path.join(
  repoRoot,
  "data",
  "spatial",
  "charlottetown",
  "lidar-terrain-dem",
  "charlottetown-dem-epsg2961-1m.tif",
);
const terrainQaSummaryPath = path.join(
  repoRoot,
  "data",
  "spatial",
  "charlottetown",
  "lidar-terrain-dem",
  "charlottetown-dem-epsg2961-1m.qa.summary.json",
);
const councilMeetingPath = path.join(
  repoRoot,
  "data",
  "council-meetings",
  "charlottetown",
  "2026-05-12-regular-council",
  "meeting.json",
);
const councilMeetingAgendaPath = path.join(
  repoRoot,
  "data",
  "council-meetings",
  "charlottetown",
  "2026-05-12-regular-council",
  "agenda.json",
);
const councilMeetingTocPath = path.join(
  repoRoot,
  "data",
  "council-meetings",
  "charlottetown",
  "2026-05-12-regular-council",
  "toc.json",
);
const councilMeetingPageImageRoot = path.join(
  repoRoot,
  "data",
  "council-meetings",
  "charlottetown",
  "2026-05-12-regular-council",
  "page-images",
);

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

function normalizeComparisonKey(value) {
  return toStringValue(value)
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

let knownZoneCodesCache = null;

async function loadKnownZoneCodes() {
  if (knownZoneCodesCache) {
    return knownZoneCodesCache;
  }
  const { rows } = await pool.query(`
    SELECT zone_code
    FROM zoning.section
    WHERE is_active
      AND document_type = 'zone'
      AND zone_code IS NOT NULL
    GROUP BY zone_code
    ORDER BY length(zone_code) DESC, zone_code
  `);
  knownZoneCodesCache = rows.map((row) => row.zone_code);
  return knownZoneCodesCache;
}

function extractReferencedZoneCodes(text, knownZoneCodes, currentZoneCode) {
  const source = toStringValue(text).toUpperCase();
  return knownZoneCodes
    .filter((zoneCode) => zoneCode !== currentZoneCode)
    .filter((zoneCode) => {
      const escaped = zoneCode.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`\\b${escaped}\\s+ZONE\\b|\\(${escaped}\\)\\s+ZONE\\b`, "i").test(source);
    });
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

function normalizeZoneFilter(value) {
  const text = compactText(value);
  return text ? text.toUpperCase() : null;
}

function normalizeDetail(value) {
  return value === "overview" ? "overview" : "detail";
}

function filteredZoneExpression(alias) {
  return `upper(COALESCE(${alias}.bylaw_zone_code, ${alias}.zone_code_normalized, ${alias}.zone_code_raw))`;
}

function geometryExpression(alias, detail, tolerance = 3) {
  return detail === "overview"
    ? `ST_SimplifyPreserveTopology(${alias}.geom, ${tolerance})`
    : `${alias}.geom`;
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
    databaseSectionId: row.section_id === null || row.section_id === undefined ? null : Number(row.section_id),
    label: compactText(row.section_label_raw),
    title: compactText(row.section_title_raw),
    citations: toJsonValue(row.citations),
    filePath: compactText(row.repo_relpath),
    clauses: row.clauses || [],
    tables: row.tables || [],
  };
}

async function loadCouncilMeeting() {
  const [payload, agenda, toc] = await Promise.all([
    readFile(councilMeetingPath, "utf8").then(JSON.parse),
    readFile(councilMeetingAgendaPath, "utf8").then(JSON.parse),
    readFile(councilMeetingTocPath, "utf8").then(JSON.parse),
  ]);
  return {
    source: "data/council-meetings/charlottetown/2026-05-12-regular-council/meeting.json",
    agendaSource: "data/council-meetings/charlottetown/2026-05-12-regular-council/agenda.json",
    tocSource: "data/council-meetings/charlottetown/2026-05-12-regular-council/toc.json",
    meeting: payload.meeting,
    sourceDocuments: payload.source_documents,
    agendaDocuments: agenda.agenda_documents,
    packageDocuments: toc.documents,
    documentStructureStandards: toc.document_structure_standards,
    pageReproductionOptions: toc.page_reproduction_options,
    agendaSections: payload.agenda_sections,
    committeeReports: payload.committee_reports,
    resolutions: payload.resolutions,
    bylawReadings: payload.bylaw_readings,
    planningItems: payload.planning_items,
    audienceWorkflows: payload.audience_workflows,
    reviewFlags: payload.review_flags,
  };
}

async function loadCouncilMeetingSourcePage(documentId, pageNumber) {
  if (!["agenda", "package"].includes(documentId)) {
    const error = new Error("documentId must be agenda or package.");
    error.statusCode = 400;
    throw error;
  }
  const page = Number(pageNumber);
  if (!Number.isInteger(page) || page < 1 || page > 999) {
    const error = new Error("page must be a positive integer.");
    error.statusCode = 400;
    throw error;
  }
  const pagePath = path.join(
    repoRoot,
    "data",
    "council-meetings",
    "charlottetown",
    "2026-05-12-regular-council",
    "raw-pages",
    `${documentId}-page-${String(page).padStart(3, "0")}.txt`,
  );
  const absolute = path.resolve(pagePath);
  const rawRoot = path.resolve(repoRoot, "data", "council-meetings", "charlottetown", "2026-05-12-regular-council", "raw-pages");
  if (!absolute.startsWith(rawRoot)) {
    const error = new Error("Invalid source page path.");
    error.statusCode = 400;
    throw error;
  }
  return {
    documentId,
    page,
    text: await readFile(absolute, "utf8"),
  };
}

async function loadCouncilMeetingPageImage(documentId, pageNumber) {
  if (documentId !== "package") {
    const error = new Error("documentId must be package.");
    error.statusCode = 400;
    throw error;
  }
  const page = Number(pageNumber);
  if (!Number.isInteger(page) || page < 1 || page > 999) {
    const error = new Error("page must be a positive integer.");
    error.statusCode = 400;
    throw error;
  }
  const imagePath = path.join(councilMeetingPageImageRoot, `${documentId}-page-${String(page).padStart(3, "0")}.png`);
  const absolute = path.resolve(imagePath);
  const imageRoot = path.resolve(councilMeetingPageImageRoot);
  if (!absolute.startsWith(imageRoot)) {
    const error = new Error("Invalid page image path.");
    error.statusCode = 400;
    throw error;
  }
  return readFile(absolute);
}

async function loadCouncilMeetingRaw() {
  return JSON.parse(await readFile(councilMeetingPath, "utf8"));
}

function councilMeetingItems(payload) {
  return [
    ...(payload?.agenda_sections || []),
    ...(payload?.committee_reports || []),
    ...(payload?.resolutions || []),
    ...(payload?.bylaw_readings || []),
    ...(payload?.planning_items || []),
  ];
}

async function loadCouncilMeetingItem(itemId) {
  const payload = await loadCouncilMeetingRaw();
  const item = councilMeetingItems(payload).find((candidate) => (
    candidate.item_id === itemId
    || candidate.planning_item_id === itemId
    || candidate.agenda_section_id === itemId
    || candidate.committee_report_id === itemId
  ));
  if (!item) {
    return null;
  }
  return { meeting: payload.meeting, item };
}

function extractCouncilItemPids(item) {
  const ordered = [];
  const add = (pid) => {
    const normalized = compactText(pid).replace(/\D/g, "");
    if (normalized && !ordered.includes(normalized)) {
      ordered.push(normalized);
    }
  };
  for (const reference of item?.property_references || []) {
    for (const pid of reference.pids || []) {
      add(pid);
    }
  }
  const text = [
    item?.title,
    item?.public_summary,
    item?.decision_requested,
    ...(item?.citations || [])
      .filter((citation) => citation.source_document_id === "package")
      .map((citation) => citation.text_excerpt || ""),
  ].join("\n");
  for (const match of text.matchAll(/\bPID\s*#?'?s?\s*[:#]?\s*((?:\d{5,8})(?:\s*(?:,|and|&)\s*\d{5,8}){0,12})/gi)) {
    for (const pid of match[1].match(/\d{5,8}/g) || []) {
      add(pid);
    }
  }
  return ordered;
}

async function loadCouncilFallbackParcelsByZones(fromZoneCode, toZoneCode, pids) {
  if (!fromZoneCode || !toZoneCode || !pids.length) {
    return [];
  }
  const { rows } = await pool.query(
    `
    SELECT
      p.spatial_feature_id,
      p.feature_key,
      p.attributes,
      p.is_valid,
      p.validation_reason,
      ST_Area(p.geom) AS area_m2,
      ST_AsGeoJSON(ST_Transform(p.geom, 4326))::jsonb AS geometry,
      jsonb_build_object(
        'lon', ST_X(ST_Transform(ST_Centroid(p.geom), 4326)),
        'lat', ST_Y(ST_Transform(ST_Centroid(p.geom), 4326))
      ) AS centroid,
      za.current_zone_code,
      za.draft_zone_code
    FROM zoning.v_charlottetown_parcel_zone_assignment za
    JOIN zoning.v_charlottetown_parcel_map p
      ON p.spatial_feature_id = za.parcel_spatial_feature_id
    WHERE za.current_zone_code = $1
      AND za.draft_zone_code = $2
    ORDER BY ST_Area(p.geom) DESC, p.spatial_feature_id
    LIMIT $3
    `,
    [fromZoneCode, toZoneCode, pids.length],
  );
  return rows.map((row, index) => {
    const pid = pids[index];
    return {
      pid,
      selected: true,
      address: {
        label: `PID ${pid}`,
        pid,
        coordinate: row.centroid,
      },
      parcel: {
        parcelId: toStringValue(row.feature_key),
        areaM2: Number(row.area_m2),
        centroid: row.centroid,
        geometry: row.geometry,
        attributes: row.attributes,
        source: {
          table: "zoning.v_charlottetown_parcel_map",
          spatialFeatureId: row.spatial_feature_id,
          featureKey: row.feature_key,
          isValid: row.is_valid,
          validationReason: row.validation_reason,
          fallback: "zone_transition_candidate",
        },
      },
      zones: {
        current: { code: row.current_zone_code, bylawZoneCode: row.current_zone_code },
        draft: { code: row.draft_zone_code, bylawZoneCode: row.draft_zone_code },
      },
      resolution: {
        status: "fallback_zone_transition_candidate",
        method: "current_to_draft_zone_transition_without_pid_join",
      },
    };
  });
}

function councilZoneFromCode(code, sections) {
  const title = compactText(sections?.[0]?.title);
  return {
    code: compactText(code),
    name: zoneNameFromPartTitle(title, code) || compactText(code),
    bylawZoneCode: compactText(code),
    source: {
      table: "zoning.section",
      sourceKind: "current",
    },
  };
}

async function loadCurrentZoneComparisonByCodes(fromZoneCode, toZoneCode, itemContext = {}) {
  const [fromSectionsRaw, toSectionsRaw] = await Promise.all([
    loadZoneSections(fromZoneCode, "current"),
    loadZoneSections(toZoneCode, "current"),
  ]);
  const [fromSections, toSections] = await Promise.all([
    attachReferencedSections(fromSectionsRaw, fromZoneCode, "current"),
    attachReferencedSections(toSectionsRaw, toZoneCode, "current"),
  ]);
  const [fromStructured, toStructured] = await Promise.all([
    loadZoneStructuredFacts(fromZoneCode, "current"),
    loadZoneStructuredFacts(toZoneCode, "current"),
  ]);
  const fromZone = councilZoneFromCode(fromZoneCode, fromSections);
  const toZone = councilZoneFromCode(toZoneCode, toSections);
  return {
    itemId: itemContext.itemId || null,
    title: itemContext.title || "Council rezoning comparison",
    pid: itemContext.primaryPid || null,
    address: itemContext.address || null,
    zones: {
      current: fromZone,
      draft: toZone,
      from: fromZone,
      to: toZone,
    },
    status: fromZoneCode === toZoneCode ? "same" : "changed",
    rows: [
      { label: "Zone code", current: fromZone.code || null, draft: toZone.code || null, status: fromZone.code === toZone.code ? "same" : "changed" },
      { label: "Zone name", current: fromZone.name || null, draft: toZone.name || null, status: fromZone.name === toZone.name ? "same" : "changed" },
    ],
    citations: {
      current: fromSections,
      draft: toSections,
      from: fromSections,
      to: toSections,
      status: fromSections.length || toSections.length ? "available" : "pending",
      note: "Current bylaw zone entries compared from the council meeting rezoning target zones.",
    },
    structuredData: buildStructuredComparison(fromStructured, toStructured),
    resolution: { status: "current_bylaw_zone_to_zone", method: "meeting_json_from_to_zone" },
    source: {
      meeting: "data/council-meetings/charlottetown/2026-05-12-regular-council/meeting.json",
      currentZoneSections: "zoning.section",
      currentStructuredFacts: "zoning.structured_fact",
    },
  };
}

async function loadCouncilMeetingItemParcels(itemId) {
  const context = await loadCouncilMeetingItem(itemId);
  if (!context) return null;
  const pids = extractCouncilItemPids(context.item);
  let rows = await Promise.all(pids.map(async (pid) => {
    const parcel = await loadParcelByPid(pid);
    return {
      pid,
      selected: true,
      address: parcel?.address || {
        label: `PID ${pid}`,
        pid,
        coordinate: null,
      },
      parcel: parcel?.parcel || null,
      zones: parcel?.zones || null,
      resolution: parcel?.resolution || { status: "not_found" },
    };
  }));
  const missingIndexes = rows
    .map((row, index) => (row.parcel ? null : index))
    .filter((index) => index !== null);
  if (missingIndexes.length) {
    const amendment = context.item.zoning_amendment || {};
    const fallbacks = await loadCouncilFallbackParcelsByZones(
      amendment.from_zone,
      amendment.to_zone,
      missingIndexes.map((index) => pids[index]),
    );
    for (let index = 0; index < fallbacks.length; index += 1) {
      rows[missingIndexes[index]] = fallbacks[index];
    }
  }
  return {
    itemId,
    title: context.item.title || context.item.title_raw || itemId,
    pids,
    parcels: rows,
    source: {
      meeting: "data/council-meetings/charlottetown/2026-05-12-regular-council/meeting.json",
      parcelTable: "zoning.v_charlottetown_parcel_map",
      addressTable: "zoning.v_charlottetown_civic_addresses",
    },
  };
}

async function loadCouncilMeetingItemComparison(itemId) {
  const context = await loadCouncilMeetingItem(itemId);
  if (!context) return null;
  const amendment = context.item.zoning_amendment || {};
  const pids = extractCouncilItemPids(context.item);
  const primaryParcel = pids[0] ? await loadParcelByPid(pids[0]) : null;
  return loadCurrentZoneComparisonByCodes(amendment.from_zone, amendment.to_zone, {
    itemId,
    title: context.item.title || context.item.title_raw || itemId,
    primaryPid: pids[0] || null,
    address: primaryParcel?.address || null,
  });
}

async function loadCouncilMeetingItemRestrictionStack(itemId) {
  const context = await loadCouncilMeetingItem(itemId);
  if (!context) return null;
  const pids = extractCouncilItemPids(context.item);
  const parcelPayload = await loadCouncilMeetingItemParcels(itemId);
  const resolved = parcelPayload?.parcels?.find((row) => row.resolution?.status === "resolved");
  const primaryPid = resolved?.pid || pids[0];
  if (!primaryPid) return null;
  const comparison = await loadCouncilMeetingItemComparison(itemId);
  const baseStack = await loadParcelRestrictionStack(primaryPid, comparison);
  if (!baseStack || !comparison) return null;
  const fromTypes = categorizedRestrictionRows(comparison, "current");
  const toTypes = categorizedRestrictionRows(comparison, "draft");
  const fromZone = comparison.zones.from;
  const toZone = comparison.zones.to;
  return {
    ...baseStack,
    itemId,
    pids,
    zones: {
      current: fromZone,
      draft: toZone,
      from: fromZone,
      to: toZone,
    },
    regulationTypes: baseStack.regulationTypes.map((type) => ({
      ...type,
      availableIn: type.availableIn.map((side) => (side === "current" ? "from" : side === "draft" ? "to" : side)),
    })),
    metadata: {
      ...baseStack.metadata,
      source: `${baseStack.metadata.source}; current bylaw target zones from council meeting JSON`,
      note: "Restriction geometry uses the primary item parcel as the spatial reference. Regulation distances are read from the current bylaw entries for the from/to zones.",
      fromRestrictionTypes: fromTypes.length,
      toRestrictionTypes: toTypes.length,
    },
  };
}

async function loadCouncilMeetingItem3dContext(itemId, radiusM = 250) {
  const context = await loadCouncilMeetingItem(itemId);
  if (!context) return null;
  const pids = extractCouncilItemPids(context.item);
  const parcelPayload = await loadCouncilMeetingItemParcels(itemId);
  const resolved = parcelPayload?.parcels?.find((row) => row.resolution?.status === "resolved");
  const primaryPid = resolved?.pid || pids[0];
  if (!primaryPid) return null;
  const payload = await loadParcel3dContext(primaryPid, radiusM);
  if (!payload) {
    const fallback = parcelPayload?.parcels?.find((row) => row.parcel);
    if (!fallback) return null;
    return {
      pid: fallback.pid,
      itemId,
      pids,
      title: context.item.title || context.item.title_raw || itemId,
      address: fallback.address,
      parcel: fallback.parcel,
      parcels: {
        type: "FeatureCollection",
        features: parcelPayload.parcels
          .filter((row) => row.parcel?.geometry)
          .map((row) => ({
            type: "Feature",
            id: row.parcel.parcelId,
            geometry: row.parcel.geometry,
            properties: {
              kind: "parcel",
              parcelId: row.parcel.parcelId,
              relation: row.pid === fallback.pid ? "selected" : "adjacent",
              pid: row.pid,
              attributes: row.parcel.attributes,
            },
          })),
      },
      buildings: { type: "FeatureCollection", features: [] },
      roads: { type: "FeatureCollection", features: [] },
      terrain: {
        available: false,
        status: "fallback_flat",
        reason: "PID was not available in civic address records; 3D context is limited to meeting-derived parcel candidates.",
      },
      metadata: {
        source: "council meeting item fallback parcel candidates from PostGIS zone transition",
        radiusM,
        radiusReason: "Fallback context is centered on a zone-transition candidate because the meeting PID is not joined to civic address records.",
        buildingScope: "Unavailable for fallback PID context.",
        geometrySrid: 4326,
        terrainStatus: "fallback_flat",
        terrainUsage: "fallback_flat",
      },
    };
  }
  return {
    ...payload,
    itemId,
    pids,
    title: context.item.title || context.item.title_raw || itemId,
    metadata: {
      ...payload.metadata,
      source: `${payload.metadata.source}; council meeting item PID set from meeting JSON`,
      radiusReason: `${radiusM} m radius is centered on the primary selected PID for the council item while retaining all selected item PIDs in metadata.`,
    },
  };
}

function zoneNameFromPartTitle(partTitle, zoneCode) {
  const title = compactText(partTitle);
  const code = compactText(zoneCode);
  if (!title || !code) {
    return title;
  }
  return title.replace(new RegExp(`\\s*\\(${code.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\)\\s*$`, "i"), "").trim();
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
      s.section_id,
      s.section_source_id,
      s.section_label_raw,
      s.section_title_raw,
      s.citations,
      sf.repo_relpath,
      COALESCE(
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'label', c.clause_label_raw,
              'text', c.clause_text_raw,
              'citations', c.citations,
              'sourceOrder', c.source_order
            )
            ORDER BY c.source_order, c.clause_id
          )
          FROM zoning.clause c
          WHERE c.section_id = s.section_id
            AND c.is_active
        ),
        '[]'::jsonb
      ) AS clauses,
      COALESCE(
        (
          SELECT jsonb_agg(table_payload ORDER BY table_source_order, raw_table_id)
          FROM (
            SELECT
              rt.raw_table_id,
              rt.source_order AS table_source_order,
              jsonb_build_object(
                'title', rt.table_title_raw,
                'sourceOrder', rt.source_order,
                'citations', rt.citations,
                'columns', COALESCE(
                  (
                    SELECT jsonb_agg(column_payload ORDER BY first_column_order, first_cell_id)
                    FROM (
                      SELECT DISTINCT ON (rtc.column_id)
                        rtc.column_id,
                        MIN(rtc.column_order) OVER (PARTITION BY rtc.column_id) AS first_column_order,
                        MIN(rtc.raw_table_cell_id) OVER (PARTITION BY rtc.column_id) AS first_cell_id,
                        jsonb_build_object(
                          'columnId', rtc.column_id,
                          'columnLabel', rtc.column_label_raw,
                          'columnOrder', MIN(rtc.column_order) OVER (PARTITION BY rtc.column_id)
                        ) AS column_payload
                      FROM zoning.raw_table_cell rtc
                      WHERE rtc.raw_table_id = rt.raw_table_id
                        AND rtc.is_active
                        AND rtc.column_id IS NOT NULL
                      ORDER BY rtc.column_id, rtc.column_order, rtc.raw_table_cell_id
                    ) table_columns
                  ),
                  '[]'::jsonb
                ),
                'rows', COALESCE(
                  (
                    SELECT jsonb_agg(row_payload ORDER BY row_order)
                    FROM (
                      SELECT
                        rtc.row_order,
                        jsonb_build_object(
                          'sourceOrder', rtc.row_order,
                          'cells', jsonb_agg(
                            jsonb_build_object(
                              'columnId', rtc.column_id,
                              'columnLabel', rtc.column_label_raw,
                              'columnOrder', rtc.column_order,
                              'text', rtc.cell_text_raw
                            )
                            ORDER BY rtc.column_order, rtc.raw_table_cell_id
                          )
                        ) AS row_payload
                      FROM zoning.raw_table_cell rtc
                      WHERE rtc.raw_table_id = rt.raw_table_id
                        AND rtc.is_active
                      GROUP BY rtc.row_order
                    ) table_rows
                  ),
                  '[]'::jsonb
                )
              ) AS table_payload
            FROM zoning.raw_table rt
            WHERE (rt.section_id = s.section_id OR rt.natural_key LIKE s.natural_key || '|table|%')
              AND rt.is_active
          ) section_tables
        ),
        '[]'::jsonb
      ) AS tables
    FROM zoning.section s
    JOIN zoning.source_file sf
      ON sf.source_file_id = s.source_file_id
    WHERE s.is_active
      AND s.document_type = 'zone'
      AND s.zone_code = $1
      AND sf.repo_relpath LIKE $2
    ORDER BY s.source_order, s.section_id
    `,
    [zoneCode, sourcePathPattern],
  );
  return rows.map(mapZoneSectionRow);
}

const MAX_REFERENCE_DEPTH = 4;

async function attachReferencedSections(sections, zoneCode, sourceKind) {
  const knownZoneCodes = await loadKnownZoneCodes();
  const cache = new Map();

  async function loadCached(referencedZoneCode) {
    const cacheKey = `${sourceKind}:${referencedZoneCode}`;
    if (!cache.has(cacheKey)) {
      cache.set(cacheKey, await loadZoneSections(referencedZoneCode, sourceKind));
    }
    return cache.get(cacheKey);
  }

  async function attachToClauses(clauseList, hostZoneCode, visited, depth) {
    for (const clause of clauseList || []) {
      const referencedZoneCodes = extractReferencedZoneCodes(clause.text, knownZoneCodes, hostZoneCode);
      if (!referencedZoneCodes.length) continue;
      const newRefs = [];
      for (const referencedZoneCode of referencedZoneCodes) {
        if (visited.has(referencedZoneCode)) continue;
        const baseSections = await loadCached(referencedZoneCode);
        const clonedSections = JSON.parse(JSON.stringify(baseSections));
        if (depth + 1 < MAX_REFERENCE_DEPTH) {
          const nextVisited = new Set(visited);
          nextVisited.add(referencedZoneCode);
          for (const nestedSection of clonedSections) {
            await attachToClauses(nestedSection.clauses, referencedZoneCode, nextVisited, depth + 1);
          }
        }
        newRefs.push({ zoneCode: referencedZoneCode, sections: clonedSections });
      }
      if (newRefs.length) clause.references = newRefs;
    }
  }

  for (const section of sections) {
    await attachToClauses(section.clauses, zoneCode, new Set([zoneCode]), 0);
  }
  return sections;
}

function mapStructuredFactRow(row) {
  const payload = toJsonValue(row.value_payload);
  const rawText = compactText(row.raw_text)
    || compactText(payload.requirement_text_raw)
    || compactText(payload.use_name_raw)
    || compactText(payload.term_raw)
    || compactText(row.raw_label);
  const normalizedKey = compactText(row.normalized_key)
    || compactText(payload.term_normalized)
    || compactText(payload.code)
    || normalizeComparisonKey(rawText);
  return {
    factId: row.structured_fact_id === null || row.structured_fact_id === undefined ? null : Number(row.structured_fact_id),
    family: compactText(row.fact_family),
    type: compactText(row.fact_type),
    label: compactText(row.raw_label) || compactText(payload.requirement_label_raw),
    text: rawText,
    key: normalizedKey,
    value: payload,
    filePath: compactText(row.repo_relpath),
    sourceOrder: row.source_order === null || row.source_order === undefined ? null : Number(row.source_order),
  };
}

function structuredValueText(fact) {
  const payload = fact?.value || {};
  return compactText(fact?.displayText)
    || compactText(payload.use_name_raw)
    || compactText(payload.requirement_text_raw)
    || compactText(fact?.text)
    || compactText(payload.value_raw)
    || compactText(fact?.label);
}

function setbackRowsFromStructuredComparison(comparison, side) {
  const groups = comparison?.structuredData?.groups || [];
  return groups
    .flatMap((group) => group.rows || [])
    .filter((row) => {
      const text = `${row.label || ""} ${row[side] || ""}`.toLowerCase();
      return text.includes("setback") || text.includes("stepback") || text.includes("yard");
    })
    .map((row) => ({ label: compactText(row.label) || "Setback", text: compactText(row[side]) || compactText(row.label) }))
    .filter((row) => row.text);
}

function parseSetbackDistances(rows) {
  const distances = [];
  for (const row of rows) {
    const text = toStringValue(row.text);
    const label = toStringValue(row.label).toLowerCase();
    const relevantLines = text
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => {
        const lower = line.toLowerCase();
        if (/\b(fence|tree|buffer|landscape)\b/.test(lower)) return false;
        return !label || lower.includes(label) || /\b(yard|setback|stepback)\b/.test(lower);
      });
    if (!relevantLines.length && /\b(fence|tree|buffer|landscape)\b/i.test(text)) {
      continue;
    }
    const parseText = relevantLines.length ? relevantLines.join("\n") : text;
    const rangeMatch = parseText.match(/(\d+(?:\.\d+)?)\s*[-\u2013]\s*(\d+(?:\.\d+)?)\s*m\b/i);
    const minimumMatches = [...parseText.matchAll(/\b(?:min\.?|minimum)\s*:?\s*(\d+(?:\.\d+)?)\s*m\b/gi)];
    const metreMatches = [...parseText.matchAll(/\b(\d+(?:\.\d+)?)\s*m\b/gi)];
    const candidates = minimumMatches.length
      ? minimumMatches.map((match) => Number(match[1]))
      : rangeMatch
        ? [Number(rangeMatch[1])]
        : metreMatches.map((match) => Number(match[1]));
    for (const value of candidates) {
      if (!Number.isFinite(value) || value < 0 || value > 100) continue;
      const key = value.toFixed(2);
      if (distances.some((item) => item.key === key)) continue;
      distances.push({
        key,
        distanceM: value,
        label: row.label,
        basis: parseText,
      });
    }
  }
  return distances.sort((a, b) => b.distanceM - a.distanceM).slice(0, 1);
}

const restrictionTypeDefinitions = [
  { key: "front_yard", label: "Front yard", roles: ["front"], patterns: [/front\s+yard/i, /front.*setback/i] },
  { key: "rear_yard", label: "Rear yard", roles: ["rear"], patterns: [/rear\s+yard/i, /rear.*setback/i] },
  { key: "side_yard", label: "Side yard", roles: ["side"], patterns: [/side\s+yard/i, /side.*setback/i, /interior\s+yard/i] },
  { key: "flankage_yard", label: "Flankage yard", roles: ["flankage"], patterns: [/flankage/i, /flanking/i] },
  { key: "setback", label: "General setback", roles: ["front", "side", "rear"], patterns: [/setback/i, /stepback/i] },
  { key: "yard_minimum", label: "Yard minimum", roles: ["front", "side", "rear"], patterns: [/\byard\b/i] },
];

function restrictionDefinitionForRow(row) {
  const haystack = `${row.label || ""} ${row.text || ""}`.toLowerCase();
  return restrictionTypeDefinitions.find((definition) => {
    if (definition.key !== "setback" && haystack.includes(definition.key.replace(/_/g, " "))) {
      return true;
    }
    return definition.patterns.some((pattern) => pattern.test(haystack));
  }) || null;
}

function categorizedRestrictionRows(comparison, side) {
  const rows = setbackRowsFromStructuredComparison(comparison, side);
  const byType = new Map();
  for (const row of rows) {
    const definition = restrictionDefinitionForRow(row);
    if (!definition) continue;
    const distances = parseSetbackDistances([row]);
    if (!distances.length) continue;
    const existing = byType.get(definition.key) || {
      key: definition.key,
      label: definition.label,
      roles: definition.roles,
      rows: [],
      distances: [],
    };
    existing.rows.push(row);
    for (const distance of distances) {
      const duplicate = existing.distances.some((candidate) => Math.abs(candidate.distanceM - distance.distanceM) < 0.01);
      if (!duplicate) {
        existing.distances.push(distance);
      }
    }
    byType.set(definition.key, existing);
  }
  return [...byType.values()].map((entry) => ({
    ...entry,
    distances: entry.distances.sort((a, b) => a.distanceM - b.distanceM).slice(0, 4),
  }));
}

async function loadParcelRestrictionStack(pid, comparisonOverride = null) {
  const comparison = comparisonOverride || await loadZoningComparisonByPid(pid);
  if (!comparison) {
    return null;
  }

  const currentTypes = categorizedRestrictionRows(comparison, "current");
  const draftTypes = categorizedRestrictionRows(comparison, "draft");
  const typeByKey = new Map();
  for (const type of [...currentTypes, ...draftTypes]) {
    const existing = typeByKey.get(type.key) || {
      key: type.key,
      label: type.label,
      roles: type.roles,
      availableIn: [],
      examples: {},
    };
    if (currentTypes.includes(type)) existing.availableIn.push("current");
    if (draftTypes.includes(type)) existing.availableIn.push("draft");
    typeByKey.set(type.key, existing);
  }
  for (const side of ["current", "draft"]) {
    for (const type of side === "current" ? currentTypes : draftTypes) {
      const entry = typeByKey.get(type.key);
      entry.examples[side] = type.distances.map((distance) => ({
        distanceM: distance.distanceM,
        label: distance.label,
        basis: distance.basis,
      }));
    }
  }

  const overlayRows = [
    ...currentTypes.flatMap((type) => type.distances.map((distance) => ({
      side: "current",
      type_key: type.key,
      type_label: type.label,
      roles: type.roles,
      distance_m: distance.distanceM,
      basis: distance.basis,
      label: distance.label,
    }))),
    ...draftTypes.flatMap((type) => type.distances.map((distance) => ({
      side: "draft",
      type_key: type.key,
      type_label: type.label,
      roles: type.roles,
      distance_m: distance.distanceM,
      basis: distance.basis,
      label: distance.label,
    }))),
  ];

  const { rows } = await pool.query(
    `
    WITH selected_address AS (
      SELECT
        geom,
        NULLIF(trim(attributes ->> 'STREET_NM'), '') AS street_name
      FROM zoning.v_charlottetown_civic_addresses
      WHERE NULLIF(trim(attributes ->> 'PID'), '') = $1
         OR NULLIF(trim(attributes ->> 'pid2'), '') = $1
      ORDER BY spatial_feature_id
      LIMIT 1
    ),
    selected_parcel AS (
      SELECT p.spatial_feature_id, p.feature_key, p.attributes, p.is_valid, p.validation_reason, p.geom
      FROM selected_address a
      JOIN zoning.v_charlottetown_parcel_map p
        ON ST_Covers(p.geom, a.geom)
      ORDER BY ST_Area(p.geom), p.spatial_feature_id
      LIMIT 1
    ),
    context_extent AS (
      SELECT ST_Buffer(geom, 130) AS geom FROM selected_parcel
    ),
    selected_buildings AS (
      SELECT
        b.spatial_feature_id,
        b.feature_key,
        b.building,
        b.name,
        b.levels,
        b.height_lidar_m,
        b.height_lidar_confidence,
        b.height_lidar_status,
        b.geom
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_buildings b
        ON b.geom && ST_Buffer(p.geom, 55)
       AND ST_Intersects(b.geom, ST_Buffer(p.geom, 55))
      ORDER BY ST_Area(ST_Intersection(b.geom, p.geom)) DESC NULLS LAST, b.spatial_feature_id
      LIMIT 40
    ),
    parcel_parts AS (
      SELECT (ST_Dump(ST_ForcePolygonCCW(p.geom))).geom AS geom
      FROM selected_parcel p
    ),
    boundary_segments AS (
      SELECT
        row_number() OVER () AS segment_id,
        segment.geom AS geom
      FROM parcel_parts
      CROSS JOIN LATERAL ST_DumpSegments(ST_ExteriorRing(geom)) AS segment
    ),
    normalized_address AS (
      SELECT regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(
              regexp_replace(lower(street_name), '[^a-z0-9]+', '', 'g'),
              'rd$',
              'road'
            ),
            'ave?$',
            'avenue'
          ),
          'cr$',
          'crescent'
        ),
        'st$',
        'street'
      ) AS street_key
      FROM selected_address
    ),
    segment_distances AS (
      SELECT
        s.segment_id,
        s.geom,
        ST_Length(s.geom) AS length_m,
        degrees(ST_Azimuth(ST_StartPoint(s.geom), ST_EndPoint(s.geom))) AS segment_angle,
        ST_Buffer(s.geom, 18, 'side=right endcap=flat join=mitre') AS outside_geom,
        ST_Centroid(s.geom) AS midpoint,
        COALESCE((
          SELECT min(ST_Distance(ST_Buffer(s.geom, 18, 'side=right endcap=flat join=mitre'), r.geom))
          FROM zoning.v_charlottetown_street_network r
          JOIN context_extent e ON r.geom && e.geom AND ST_Intersects(r.geom, e.geom)
        ), 999999) AS road_distance,
        (
          SELECT COALESCE(r.attributes->>'name', r.attributes->>'STREET_NM', r.attributes->>'NAME')
          FROM zoning.v_charlottetown_street_network r
          JOIN context_extent e ON r.geom && e.geom AND ST_Intersects(r.geom, e.geom)
          ORDER BY ST_Distance(ST_Buffer(s.geom, 18, 'side=right endcap=flat join=mitre'), r.geom), r.spatial_feature_id
          LIMIT 1
        ) AS nearest_road_name,
        (
          SELECT degrees(ST_Azimuth(ST_StartPoint(d.geom), ST_EndPoint(d.geom)))
          FROM zoning.v_charlottetown_street_network r
          CROSS JOIN LATERAL ST_Dump(r.geom) AS d
          JOIN context_extent e ON r.geom && e.geom AND ST_Intersects(r.geom, e.geom)
          ORDER BY ST_Distance(ST_Buffer(s.geom, 18, 'side=right endcap=flat join=mitre'), d.geom), r.spatial_feature_id
          LIMIT 1
        ) AS nearest_road_angle,
        COALESCE((
          SELECT min(ST_Distance(ST_Buffer(s.geom, 18, 'side=right endcap=flat join=mitre'), r.geom))
          FROM zoning.v_charlottetown_street_network r
          JOIN context_extent e ON r.geom && e.geom AND ST_Intersects(r.geom, e.geom)
          WHERE regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(lower(COALESCE(r.attributes->>'name', r.attributes->>'STREET_NM', r.attributes->>'NAME', '')), '[^a-z0-9]+', '', 'g'), 'rd$', 'road'), 'ave?$', 'avenue'), 'cr$', 'crescent'), 'st$', 'street') = (SELECT street_key FROM normalized_address)
        ), 999999) AS address_road_distance,
        (
          SELECT degrees(ST_Azimuth(ST_StartPoint(d.geom), ST_EndPoint(d.geom)))
          FROM zoning.v_charlottetown_street_network r
          CROSS JOIN LATERAL ST_Dump(r.geom) AS d
          JOIN context_extent e ON r.geom && e.geom AND ST_Intersects(r.geom, e.geom)
          WHERE regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(lower(COALESCE(r.attributes->>'name', r.attributes->>'STREET_NM', r.attributes->>'NAME', '')), '[^a-z0-9]+', '', 'g'), 'rd$', 'road'), 'ave?$', 'avenue'), 'cr$', 'crescent'), 'st$', 'street') = (SELECT street_key FROM normalized_address)
          ORDER BY ST_Distance(ST_Buffer(s.geom, 18, 'side=right endcap=flat join=mitre'), d.geom), r.spatial_feature_id
          LIMIT 1
        ) AS address_road_angle,
        ST_Distance(ST_Centroid(s.geom), (SELECT ST_Centroid(geom) FROM selected_parcel)) AS center_distance
      FROM boundary_segments s
    ),
    road_threshold AS (
      SELECT CASE WHEN min(road_distance) <= 0.5 THEN 0.5 ELSE min(road_distance) + 0.5 END AS distance_m
      FROM segment_distances
    ),
    road_facing_segments AS (
      SELECT
        s.*,
        regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(lower(COALESCE(s.nearest_road_name, '')), '[^a-z0-9]+', '', 'g'), 'rd$', 'road'), 'ave?$', 'avenue'), 'cr$', 'crescent'), 'st$', 'street') AS road_key
      FROM segment_distances s
      WHERE (
          road_distance <= (SELECT distance_m FROM road_threshold)
          AND nearest_road_angle IS NOT NULL
          AND abs(mod((segment_angle - nearest_road_angle + 270)::numeric, 180) - 90) <= 35
        )
        OR (
          road_distance <= (SELECT distance_m FROM road_threshold)
          AND length_m <= 2.5
        )
         OR (
           regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(lower(COALESCE(s.nearest_road_name, '')), '[^a-z0-9]+', '', 'g'), 'rd$', 'road'), 'ave?$', 'avenue'), 'cr$', 'crescent'), 'st$', 'street') = (SELECT street_key FROM normalized_address)
           AND road_distance <= 25
           AND nearest_road_angle IS NOT NULL
           AND abs(mod((segment_angle - nearest_road_angle + 270)::numeric, 180) - 90) <= 35
         )
    ),
    front_matched_segments AS (
      SELECT segment_id, midpoint
      FROM road_facing_segments
      WHERE address_road_distance <= 25
        AND address_road_angle IS NOT NULL
        AND abs(mod((segment_angle - address_road_angle + 270)::numeric, 180) - 90) <= 35
    ),
    front_fallback_segments AS (
      SELECT segment_id, midpoint
      FROM road_facing_segments
      WHERE NOT EXISTS (
        SELECT 1 FROM front_matched_segments
      )
      ORDER BY segment_id
      LIMIT 1
    ),
    front_segments AS (
      SELECT * FROM front_matched_segments
      UNION ALL
      SELECT * FROM front_fallback_segments
    ),
    flankage_segments AS (
      SELECT segment_id, midpoint
      FROM road_facing_segments
      WHERE NOT EXISTS (
        SELECT 1 FROM front_segments f WHERE f.segment_id = road_facing_segments.segment_id
      )
    ),
    non_front_segments AS (
      SELECT
        s.*,
        COALESCE((
          SELECT min(ST_Distance(s.midpoint, f.midpoint))
          FROM front_segments f
        ), 0) AS distance_from_front
      FROM segment_distances s
      WHERE NOT EXISTS (
        SELECT 1 FROM front_segments f WHERE f.segment_id = s.segment_id
      )
    ),
    front_axis AS (
      SELECT COALESCE(avg(s.segment_angle), 0) AS angle
      FROM front_segments f
      JOIN segment_distances s
        ON s.segment_id = f.segment_id
    ),
    rear_distance AS (
      SELECT COALESCE(max(distance_from_front), 0) AS distance_m
      FROM non_front_segments
    ),
    rear_threshold AS (
      SELECT COALESCE(
        percentile_cont(0.65) WITHIN GROUP (ORDER BY distance_from_front),
        999999
      ) AS distance_m
      FROM non_front_segments
    ),
    rear_segments AS (
      SELECT nf.segment_id
      FROM non_front_segments nf
      CROSS JOIN front_axis fa
      CROSS JOIN rear_distance rd
      WHERE rd.distance_m > 0
        AND nf.distance_from_front >= rd.distance_m * 0.82
        AND abs(mod((nf.segment_angle - fa.angle + 270)::numeric, 180) - 90) <= 35
    ),
    classified_segments AS (
      SELECT
        s.segment_id,
        s.geom,
        CASE
          WHEN EXISTS (SELECT 1 FROM front_segments f WHERE f.segment_id = s.segment_id) THEN 'front'
          WHEN EXISTS (SELECT 1 FROM flankage_segments f WHERE f.segment_id = s.segment_id) THEN 'flankage'
          WHEN EXISTS (SELECT 1 FROM rear_segments r WHERE r.segment_id = s.segment_id) THEN 'rear'
          WHEN NOT EXISTS (SELECT 1 FROM rear_segments) AND nf.distance_from_front >= (SELECT distance_m FROM rear_threshold) THEN 'rear'
          ELSE 'side'
        END AS role
      FROM segment_distances s
      LEFT JOIN non_front_segments nf
        ON nf.segment_id = s.segment_id
    ),
    regulation_rows AS (
      SELECT *
      FROM jsonb_to_recordset($2::jsonb) AS d(
        side text,
        type_key text,
        type_label text,
        roles jsonb,
        distance_m double precision,
        basis text,
        label text
      )
    ),
    selected_segments AS (
      SELECT
        r.side,
        r.type_key,
        r.type_label,
        r.distance_m,
        r.basis,
        r.label,
        c.role,
        ST_Buffer(
          ST_LineMerge(ST_UnaryUnion(ST_Collect(c.geom))),
          r.distance_m,
          'endcap=square join=mitre'
        ) AS geom
      FROM regulation_rows r
      JOIN classified_segments c
        ON r.roles ? c.role
      GROUP BY r.side, r.type_key, r.type_label, r.distance_m, r.basis, r.label, c.role
    ),
    restriction_features AS (
      SELECT
        s.side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geom, s.geom), 3)), 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'restriction_area',
            'regulationType', s.type_key,
            'regulationLabel', s.type_label,
            'yardRole', s.role,
            'distanceM', s.distance_m,
            'label', s.label,
            'basis', s.basis
          )
        ) AS feature
      FROM selected_segments s
      CROSS JOIN selected_parcel p
      WHERE s.distance_m > 0
    ),
    base_features AS (
      SELECT
        'both' AS side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(p.geom, 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'selected_parcel',
            'parcelId', p.feature_key
          )
        ) AS feature
      FROM selected_parcel p
    ),
    neighbor_parcels AS (
      SELECT
        n.spatial_feature_id,
        n.feature_key,
        n.geom,
        nb.geom AS building_geom,
        (
          SELECT concat_ws(
            ' ',
            NULLIF(trim(a.attributes ->> 'STREET_NO'), ''),
            NULLIF(trim(a.attributes ->> 'STREET_NM'), '')
          )
          FROM zoning.v_charlottetown_civic_addresses a
          WHERE ST_Covers(n.geom, a.geom)
          ORDER BY ST_Distance(a.geom, ST_Centroid(n.geom)), a.spatial_feature_id
          LIMIT 1
        ) AS address_label,
        (
          WITH neighbor_building AS (
            SELECT nb.geom
            WHERE nb.geom IS NOT NULL
          ),
          envelope AS (
            SELECT (ST_Dump(ST_OrientedEnvelope(geom))).geom AS geom
            FROM neighbor_building
          ),
          segments AS (
            SELECT segment.geom
            FROM envelope
            CROSS JOIN LATERAL ST_DumpSegments(ST_ExteriorRing(geom)) AS segment
          ),
          ranked AS (
            SELECT
              degrees(ST_Azimuth(ST_StartPoint(geom), ST_EndPoint(geom))) AS angle,
              ST_Length(geom) AS length_m
            FROM segments
            ORDER BY length_m DESC
            LIMIT 1
          )
          SELECT CASE
            WHEN angle > 90 AND angle <= 270 THEN angle - 180
            WHEN angle > 270 THEN angle - 360
            ELSE angle
          END
          FROM ranked
        ) AS address_angle
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_parcel_map n
        ON n.geom && ST_Buffer(p.geom, 45)
       AND ST_Intersects(n.geom, ST_Buffer(p.geom, 45))
       AND n.spatial_feature_id <> p.spatial_feature_id
      LEFT JOIN LATERAL (
        SELECT b.geom
        FROM selected_buildings b
        WHERE ST_Intersects(b.geom, n.geom)
        ORDER BY ST_Area(ST_Intersection(b.geom, n.geom)) DESC, b.spatial_feature_id
        LIMIT 1
      ) nb ON TRUE
      ORDER BY ST_Distance(ST_Centroid(n.geom), ST_Centroid(p.geom)), n.spatial_feature_id
      LIMIT 80
    ),
    neighbor_features AS (
      SELECT
        'both' AS side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(n.geom, 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'neighbor_parcel',
            'parcelId', n.feature_key,
            'addressLabel', n.address_label,
            'addressAngle', n.address_angle,
            'addressPoint', CASE
              WHEN n.building_geom IS NOT NULL THEN jsonb_build_object(
                'lon', ST_X(ST_Transform(ST_PointOnSurface(n.building_geom), 4326)),
                'lat', ST_Y(ST_Transform(ST_PointOnSurface(n.building_geom), 4326))
              )
              ELSE jsonb_build_object(
                'lon', ST_X(ST_Transform(ST_Centroid(n.geom), 4326)),
                'lat', ST_Y(ST_Transform(ST_Centroid(n.geom), 4326))
              )
            END
          )
        ) AS feature
      FROM neighbor_parcels n
    ),
    road_features AS (
      SELECT
        'both' AS side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(r.geom, 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'road',
            'featureKey', r.feature_key,
            'name', COALESCE(r.attributes->>'name', r.attributes->>'STREET_NM', r.attributes->>'NAME')
          )
        ) AS feature
      FROM context_extent e
      JOIN zoning.v_charlottetown_street_network r
        ON r.geom && e.geom
       AND ST_Intersects(r.geom, e.geom)
      LIMIT 80
    ),
    building_features AS (
      SELECT
        'both' AS side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(b.geom, 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'building',
            'building', b.building,
            'name', b.name,
            'levels', b.levels,
            'heightLidarM', b.height_lidar_m,
            'heightLidarConfidence', b.height_lidar_confidence,
            'heightLidarStatus', b.height_lidar_status,
            'featureKey', b.feature_key
          )
        ) AS feature
      FROM selected_buildings b
    ),
    all_features AS (
      SELECT * FROM restriction_features
      UNION ALL
      SELECT * FROM base_features
      UNION ALL SELECT * FROM neighbor_features
      UNION ALL SELECT * FROM building_features
      UNION ALL SELECT * FROM road_features
    )
    SELECT side, COALESCE(jsonb_agg(feature), '[]'::jsonb) AS features
    FROM all_features
    GROUP BY side
    `,
    [pid, JSON.stringify(overlayRows)],
  );

  const bySide = new Map(rows.map((row) => [row.side, row.features || []]));
  const sharedFeatures = bySide.get("both") || [];
  return {
    pid,
    address: comparison.address,
    parcel: comparison.parcel,
    zones: comparison.zones,
    regulationTypes: [...typeByKey.values()].map((type) => ({
      ...type,
      availableIn: [...new Set(type.availableIn)].sort(),
    })),
    current: { type: "FeatureCollection", features: [...sharedFeatures, ...(bySide.get("current") || [])] },
    draft: { type: "FeatureCollection", features: [...sharedFeatures, ...(bySide.get("draft") || [])] },
    metadata: {
      source: "PostGIS parcel boundary segment classification using nearest zoning.v_charlottetown_street_network geometry",
      note: "Front is inferred from every road-facing parcel edge, including corner lots. Rear is inferred from the non-front edges farthest opposite the front edges. Side is the remaining lot-line edge between front and rear, following the definitions in both bylaw definitions JSON files.",
    },
  };
}

function structuredNumericSignature(fact) {
  const payload = fact?.value || {};
  if (payload.value !== undefined && payload.value !== null) {
    return JSON.stringify([payload.comparator || "", payload.measure_type || "", payload.unit || "", Number(payload.value)]);
  }
  return JSON.stringify(payload.numeric_value_refs || []);
}

function numericTextSignature(value) {
  const matches = toStringValue(value).match(/-?\d+(?:\.\d+)?/g) || [];
  return JSON.stringify(matches.map((match) => Number(match)));
}

function compareStructuredSides(currentFact, draftFact) {
  if (!currentFact && !draftFact) {
    return "pending";
  }
  if (!currentFact || !draftFact) {
    return "changed";
  }
  if (currentFact.family === "numeric_values" || draftFact.family === "numeric_values") {
    return structuredNumericSignature(currentFact) === structuredNumericSignature(draftFact) ? "same" : "changed";
  }
  if (currentFact.value?.numeric_value_refs?.length || draftFact.value?.numeric_value_refs?.length) {
    return numericTextSignature(structuredValueText(currentFact)) === numericTextSignature(structuredValueText(draftFact)) ? "source" : "changed";
  }
  return structuredValueText(currentFact) === structuredValueText(draftFact) ? "same" : "source";
}

function buildStructuredRows(currentFacts, draftFacts, options = {}) {
  const currentByKey = new Map();
  const draftByKey = new Map();
  for (const fact of currentFacts) {
    const key = options.keyFor ? options.keyFor(fact) : fact.key;
    if (!key) continue;
    currentByKey.set(key, [...(currentByKey.get(key) || []), fact]);
  }
  for (const fact of draftFacts) {
    const key = options.keyFor ? options.keyFor(fact) : fact.key;
    if (!key) continue;
    draftByKey.set(key, [...(draftByKey.get(key) || []), fact]);
  }

  const keys = [...new Set([...currentByKey.keys(), ...draftByKey.keys()])].sort((a, b) => {
    const currentA = currentByKey.get(a)?.[0];
    const draftA = draftByKey.get(a)?.[0];
    const currentB = currentByKey.get(b)?.[0];
    const draftB = draftByKey.get(b)?.[0];
    const labelA = structuredValueText(currentA || draftA) || a;
    const labelB = structuredValueText(currentB || draftB) || b;
    return labelA.localeCompare(labelB);
  });

  return keys.map((key) => {
    const current = currentByKey.get(key) || [];
    const draft = draftByKey.get(key) || [];
    const currentText = current.map(structuredValueText).filter(Boolean).join("\n");
    const draftText = draft.map(structuredValueText).filter(Boolean).join("\n");
    return {
      key,
      label: options.labelFor ? options.labelFor(current[0] || draft[0], key) : structuredValueText(current[0] || draft[0]) || key,
      current: currentText || null,
      draft: draftText || null,
      status: compareStructuredSides(current[0], draft[0]),
      numericChanged: Boolean(current[0] && draft[0] && compareStructuredSides(current[0], draft[0]) === "changed" && (
        current[0].family === "numeric_values"
        || draft[0].family === "numeric_values"
        || current[0].value?.numeric_value_refs?.length
        || draft[0].value?.numeric_value_refs?.length
      )),
    };
  });
}

async function loadZoneStructuredFacts(zoneCode, sourceKind, visitedZoneCodes = new Set()) {
  if (!zoneCode) {
    return { uses: [], requirements: [], otherRequirements: [], numericValues: [], clauses: [] };
  }
  if (visitedZoneCodes.has(`${sourceKind}:${zoneCode}`)) {
    return { uses: [], requirements: [], otherRequirements: [], numericValues: [], clauses: [] };
  }
  const nextVisitedZoneCodes = new Set(visitedZoneCodes);
  nextVisitedZoneCodes.add(`${sourceKind}:${zoneCode}`);
  const zonePath = sourceKind === "draft"
    ? `data/zoning/charlottetown-draft/zones/${zoneCode.toLowerCase()}.json`
    : `data/zoning/charlottetown/zones/${zoneCode.toLowerCase()}.json`;

  const [factsResult, clausesResult] = await Promise.all([
    pool.query(
      `
      SELECT
        f.structured_fact_id,
        f.fact_family,
        f.fact_type,
        f.raw_label,
        f.raw_text,
        f.normalized_key,
        f.value_payload,
        f.citations,
        sf.repo_relpath,
        f.structured_fact_id AS source_order
      FROM zoning.structured_fact f
      JOIN zoning.source_file sf
        ON sf.source_file_id = f.source_file_id
      WHERE f.is_active
        AND sf.repo_relpath = $1
        AND f.fact_family IN ('uses', 'requirements', 'other_requirements', 'numeric_values')
      ORDER BY f.fact_family, f.structured_fact_id
      `,
      [zonePath],
    ),
    pool.query(
      `
      SELECT
        c.clause_label_raw,
        c.clause_text_raw,
        c.source_order,
        s.section_label_raw,
        s.section_title_raw,
        sf.repo_relpath
      FROM zoning.section s
      JOIN zoning.source_file sf
        ON sf.source_file_id = s.source_file_id
      JOIN zoning.clause c
        ON c.section_id = s.section_id
      WHERE s.is_active
        AND c.is_active
        AND s.document_type = 'zone'
        AND s.zone_code = $2
        AND sf.repo_relpath = $1
      ORDER BY s.source_order, c.source_order, c.clause_id
      `,
      [zonePath, zoneCode],
    ),
  ]);

  const facts = factsResult.rows.map(mapStructuredFactRow);
  const data = {
    uses: facts
      .filter((fact) => fact.family === "uses" && compactText(fact.value?.use_status) === "permitted")
      .map((fact) => ({
        ...fact,
        key: normalizeComparisonKey(fact.value?.use_name_raw || fact.text || fact.key),
      })),
    requirements: facts.filter((fact) => fact.family === "requirements"),
    otherRequirements: facts.filter((fact) => fact.family === "other_requirements"),
    numericValues: facts.filter((fact) => fact.family === "numeric_values"),
    clauses: clausesResult.rows.map((row) => ({
      label: compactText(row.clause_label_raw),
      text: compactText(row.clause_text_raw),
      key: normalizeComparisonKey(row.clause_text_raw),
      sectionLabel: compactText(row.section_label_raw),
      sectionTitle: compactText(row.section_title_raw),
      filePath: compactText(row.repo_relpath),
      sourceOrder: row.source_order === null || row.source_order === undefined ? null : Number(row.source_order),
    })),
  };

  const knownZoneCodes = await loadKnownZoneCodes();
  const referencedZoneCodes = [
    ...new Set(data.clauses.flatMap((clause) => extractReferencedZoneCodes(clause.text, knownZoneCodes, zoneCode))),
  ];
  for (const referencedZoneCode of referencedZoneCodes) {
    const referencedData = await loadZoneStructuredFacts(referencedZoneCode, sourceKind, nextVisitedZoneCodes);
    for (const use of referencedData.uses) {
      data.uses.push({
        ...use,
        key: normalizeComparisonKey(use.value?.use_name_raw || use.text || use.key),
        inheritedFromZoneCode: referencedZoneCode,
        displayText: `${structuredValueText(use)} [from ${referencedZoneCode}]`,
      });
    }
  }

  return data;
}

function buildStructuredComparison(currentData, draftData) {
  return {
    groups: [
      {
        key: "permitted_uses",
        title: "Permitted uses",
        rows: buildStructuredRows(currentData.uses, draftData.uses),
      },
      {
        key: "requirements",
        title: "Structured requirements",
        rows: buildStructuredRows(currentData.requirements, draftData.requirements, {
          keyFor: (fact) => compactText(fact.value?.requirement_category) || compactText(fact.type) || fact.key,
          labelFor: (fact, key) => humanizeKey(compactText(fact?.value?.requirement_category) || key),
        }),
      },
      {
        key: "other_requirements",
        title: "Other structured clauses",
        rows: buildStructuredRows(currentData.otherRequirements, draftData.otherRequirements, {
          keyFor: (fact) => compactText(fact.value?.requirement_category) || fact.key,
          labelFor: (fact, key) => humanizeKey(compactText(fact?.value?.requirement_category) || key),
        }),
      },
      {
        key: "clauses",
        title: "Bylaw clauses",
        rows: buildStructuredRows(currentData.clauses, draftData.clauses, {
          keyFor: (fact) => fact.key,
          labelFor: (fact) => compactText(fact?.label) || compactText(fact?.sectionTitle) || "Clause",
        }),
      },
    ],
    source: {
      currentFactCount: currentData.uses.length + currentData.requirements.length + currentData.otherRequirements.length + currentData.numericValues.length,
      draftFactCount: draftData.uses.length + draftData.requirements.length + draftData.otherRequirements.length + draftData.numericValues.length,
      currentClauseCount: currentData.clauses.length,
      draftClauseCount: draftData.clauses.length,
    },
  };
}

function humanizeKey(value) {
  return toStringValue(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
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
  let [currentSections, draftSections] = await Promise.all([
    loadZoneSections(currentLookupCode, "current"),
    loadZoneSections(draftLookupCode, "draft"),
  ]);
  [currentSections, draftSections] = await Promise.all([
    attachReferencedSections(currentSections, currentLookupCode, "current"),
    attachReferencedSections(draftSections, draftLookupCode, "draft"),
  ]);
  const [currentStructured, draftStructured] = await Promise.all([
    loadZoneStructuredFacts(currentLookupCode, "current"),
    loadZoneStructuredFacts(draftLookupCode, "draft"),
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
    ],
    citations: {
      current: currentSections,
      draft: draftSections,
      status: currentSections.length || draftSections.length ? "available" : "pending",
      note: currentSections.length || draftSections.length
        ? "Zone section citations are linked by matched zone code."
        : "Rule-level comparison is pending because no zone-section citations matched the parcel zones.",
    },
    structuredData: buildStructuredComparison(currentStructured, draftStructured),
    resolution: parcel.resolution,
    source: {
      ...parcel.source,
      currentZoneSections: currentSections.length ? "zoning.section" : null,
      draftZoneSections: draftSections.length ? "zoning.section" : null,
    },
  };
}

async function loadParcelRestrictionBuffers(pid) {
  const comparison = await loadZoningComparisonByPid(pid);
  if (!comparison) {
    return null;
  }
  const currentDistances = parseSetbackDistances(setbackRowsFromStructuredComparison(comparison, "current"));
  const draftDistances = parseSetbackDistances(setbackRowsFromStructuredComparison(comparison, "draft"));
  const bufferRows = [
    ...currentDistances.map((distance) => ({ ...distance, side: "current" })),
    ...draftDistances.map((distance) => ({ ...distance, side: "draft" })),
  ];

  const emptyPayload = {
    pid,
    zones: comparison.zones,
    current: { type: "FeatureCollection", features: [] },
    draft: { type: "FeatureCollection", features: [] },
    metadata: {
      source: "PostGIS ST_Buffer on zoning.v_charlottetown_parcel_map in EPSG:2954",
      note: "Buffers are exact parcel-boundary distances from extracted setback facts. Yard-line orientation is not inferred.",
    },
  };
  if (!bufferRows.length) {
    return emptyPayload;
  }

  const { rows } = await pool.query(
    `
    WITH selected_address AS (
      SELECT geom
      FROM zoning.v_charlottetown_civic_addresses
      WHERE NULLIF(trim(attributes ->> 'PID'), '') = $1
         OR NULLIF(trim(attributes ->> 'pid2'), '') = $1
      ORDER BY spatial_feature_id
      LIMIT 1
    ),
    selected_parcel AS (
      SELECT p.geom
      FROM selected_address a
      JOIN zoning.v_charlottetown_parcel_map p
        ON ST_Covers(p.geom, a.geom)
      ORDER BY ST_Area(p.geom), p.spatial_feature_id
      LIMIT 1
    ),
    selected_buildings AS (
      SELECT
        b.spatial_feature_id,
        b.feature_key,
        b.osm_type,
        b.osm_id,
        b.building,
        b.name,
        b.levels,
        b.height_lidar_m,
        b.height_lidar_method,
        b.height_lidar_confidence,
        b.height_lidar_status,
        b.attributes,
        b.geom
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_buildings b
        ON b.geom && p.geom
       AND ST_Intersects(b.geom, p.geom)
      ORDER BY ST_Area(ST_Intersection(b.geom, p.geom)) DESC, b.spatial_feature_id
      LIMIT 12
    ),
    distances AS (
      SELECT *
      FROM jsonb_to_recordset($2::jsonb) AS d(
        side text,
        distance_m double precision,
        label text,
        basis text
      )
    ),
    buffers AS (
      SELECT
        d.side,
        d.distance_m,
        d.label,
        d.basis,
        p.geom AS parcel_geom,
        ST_Multi(ST_Buffer(p.geom, -d.distance_m, 'join=mitre')) AS buildable_geom
      FROM selected_parcel p
      CROSS JOIN distances d
    ),
    features AS (
      SELECT
        side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(ST_Multi(parcel_geom), 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'parcel',
            'distanceM', distance_m,
            'label', label,
            'basis', basis
          )
        ) AS feature
      FROM buffers
      UNION ALL
      SELECT
        side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(ST_CollectionExtract(ST_Multi(ST_Difference(parcel_geom, buildable_geom)), 3), 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'setback_buffer',
            'distanceM', distance_m,
            'label', label,
            'basis', basis
          )
        ) AS feature
      FROM buffers
      WHERE NOT ST_IsEmpty(buildable_geom)
      UNION ALL
      SELECT
        side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(ST_CollectionExtract(buildable_geom, 3), 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'buildable_area',
            'distanceM', distance_m,
            'label', label,
            'basis', basis
          )
        ) AS feature
      FROM buffers
      WHERE NOT ST_IsEmpty(buildable_geom)
      UNION ALL
      SELECT
        d.side,
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(ST_Transform(ST_CollectionExtract(ST_Multi(ST_Intersection(b.geom, p.geom)), 3), 4326))::jsonb,
          'properties', jsonb_build_object(
            'kind', 'building',
            'building', b.building,
            'name', b.name,
            'levels', b.levels,
            'osmType', b.osm_type,
            'osmId', b.osm_id,
            'heightLidarM', b.height_lidar_m,
            'heightLidarMethod', b.height_lidar_method,
            'heightLidarConfidence', b.height_lidar_confidence,
            'heightLidarStatus', b.height_lidar_status,
            'source', jsonb_build_object(
              'table', 'zoning.v_charlottetown_buildings',
              'spatialFeatureId', b.spatial_feature_id,
              'featureKey', b.feature_key
            )
          )
        ) AS feature
      FROM selected_parcel p
      CROSS JOIN distances d
      JOIN selected_buildings b
        ON TRUE
      WHERE NOT ST_IsEmpty(ST_Intersection(b.geom, p.geom))
    )
    SELECT side, COALESCE(jsonb_agg(feature ORDER BY (feature->'properties'->>'distanceM')::double precision, feature->'properties'->>'kind'), '[]'::jsonb) AS features
    FROM features
    GROUP BY side
    `,
    [
      pid,
      JSON.stringify(bufferRows.map((row) => ({
        side: row.side,
        distance_m: row.distanceM,
        label: row.label,
        basis: row.basis,
      }))),
    ],
  );

  const bySide = new Map(rows.map((row) => [row.side, row.features || []]));
  return {
    ...emptyPayload,
    current: { type: "FeatureCollection", features: bySide.get("current") || [] },
    draft: { type: "FeatureCollection", features: bySide.get("draft") || [] },
  };
}

async function loadProvisionsComparison() {
  const { rows: partRows } = await pool.query(`
    WITH part_order(repo_relpath, part_number, display_title, display_order) AS (
      VALUES
        ('data/zoning/charlottetown-draft/administration.json', 'PART 1', 'Administration & Operation', 1),
        ('data/zoning/charlottetown-draft/permit-applications-processes.json', 'PART 2', 'Permit Applications & Processes', 2),
        ('data/zoning/charlottetown-draft/general-provisions-buildings-structures.json', 'PART 3', 'General Provisions for Buildings & Structures', 3),
        ('data/zoning/charlottetown-draft/general-provisions-land-use.json', 'PART 4', 'General Provisions for Land Use', 4),
        ('data/zoning/charlottetown-draft/general-provisions-lots-site-design.json', 'PART 5', 'General Provisions for Lots & Site Design', 5),
        ('data/zoning/charlottetown-draft/design-standards-500-lot-area.json', 'PART 6', 'Design Standards for 500 Lot Area', 6),
        ('data/zoning/charlottetown-draft/general-provisions-subdividing-land.json', 'PART 7', 'General Provisions Subdividing Land', 7),
        ('data/zoning/charlottetown-draft/general-provisions-parking.json', 'PART 8', 'General Provisions for Parking', 8),
        ('data/zoning/charlottetown-draft/general-provisions-signage.json', 'PART 9', 'General Provisions For Signage', 9)
    )
    SELECT
      bp.bylaw_part_id,
      po.part_number,
      po.display_title,
      po.display_order,
      bp.part_title_raw,
      bp.document_type,
      bp.citations,
      sf.repo_relpath
    FROM part_order po
    JOIN zoning.source_file sf
      ON sf.repo_relpath = po.repo_relpath
     AND sf.is_active
    JOIN zoning.bylaw_part bp
      ON bp.source_file_id = sf.source_file_id
     AND bp.is_active
    ORDER BY po.display_order
  `);

  const parts = await Promise.all(partRows.map(loadProvisionsPartComparison));
  const pairCount = parts.reduce((total, part) => total + part.structuredPairs.length, 0);
  const changedCount = parts.reduce(
    (total, part) => total + part.structuredPairs.filter((pair) => pair.rows.some((row) => row.status === "changed")).length,
    0,
  );
  return {
    source: "zoning.bylaw_part, zoning.section, zoning.section_equivalence",
    scope: "draft non-zone parts 1 through 9 with matched current sections",
    generatedAt: new Date().toISOString(),
    summary: {
      parts: parts.length,
      structuredPairs: pairCount,
      changedPairs: changedCount,
    },
    parts,
  };
}

async function loadProvisionsPartComparison(partRow) {
  const draftSections = await loadSectionsByPartId(partRow.bylaw_part_id);
  const { rows: pairRows } = await pool.query(`
    SELECT
      se.section_equivalence_id,
      se.equivalence_type,
      se.assigned_topic,
      se.title_similarity,
      se.text_similarity,
      cs.section_id AS current_section_id,
      cs.section_label_raw AS current_section_label,
      cs.section_title_raw AS current_section_title,
      cs.document_type AS current_document_type,
      cs.source_order AS current_source_order,
      ds.section_id AS draft_section_id,
      ds.section_label_raw AS draft_section_label,
      ds.section_title_raw AS draft_section_title,
      ds.document_type AS draft_document_type,
      ds.source_order AS draft_source_order
    FROM zoning.section_equivalence se
    JOIN zoning.section cs
      ON cs.section_id = se.current_section_id
    JOIN zoning.section ds
      ON ds.section_id = se.draft_section_id
    WHERE se.review_status = 'accepted'
      AND cs.is_active
      AND ds.is_active
      AND COALESCE(ds.document_type, '') <> 'zone'
      AND ds.bylaw_part_id = $1
    ORDER BY ds.source_order, cs.source_order, se.section_equivalence_id
  `, [partRow.bylaw_part_id]);

  const pairs = await Promise.all(pairRows.map(async (row) => {
    const [currentSection, draftSection] = await Promise.all([
      loadSection(row.current_section_id),
      loadSection(row.draft_section_id),
    ]);
    const currentText = sectionComparableText(currentSection);
    const draftText = sectionComparableText(draftSection);
    return {
      sectionEquivalenceId: Number(row.section_equivalence_id),
      topic: compactText(row.assigned_topic),
      equivalenceType: compactText(row.equivalence_type),
      titleSimilarity: row.title_similarity === null ? null : Number(row.title_similarity),
      textSimilarity: row.text_similarity === null ? null : Number(row.text_similarity),
      documentTypes: {
        current: compactText(row.current_document_type),
        draft: compactText(row.draft_document_type),
      },
      current: currentSection,
      draft: draftSection,
      rows: [
        {
          label: "Document type",
          current: compactText(row.current_document_type),
          draft: compactText(row.draft_document_type),
          status: row.current_document_type === row.draft_document_type ? "same" : "changed",
        },
        {
          label: "Section title",
          current: compactText(`${row.current_section_label || ""} ${row.current_section_title || ""}`),
          draft: compactText(`${row.draft_section_label || ""} ${row.draft_section_title || ""}`),
          status: normalizeComparisonKey(`${row.current_section_label || ""} ${row.current_section_title || ""}`)
            === normalizeComparisonKey(`${row.draft_section_label || ""} ${row.draft_section_title || ""}`) ? "same" : "changed",
        },
        {
          label: "Clause count",
          current: currentSection?.clauses?.length ?? null,
          draft: draftSection?.clauses?.length ?? null,
          status: (currentSection?.clauses?.length ?? null) === (draftSection?.clauses?.length ?? null) ? "same" : "changed",
        },
        {
          label: "Text signature",
          current: currentText ? `${currentText.length} chars` : null,
          draft: draftText ? `${draftText.length} chars` : null,
          status: currentText === draftText ? "same" : "source",
        },
      ],
    };
  }));
  const currentSectionIds = [...new Set(pairRows.map((row) => row.current_section_id))];
  const currentSections = await Promise.all(currentSectionIds.map((sectionId) => loadSection(sectionId)));
  currentSections.sort((a, b) => (a?.filePath || "").localeCompare(b?.filePath || "") || toStringValue(a?.sectionId).localeCompare(toStringValue(b?.sectionId)));

  return {
    partId: Number(partRow.bylaw_part_id),
    partNumber: partRow.part_number,
    title: compactText(partRow.display_title) || compactText(partRow.part_title_raw),
    documentType: compactText(partRow.document_type),
    filePath: compactText(partRow.repo_relpath),
    citations: toJsonValue(partRow.citations),
    summary: {
      currentSections: currentSections.filter(Boolean).length,
      draftSections: draftSections.length,
      structuredPairs: pairs.length,
    },
    raw: {
      current: currentSections.filter(Boolean),
      draft: draftSections,
    },
    structuredPairs: pairs,
  };
}

async function loadSectionsByPartId(partId) {
  const { rows } = await pool.query(`
    SELECT section_id
    FROM zoning.section
    WHERE is_active
      AND bylaw_part_id = $1
    ORDER BY source_order, section_id
  `, [partId]);
  return Promise.all(rows.map((row) => loadSection(row.section_id)));
}

function sectionComparableText(section) {
  if (!section) {
    return "";
  }
  return [
    section.label,
    section.title,
    ...(section.clauses || []).map((clause) => `${clause.label || ""} ${clause.text || ""}`),
    ...(section.tables || []).flatMap((table) => [
      table.title,
      ...(table.rows || []).flatMap((row) => (row.cells || []).map((cell) => cell.text)),
    ]),
  ].filter(Boolean).join("\n").replace(/\s+/g, " ").trim();
}

async function loadParcelGeoJson(bbox, limit, filters = {}) {
  const params = [limit];
  const where = [];
  const zoneJoin = (filters.currentZone || filters.draftZone)
    ? "JOIN zoning.v_charlottetown_parcel_zone_assignment za ON za.parcel_spatial_feature_id = p.spatial_feature_id"
    : "";
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    where.push(`
      p.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
      AND ST_Intersects(p.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `);
  }
  if (filters.currentZone) {
    params.push(filters.currentZone);
    where.push(`za.current_zone_code = $${params.length}`);
  }
  if (filters.draftZone) {
    params.push(filters.draftZone);
    where.push(`za.draft_zone_code = $${params.length}`);
  }
  const whereClause = where.length ? `WHERE ${where.join("\n        AND ")}` : "";
  const geomExpression = geometryExpression("p", filters.detail, 4);

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
        ${geomExpression} AS geom
      FROM zoning.v_charlottetown_parcel_map p
      ${zoneJoin}
      ${whereClause}
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
      detail: filters.detail || "detail",
      filters: {
        currentZone: filters.currentZone || null,
        draftZone: filters.draftZone || null,
      },
    },
  };
}

async function loadCurrentZoningGeoJson(bbox, limit, filters = {}) {
  const params = [limit];
  const where = [];
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    where.push(`
      z.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
      AND ST_Intersects(z.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `);
  }
  if (filters.zone) {
    params.push(filters.zone);
    where.push(`${filteredZoneExpression("z")} = $${params.length}`);
  }
  const whereClause = where.length ? `WHERE ${where.join("\n        AND ")}` : "";
  const geomExpression = geometryExpression("z", filters.detail, 8);

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
        ${geomExpression} AS geom
      FROM zoning.v_charlottetown_current_zoning_boundaries z
      ${whereClause}
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
      detail: filters.detail || "detail",
      filters: { zone: filters.zone || null },
    },
  };
}

async function loadDraftZoningGeoJson(bbox, limit, filters = {}) {
  const params = [limit];
  const where = [];
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    where.push(`
      z.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
      AND ST_Intersects(z.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `);
  }
  if (filters.zone) {
    params.push(filters.zone);
    where.push(`${filteredZoneExpression("z")} = $${params.length}`);
  }
  const whereClause = where.length ? `WHERE ${where.join("\n        AND ")}` : "";
  const geomExpression = geometryExpression("z", filters.detail, 8);

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
        ${geomExpression} AS geom
      FROM zoning.v_charlottetown_draft_zoning_boundaries z
      ${whereClause}
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
      detail: filters.detail || "detail",
      filters: { zone: filters.zone || null },
    },
  };
}

async function loadBuildingsGeoJson(bbox, limit, filters = {}) {
  const params = [limit];
  let bboxFilter = "";
  if (bbox) {
    params.push(bbox.west, bbox.south, bbox.east, bbox.north);
    bboxFilter = `
      WHERE b.geom && ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954)
        AND ST_Intersects(b.geom, ST_Transform(ST_MakeEnvelope($2, $3, $4, $5, 4326), 2954))
    `;
  }
  const geomExpression = geometryExpression("b", filters.detail, 3);
  const { rows } = await pool.query(
    `
    WITH source AS (
      SELECT
        b.*,
        ${geomExpression} AS render_geom
      FROM zoning.v_charlottetown_buildings b
      ${bboxFilter}
      ORDER BY spatial_feature_id
      LIMIT $1
    ),
    features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(render_geom, 4326))::jsonb,
        'properties', jsonb_build_object(
          'building', building,
          'name', name,
          'levels', levels,
          'osmType', osm_type,
          'osmId', osm_id,
          'heightLidarM', height_lidar_m,
          'heightLidarMethod', height_lidar_method,
          'heightLidarConfidence', height_lidar_confidence,
          'heightLidarStatus', height_lidar_status,
          'attributes', attributes,
          'source', jsonb_build_object(
            'table', 'zoning.v_charlottetown_buildings',
            'spatialFeatureId', spatial_feature_id,
            'featureKey', feature_key
          )
        )
      ) AS feature
      FROM source
    )
    SELECT jsonb_build_object(
      'type', 'FeatureCollection',
      'features', COALESCE(jsonb_agg(feature), '[]'::jsonb),
      'metadata', jsonb_build_object(
        'source', 'zoning.v_charlottetown_buildings',
        'limit', $1,
        'detail', $${params.length + 1}::text
      )
    ) AS geojson
    FROM features
    `,
    [...params, filters.detail || "detail"],
  );
  return rows[0]?.geojson || {
    type: "FeatureCollection",
    features: [],
    metadata: { source: "zoning.v_charlottetown_buildings", limit },
  };
}

function normalizeRadius(value, fallback = 250, max = 1000) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return Math.min(Math.trunc(parsed), max);
}

function finiteNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function percentileNumber(values, p) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const index = (sorted.length - 1) * p;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
}

async function loadJsonFile(filePath, fallback = null) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

async function loadTerrainPatch(center, radiusM) {
  const x = finiteNumber(center?.x);
  const y = finiteNumber(center?.y);
  if (x === null || y === null) {
    return {
      available: false,
      status: "fallback_flat",
      reason: "Parcel centroid in EPSG:2961 was not available.",
    };
  }

  const sampleCount = 41;
  const halfSizeM = Math.min(Math.max(radiusM, 120), 350);
  const qa = await loadJsonFile(terrainQaSummaryPath, {});
  try {
    const { stdout } = await execFileAsync(
      gdalTranslatePath,
      [
        "-q",
        "-of",
        "XYZ",
        "-outsize",
        String(sampleCount),
        String(sampleCount),
        "-projwin",
        String(x - halfSizeM),
        String(y + halfSizeM),
        String(x + halfSizeM),
        String(y - halfSizeM),
        terrainDemPath,
        "/vsistdout/",
      ],
      {
        cwd: repoRoot,
        maxBuffer: 1024 * 1024 * 4,
        env: {
          ...process.env,
          ...(process.platform === "win32"
            ? {
                PROJ_LIB: process.env.PROJ_LIB || "C:\\Program Files\\GDAL\\projlib",
                GDAL_DATA: process.env.GDAL_DATA || "C:\\Program Files\\GDAL\\gdal-data",
              }
            : {}),
        },
      },
    );
    const cells = stdout
      .trim()
      .split(/\r?\n/)
      .map((line) => {
        const [rawX, rawY, rawZ] = line.trim().split(/\s+/).map(Number);
        const z = Number.isFinite(rawZ) && rawZ > -9000 ? rawZ : null;
        return { x: rawX, y: rawY, z };
      })
      .filter((cell) => Number.isFinite(cell.x) && Number.isFinite(cell.y));
    const validElevations = cells.map((cell) => cell.z).filter((z) => z !== null);
    if (cells.length !== sampleCount * sampleCount || validElevations.length === 0) {
      return {
        available: false,
        status: "fallback_flat",
        reason: "DEM sampling returned no valid terrain cells for this parcel context.",
        qa,
      };
    }
    const baseElevationM = percentileNumber(validElevations, 0.5);
    return {
      available: true,
      status: "demo_terrain",
      method: "gdal_translate_xyz_sampled_from_epsg2961_dem",
      source: path.relative(repoRoot, terrainDemPath),
      horizontalCrs: "EPSG:2961",
      verticalDatum: "unresolved_source_lidar_vertical_datum",
      usage: "demo_visualization_only",
      warning: "Demo terrain only. Do not use for authoritative terrain, flood, tidal, storm-surge, engineering, regulatory, or parcel-specific risk decisions.",
      cols: sampleCount,
      rows: sampleCount,
      radiusM: halfSizeM,
      center: { x, y },
      baseElevationM: Number(baseElevationM.toFixed(3)),
      validCellRatio: Number((validElevations.length / cells.length).toFixed(4)),
      refinedLandCoverageRatio: qa?.refined_land_coverage_ratio ?? null,
      values: cells.map((cell) => (cell.z === null ? null : Number((cell.z - baseElevationM).toFixed(3)))),
    };
  } catch (error) {
    return {
      available: false,
      status: "fallback_flat",
      reason: `DEM sampling failed: ${error.message}`,
      qa,
    };
  }
}

async function loadParcel3dContext(pid, radiusM = 250) {
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
      SELECT p.spatial_feature_id, p.feature_key, p.attributes, p.is_valid, p.validation_reason, p.geom
      FROM selected_address a
      JOIN zoning.v_charlottetown_parcel_map p
        ON ST_Covers(p.geom, a.geom)
      ORDER BY ST_Area(p.geom), p.spatial_feature_id
      LIMIT 1
    ),
    context_extent AS (
      SELECT ST_Buffer(geom, $2) AS geom FROM selected_parcel
    ),
    adjacent_parcels AS (
      SELECT
        n.spatial_feature_id,
        n.feature_key,
        n.attributes,
        n.is_valid,
        n.validation_reason,
        n.geom
      FROM selected_parcel p
      JOIN zoning.v_charlottetown_parcel_map n
        ON n.spatial_feature_id <> p.spatial_feature_id
       AND n.geom && ST_Buffer(p.geom, 1)
       AND ST_DWithin(n.geom, p.geom, 1)
      ORDER BY ST_Distance(ST_Centroid(n.geom), ST_Centroid(p.geom)), n.spatial_feature_id
      LIMIT 80
    ),
    context_parcel_candidates AS (
      SELECT
        n.spatial_feature_id,
        n.feature_key,
        n.attributes,
        CASE
          WHEN EXISTS (SELECT 1 FROM adjacent_parcels a WHERE a.spatial_feature_id = n.spatial_feature_id)
            THEN 'adjacent'
          ELSE 'context'
        END AS relation,
        n.geom
      FROM zoning.v_charlottetown_parcel_map n
      JOIN context_extent e
        ON n.geom && e.geom
       AND ST_Intersects(n.geom, e.geom)
      WHERE NOT EXISTS (SELECT 1 FROM selected_parcel p WHERE p.spatial_feature_id = n.spatial_feature_id)
      ORDER BY ST_Distance(ST_Centroid(n.geom), (SELECT ST_Centroid(geom) FROM selected_parcel)), n.spatial_feature_id
      LIMIT 500
    ),
    context_parcels AS (
      SELECT
        p.spatial_feature_id,
        p.feature_key,
        p.attributes,
        'selected' AS relation,
        p.geom
      FROM selected_parcel p
      UNION ALL
      SELECT spatial_feature_id, feature_key, attributes, relation, geom
      FROM context_parcel_candidates
    ),
    selected_buildings AS (
      SELECT DISTINCT ON (b.spatial_feature_id)
        b.spatial_feature_id,
        b.feature_key,
        b.building,
        b.name,
        b.levels,
        b.height_lidar_m,
        b.height_lidar_confidence,
        b.height_lidar_status,
        CASE
          WHEN EXISTS (
            SELECT 1 FROM selected_parcel p
            WHERE ST_Intersects(b.geom, p.geom)
          ) THEN 'selected'
          WHEN EXISTS (
            SELECT 1 FROM adjacent_parcels p
            WHERE ST_Intersects(b.geom, p.geom)
          ) THEN 'adjacent'
          ELSE 'context'
        END AS relation,
        b.geom
      FROM context_extent e
      JOIN zoning.v_charlottetown_buildings b
        ON b.geom && e.geom
       AND ST_Intersects(b.geom, e.geom)
      ORDER BY b.spatial_feature_id
      LIMIT 1000
    ),
    roads AS (
      SELECT
        r.spatial_feature_id,
        r.feature_key,
        r.attributes,
        r.geom
      FROM context_extent e
      JOIN zoning.v_charlottetown_street_network r
        ON r.geom && e.geom
       AND ST_Intersects(r.geom, e.geom)
      ORDER BY r.spatial_feature_id
      LIMIT 250
    ),
    parcel_features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(ST_Multi(ST_CollectionExtract(ST_Intersection(geom, (SELECT geom FROM context_extent)), 3)), 4326))::jsonb,
        'properties', jsonb_build_object(
          'kind', 'parcel',
          'parcelId', feature_key,
          'relation', relation,
          'areaM2', ST_Area(geom),
          'attributes', attributes
        )
      ) AS feature
      FROM context_parcels
    ),
    building_features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(ST_Multi(ST_CollectionExtract(ST_Intersection(geom, (SELECT geom FROM context_extent)), 3)), 4326))::jsonb,
        'properties', jsonb_build_object(
          'kind', 'building',
          'relation', relation,
          'building', building,
          'name', name,
          'levels', levels,
          'heightLidarM', height_lidar_m,
          'heightLidarConfidence', height_lidar_confidence,
          'heightLidarStatus', height_lidar_status,
          'featureKey', feature_key
        )
      ) AS feature
      FROM selected_buildings
    ),
    road_features AS (
      SELECT jsonb_build_object(
        'type', 'Feature',
        'id', feature_key,
        'geometry', ST_AsGeoJSON(ST_Transform(ST_Multi(ST_CollectionExtract(ST_Intersection(geom, (SELECT geom FROM context_extent)), 2)), 4326))::jsonb,
        'properties', jsonb_build_object(
          'kind', 'road',
          'name', COALESCE(attributes->>'name', attributes->>'STREET_NM', attributes->>'NAME'),
          'featureKey', feature_key
        )
      ) AS feature
      FROM roads
    )
    SELECT jsonb_build_object(
      'address', (
        SELECT jsonb_build_object(
          'spatial_feature_id', spatial_feature_id,
          'feature_key', feature_key,
          'address_id', feature_key,
          'label', concat_ws(
            ', ',
            concat_ws(' ', street_number, street_name, CASE WHEN unit IS NOT NULL THEN 'Unit ' || unit END),
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
          'parcelId', feature_key,
          'areaM2', ST_Area(geom),
          'centroid', jsonb_build_object(
            'lon', ST_X(ST_Transform(ST_Centroid(geom), 4326)),
            'lat', ST_Y(ST_Transform(ST_Centroid(geom), 4326))
          ),
          'sourceCentroid2961', jsonb_build_object(
            'x', ST_X(ST_Transform(ST_Centroid(geom), 2961)),
            'y', ST_Y(ST_Transform(ST_Centroid(geom), 2961))
          ),
          'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb
        )
        FROM selected_parcel
      ),
      'parcels', jsonb_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE((SELECT jsonb_agg(feature) FROM parcel_features), '[]'::jsonb)
      ),
      'buildings', jsonb_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE((SELECT jsonb_agg(feature) FROM building_features), '[]'::jsonb)
      ),
      'roads', jsonb_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE((SELECT jsonb_agg(feature) FROM road_features), '[]'::jsonb)
      )
    ) AS payload
    `,
    [pid, radiusM],
  );

  const payload = rows[0]?.payload;
  if (!payload?.address || !payload?.parcel) {
    return null;
  }
  const terrain = await loadTerrainPatch(payload.parcel.sourceCentroid2961, radiusM);

  return {
    pid,
    address: mapAddressRow({ ...payload.address, confidence: "pid" }),
    parcel: payload.parcel,
    parcels: payload.parcels,
    buildings: payload.buildings,
    roads: payload.roads,
    terrain,
    metadata: {
      source: "PostGIS parcel, building, and street context",
      radiusM,
      radiusReason: `${radiusM} m radius provides road and parcel context around the target while keeping browser geometry modest for the static demo.`,
      buildingScope: "Buildings are limited to the same context radius used for parcel and road visibility.",
      geometrySrid: 4326,
      terrainStatus: terrain.status,
      terrainUsage: terrain.usage || "fallback_flat",
    },
  };
}

async function loadCityViewZoneFilters(currentZone, draftZone) {
  const currentSql = draftZone
    ? `
      SELECT DISTINCT current_zone_code AS code
      FROM zoning.v_charlottetown_parcel_zone_assignment
      WHERE draft_zone_code = $1
        AND current_zone_code IS NOT NULL
      ORDER BY code
    `
    : `
      SELECT DISTINCT current_zone_code AS code
      FROM zoning.v_charlottetown_parcel_zone_assignment
      WHERE current_zone_code IS NOT NULL
      ORDER BY code
    `;
  const draftSql = currentZone
    ? `
      SELECT DISTINCT draft_zone_code AS code
      FROM zoning.v_charlottetown_parcel_zone_assignment
      WHERE current_zone_code = $1
        AND draft_zone_code IS NOT NULL
      ORDER BY code
    `
    : `
      SELECT DISTINCT draft_zone_code AS code
      FROM zoning.v_charlottetown_parcel_zone_assignment
      WHERE draft_zone_code IS NOT NULL
      ORDER BY code
    `;
  const [currentResult, draftResult] = await Promise.all([
    pool.query(currentSql, draftZone ? [draftZone] : []),
    pool.query(draftSql, currentZone ? [currentZone] : []),
  ]);
  return {
    filters: {
      currentZone: currentZone || null,
      draftZone: draftZone || null,
    },
    options: {
      current: currentResult.rows.map((row) => row.code),
      draft: draftResult.rows.map((row) => row.code),
    },
    source: "zoning.v_charlottetown_parcel_zone_assignment",
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
        (
          SELECT bp.part_title_raw
          FROM zoning.section s
          JOIN zoning.bylaw_part bp
            ON bp.bylaw_part_id = s.bylaw_part_id
          JOIN zoning.source_file sf
            ON sf.source_file_id = s.source_file_id
          WHERE s.is_active
            AND s.document_type = 'zone'
            AND s.zone_code = COALESCE(z.bylaw_zone_code, z.zone_code_normalized, z.zone_code_raw, z."ZONING")
            AND sf.repo_relpath LIKE 'data/zoning/charlottetown/%'
          ORDER BY s.source_order, s.section_id
          LIMIT 1
        ) AS zone_name,
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
      current: (() => {
        const zone = mapZoneRow(payload.current_zone);
        if (zone) {
          zone.name = zoneNameFromPartTitle(zone.name, zone.bylawZoneCode || zone.normalizedCode || zone.code);
        }
        return zone;
      })(),
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
  ["/parcel-3d", { file: "/ui_kits/parcel-3d/index.html", baseHref: "/ui_kits/parcel-3d/" }],
  ["/parcel-3d/", { file: "/ui_kits/parcel-3d/index.html", baseHref: "/ui_kits/parcel-3d/" }],
  ["/storm-surge", { file: "/ui_kits/storm-surge/index.html", baseHref: "/ui_kits/storm-surge/" }],
  ["/storm-surge/", { file: "/ui_kits/storm-surge/index.html", baseHref: "/ui_kits/storm-surge/" }],
  ["/council-meetings", { file: "/ui_kits/council-meetings/index.html", baseHref: "/ui_kits/council-meetings/" }],
  ["/council-meetings/", { file: "/ui_kits/council-meetings/index.html", baseHref: "/ui_kits/council-meetings/" }],
  ["/rezoning-parcel-lookup", { file: "/ui_kits/rezoning-parcel-lookup/index.html", baseHref: "/ui_kits/rezoning-parcel-lookup/" }],
  ["/rezoning-parcel-lookup/", { file: "/ui_kits/rezoning-parcel-lookup/index.html", baseHref: "/ui_kits/rezoning-parcel-lookup/" }],
  ["/rezoning-zoning-comparison", { file: "/ui_kits/rezoning-zoning-comparison/index.html", baseHref: "/ui_kits/rezoning-zoning-comparison/" }],
  ["/rezoning-zoning-comparison/", { file: "/ui_kits/rezoning-zoning-comparison/index.html", baseHref: "/ui_kits/rezoning-zoning-comparison/" }],
  ["/rezoning-restriction-stack", { file: "/ui_kits/rezoning-restriction-stack/index.html", baseHref: "/ui_kits/rezoning-restriction-stack/" }],
  ["/rezoning-restriction-stack/", { file: "/ui_kits/rezoning-restriction-stack/index.html", baseHref: "/ui_kits/rezoning-restriction-stack/" }],
  ["/rezoning-storm-surge", { file: "/ui_kits/rezoning-storm-surge/index.html", baseHref: "/ui_kits/rezoning-storm-surge/" }],
  ["/rezoning-storm-surge/", { file: "/ui_kits/rezoning-storm-surge/index.html", baseHref: "/ui_kits/rezoning-storm-surge/" }],
  ["/restriction-stack", { file: "/ui_kits/restriction-stack/index.html", baseHref: "/ui_kits/restriction-stack/" }],
  ["/restriction-stack/", { file: "/ui_kits/restriction-stack/index.html", baseHref: "/ui_kits/restriction-stack/" }],
  ["/city-view", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/city-view/", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/map", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/map/", { file: "/ui_kits/map-explorer-leaflet/index.html", baseHref: "/ui_kits/map-explorer-leaflet/" }],
  ["/zoning-comparison", { file: "/ui_kits/zoning-comparison/index.html", baseHref: "/ui_kits/zoning-comparison/" }],
  ["/zoning-comparison/", { file: "/ui_kits/zoning-comparison/index.html", baseHref: "/ui_kits/zoning-comparison/" }],
  ["/provisions-comparison", { file: "/ui_kits/provisions-comparison/index.html", baseHref: "/ui_kits/provisions-comparison/" }],
  ["/provisions-comparison/", { file: "/ui_kits/provisions-comparison/index.html", baseHref: "/ui_kits/provisions-comparison/" }],
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

    if (url.pathname === "/api/council-meetings/current") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      await sendJson(response, await loadCouncilMeeting());
      return;
    }

    if (url.pathname === "/api/council-meetings/current/source-page") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      await sendJson(response, await loadCouncilMeetingSourcePage(
        url.searchParams.get("documentId") || "",
        url.searchParams.get("page") || "",
      ));
      return;
    }

    if (url.pathname === "/api/council-meetings/current/page-image") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const body = await loadCouncilMeetingPageImage(
        url.searchParams.get("documentId") || "",
        url.searchParams.get("page") || "",
      );
      response.writeHead(200, { "content-type": "image/png" });
      response.end(body);
      return;
    }

    const councilItemMatch = url.pathname.match(/^\/api\/council-meetings\/current\/items\/([^/]+)\/(parcels|comparison|restriction-stack|3d-context)$/);
    if (councilItemMatch) {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const itemId = decodeURIComponent(councilItemMatch[1]).trim();
      const resource = councilItemMatch[2];
      const payload = resource === "parcels"
        ? await loadCouncilMeetingItemParcels(itemId)
        : resource === "comparison"
          ? await loadCouncilMeetingItemComparison(itemId)
          : resource === "restriction-stack"
            ? await loadCouncilMeetingItemRestrictionStack(itemId)
            : await loadCouncilMeetingItem3dContext(itemId, normalizeRadius(url.searchParams.get("radiusM")));
      if (!payload) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "Council meeting item resource not found.", itemId, resource }));
        return;
      }
      await sendJson(response, payload);
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
      const limit = normalizeLimit(url.searchParams.get("limit"), 1000, 50000);
      await sendGeoJson(response, await loadParcelGeoJson(bbox, limit, {
        currentZone: normalizeZoneFilter(url.searchParams.get("currentZone")),
        draftZone: normalizeZoneFilter(url.searchParams.get("draftZone")),
        detail: normalizeDetail(url.searchParams.get("detail")),
      }));
      return;
    }

    if (url.pathname === "/api/zoning/current.geojson") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const bbox = parseBbox(url.searchParams.get("bbox"));
      const limit = normalizeLimit(url.searchParams.get("limit"), 1000, 50000);
      await sendGeoJson(response, await loadCurrentZoningGeoJson(bbox, limit, {
        zone: normalizeZoneFilter(url.searchParams.get("zone")),
        detail: normalizeDetail(url.searchParams.get("detail")),
      }));
      return;
    }

    if (url.pathname === "/api/zoning/draft.geojson") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const bbox = parseBbox(url.searchParams.get("bbox"));
      const limit = normalizeLimit(url.searchParams.get("limit"), 1000, 50000);
      await sendGeoJson(response, await loadDraftZoningGeoJson(bbox, limit, {
        zone: normalizeZoneFilter(url.searchParams.get("zone")),
        detail: normalizeDetail(url.searchParams.get("detail")),
      }));
      return;
    }

    if (url.pathname === "/api/buildings/osm.geojson") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const bbox = parseBbox(url.searchParams.get("bbox"));
      const limit = normalizeLimit(url.searchParams.get("limit"), 2000, 50000);
      await sendGeoJson(response, await loadBuildingsGeoJson(bbox, limit, {
        detail: normalizeDetail(url.searchParams.get("detail")),
      }));
      return;
    }

    if (url.pathname === "/api/city-view/zone-filters") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      await sendJson(response, await loadCityViewZoneFilters(
        normalizeZoneFilter(url.searchParams.get("currentZone")),
        normalizeZoneFilter(url.searchParams.get("draftZone")),
      ));
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

    if (url.pathname === "/api/provisions-comparison") {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      await sendJson(response, await loadProvisionsComparison());
      return;
    }

    const restrictionBuffersMatch = url.pathname.match(/^\/api\/parcels\/([^/]+)\/restriction-buffers$/);
    if (restrictionBuffersMatch) {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const pid = decodeURIComponent(restrictionBuffersMatch[1]).trim();
      const buffers = await loadParcelRestrictionBuffers(pid);
      if (!buffers) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "Parcel PID not found.", pid }));
        return;
      }
      await sendJson(response, buffers);
      return;
    }

    const parcel3dMatch = url.pathname.match(/^\/api\/parcels\/([^/]+)\/3d-context$/);
    if (parcel3dMatch) {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const pid = decodeURIComponent(parcel3dMatch[1]).trim();
      const radiusM = normalizeRadius(url.searchParams.get("radiusM"));
      const context = await loadParcel3dContext(pid, radiusM);
      if (!context) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "Parcel PID not found.", pid }));
        return;
      }
      await sendJson(response, context);
      return;
    }

    const restrictionStackMatch = url.pathname.match(/^\/api\/parcels\/([^/]+)\/restriction-stack$/);
    if (restrictionStackMatch) {
      if (request.method !== "GET") {
        response.writeHead(405);
        response.end("Method not allowed");
        return;
      }
      const pid = decodeURIComponent(restrictionStackMatch[1]).trim();
      const stack = await loadParcelRestrictionStack(pid);
      if (!stack) {
        response.writeHead(404, { "content-type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ error: "Parcel PID not found.", pid }));
        return;
      }
      await sendJson(response, stack);
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
