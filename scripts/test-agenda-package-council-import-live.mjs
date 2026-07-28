#!/usr/bin/env node

import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pg from "../web/node_modules/pg/lib/index.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { Client } = pg;
const databaseConfig = {
  host: process.env.PGHOST || "127.0.0.1",
  port: Number(process.env.PGPORT || "54329"),
  database: process.env.PGDATABASE || "mdopendata",
  user: process.env.PGUSER || "mdopendata",
  password: process.env.PGPASSWORD || "mdopendata_dev",
};
const positivePackageKey = "agenda-package-73d48c77694d443e5351089c";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function availablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

async function waitForServer(baseUrl, child) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (child.exitCode !== null) throw new Error(`Server exited with ${child.exitCode}.`);
    try {
      const response = await fetch(`${baseUrl}/healthz`);
      if (response.ok) return;
    } catch {
      // Continue until the bounded startup deadline.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Server did not start.");
}

async function stopServer(child) {
  if (child.exitCode !== null) return;
  child.kill();
  await Promise.race([
    new Promise((resolve) => child.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

async function permanentFingerprint(client) {
  const { rows } = await client.query(`
    SELECT jsonb_build_object(
      'meetings', (SELECT jsonb_agg(to_jsonb(t) ORDER BY meeting_id) FROM council.meeting t),
      'agenda_items', (SELECT jsonb_agg(to_jsonb(t) ORDER BY agenda_item_id) FROM council.agenda_item t),
      'source_documents', (SELECT jsonb_agg(to_jsonb(t) ORDER BY source_document_id) FROM council.source_document t),
      'package_documents', (SELECT jsonb_agg(to_jsonb(t) ORDER BY package_document_id) FROM council.package_document t),
      'import_batches', (SELECT jsonb_agg(to_jsonb(t) ORDER BY import_batch_id) FROM council.import_batch t),
      'import_events', (SELECT jsonb_agg(to_jsonb(t) ORDER BY import_record_event_id) FROM council.import_record_event t)
    )::text AS fingerprint
  `);
  return rows[0].fingerprint;
}

async function createFixture(client, suffix) {
  const packageKey = `agenda-package-council-import-${suffix}`;
  const meetingKey = `charlottetown-live-council-import-${suffix}`;
  await client.query("BEGIN");
  try {
  const { rows: sourceRows } = await client.query(`
    INSERT INTO documents.source_document (
      ingest_batch_id, source_document_key, jurisdiction_key,
      jurisdiction_name_raw, municipality_raw, province, country,
      document_family_key, document_type_key, title_raw, repo_relpath,
      source_url, mime_type, page_count, source_file_hash, published_date,
      acquired_at, metadata, natural_key, content_hash
    )
    SELECT ingest_batch_id, $2, jurisdiction_key,
      jurisdiction_name_raw, municipality_raw, province, country,
      document_family_key, document_type_key, title_raw || ' [council import verification]',
      repo_relpath, source_url, mime_type, page_count, source_file_hash,
      published_date, acquired_at,
      metadata || jsonb_build_object('verification_scope', 'ephemeral-council-import'),
      'documents:source-document:' || $2, content_hash
    FROM documents.source_document
    WHERE source_document_key = $1 AND is_active
    RETURNING source_document_id
  `, [positivePackageKey, packageKey]);
  const sourceDocumentId = sourceRows[0].source_document_id;
  const { rows: extractionRows } = await client.query(`
    INSERT INTO documents.package_extraction (
      source_document_id, extraction_status, agenda_document_key,
      unresolved_template_count, result_json, pipeline_version, diagnostics,
      natural_key, content_hash, completed_at
    )
    SELECT $2, pe.extraction_status, pe.agenda_document_key,
      pe.unresolved_template_count, pe.result_json, pe.pipeline_version,
      pe.diagnostics || jsonb_build_object('verification_scope', 'ephemeral-council-import'),
      'documents:package-extraction:' || $3 || ':1', pe.content_hash, pe.completed_at
    FROM documents.package_extraction pe
    JOIN documents.source_document sd USING (source_document_id)
    WHERE sd.source_document_key = $1 AND sd.is_active AND pe.is_active
    RETURNING package_extraction_id
  `, [positivePackageKey, sourceDocumentId, packageKey]);
  const packageExtractionId = extractionRows[0].package_extraction_id;
  await client.query(`
    INSERT INTO documents.package_document_assembly (
      source_document_id, document_key, document_order, title, page_start,
      page_end, is_agenda, primary_agenda_item_key, page_template_keys,
      assembly_rule, status, natural_key, content_hash, approved_at
    )
    SELECT $2, pda.document_key, pda.document_order, pda.title, pda.page_start,
      pda.page_end, pda.is_agenda, pda.primary_agenda_item_key,
      pda.page_template_keys, pda.assembly_rule, 'approved',
      'documents:package-assembly:' || $3 || ':' || pda.document_key,
      pda.content_hash, now()
    FROM documents.package_document_assembly pda
    JOIN documents.source_document sd USING (source_document_id)
    WHERE sd.source_document_key = $1 AND sd.is_active
      AND pda.is_active AND pda.status = 'approved'
    ORDER BY pda.document_order
  `, [positivePackageKey, sourceDocumentId, packageKey]);
  await client.query(`
    INSERT INTO documents.package_extracted_document (
      package_extraction_id, document_key, document_role, source_order,
      primary_agenda_item_key, document_type_key, title_raw, page_numbers,
      page_template_keys, content_json, provenance, natural_key, content_hash
    )
    SELECT $2, ped.document_key, ped.document_role, ped.source_order,
      ped.primary_agenda_item_key, ped.document_type_key, ped.title_raw,
      ped.page_numbers, ped.page_template_keys, ped.content_json,
      ped.provenance || jsonb_build_object('verification_scope', 'ephemeral-council-import'),
      'documents:package-extracted-document:' || $3 || ':' || ped.document_key,
      ped.content_hash
    FROM documents.package_extracted_document ped
    JOIN documents.package_extraction pe USING (package_extraction_id)
    JOIN documents.source_document sd USING (source_document_id)
    WHERE sd.source_document_key = $1 AND sd.is_active
      AND pe.is_active AND ped.is_active
    ORDER BY ped.source_order
  `, [positivePackageKey, packageExtractionId, packageKey]);
  const { rows: meetingRows } = await client.query(`
    INSERT INTO council.meeting (
      jurisdiction_id, body_id, meeting_key, meeting_type, title_raw,
      meeting_date, meeting_time_raw, location_raw, meeting_status,
      metadata, natural_key, content_hash
    )
    SELECT m.jurisdiction_id, m.body_id, $2, 'public_meeting',
      'Public Meeting of Council [live import verification]',
      DATE '2026-02-03', '6:00 PM',
      'Council Chambers, City Hall, 199 Queen Street', 'scheduled',
      '{"verification_scope":"ephemeral-council-import"}'::jsonb,
      'council:meeting:' || $2, repeat('1', 64)
    FROM council.meeting m
    WHERE m.meeting_key = $1 AND m.is_active
    LIMIT 1
    RETURNING meeting_id
  `, ["charlottetown-2026-05-12-regular-council", meetingKey]);
  const meetingId = meetingRows[0].meeting_id;
  const { rows: businessRows } = await client.query(`
    SELECT business_item_id
    FROM council.business_item
    WHERE is_active
    ORDER BY business_item_id
    LIMIT 1
  `);
  assert(businessRows.length === 1, "Live control requires one active council business item.");
  const businessItemId = businessRows[0].business_item_id;
  await client.query(`
    INSERT INTO council.agenda_item (
      meeting_id, business_item_id, agenda_item_key, item_number_raw, item_type, title_raw,
      source_order, metadata, natural_key, content_hash
    ) VALUES (
      $1, $3, 'bia-hearing', '4(a)', 'public_hearing',
      'Proposal to establish a Business Improvement Area',
      1, '{"verification_scope":"ephemeral-council-import"}'::jsonb,
      'council:agenda-item:' || $2 || ':bia-hearing', repeat('2', 64)
    )
  `, [meetingId, meetingKey, businessItemId]);
  await client.query("COMMIT");
  return {
    packageKey,
    sourceDocumentId,
    packageExtractionId,
    meetingKey,
    meetingId,
    businessItemId,
  };
  } catch (error) {
    await client.query("ROLLBACK").catch(() => {});
    throw error;
  }
}

async function councilBindings(baseUrl, packageKey, meetingKey = "") {
  const query = meetingKey ? `?meetingKey=${encodeURIComponent(meetingKey)}` : "";
  const response = await fetch(
    `${baseUrl}/api/document-ingestion/packages/${packageKey}/council-import${query}`,
  );
  const payload = await response.json();
  assert(response.ok, `Binding preview returned ${response.status}: ${JSON.stringify(payload)}`);
  return payload;
}

async function councilImport(baseUrl, packageKey, meetingKey) {
  const response = await fetch(
    `${baseUrl}/api/document-ingestion/packages/${packageKey}/council-import`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ meetingKey }),
    },
  );
  const payload = await response.json();
  assert(response.ok, `Council import returned ${response.status}: ${JSON.stringify(payload)}`);
  return payload;
}

async function blockedCouncilImport(baseUrl, packageKey, meetingKey) {
  const response = await fetch(
    `${baseUrl}/api/document-ingestion/packages/${packageKey}/council-import`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ meetingKey }),
    },
  );
  const payload = await response.json();
  assert(
    response.status === 409 && payload.error?.includes("agenda-item-resolution-incomplete"),
    `Blocked council import returned ${response.status}: ${JSON.stringify(payload)}`,
  );
}

const client = new Client(databaseConfig);
await client.connect();
await client.query(`
  DELETE FROM council.meeting
  WHERE metadata->>'verification_scope' = 'ephemeral-council-import'
`);
await client.query(`
  DELETE FROM council.source_document
  WHERE metadata->>'verification_scope' = 'ephemeral-council-import'
     OR metadata->>'documents_source_document_id' IN (
       SELECT source_document_id::text
       FROM documents.source_document
       WHERE metadata->>'verification_scope' = 'ephemeral-council-import'
     )
`);
await client.query(`
  DELETE FROM council.import_batch
  WHERE diagnostics->>'package_key' LIKE 'agenda-package-council-import-%'
`);
await client.query(`
  DELETE FROM documents.source_document
  WHERE metadata->>'verification_scope' = 'ephemeral-council-import'
`);
const before = await permanentFingerprint(client);
const suffix = randomUUID().replaceAll("-", "").slice(0, 16);
let fixture = null;
const port = await availablePort();
const child = spawn(process.execPath, ["web/server.js"], {
  cwd: root,
  env: {
    ...process.env,
    REPO_ROOT: root,
    HOST: "127.0.0.1",
    PORT: String(port),
    PGHOST: databaseConfig.host,
    PGPORT: String(databaseConfig.port),
    PGDATABASE: databaseConfig.database,
    PGUSER: databaseConfig.user,
    PGPASSWORD: databaseConfig.password,
  },
  stdio: ["ignore", "pipe", "pipe"],
  windowsHide: true,
});
let diagnostics = "";
child.stdout.on("data", (chunk) => { diagnostics += chunk.toString(); });
child.stderr.on("data", (chunk) => { diagnostics += chunk.toString(); });
const baseUrl = `http://127.0.0.1:${port}`;

try {
  await waitForServer(baseUrl, child);
  fixture = await createFixture(client, suffix);
  const unselected = await councilBindings(baseUrl, fixture.packageKey);
  assert(
    !unselected.ready && unselected.reasonCodes.includes("meeting-required"),
    `Meeting selection gate failed: ${JSON.stringify(unselected)}`,
  );
  const missing = await councilBindings(
    baseUrl,
    fixture.packageKey,
    "charlottetown-2026-05-12-regular-council",
  );
  assert(
    !missing.ready
      && missing.missingAgendaItemKeys.length === 1
      && missing.missingAgendaItemKeys[0] === "bia-hearing",
    "Missing agenda-item control did not block.",
  );
  await blockedCouncilImport(
    baseUrl,
    fixture.packageKey,
    "charlottetown-2026-05-12-regular-council",
  );
  const { rows: blockedWriteRows } = await client.query(`
    SELECT
      (SELECT count(*) FROM council.package_document
       WHERE metadata->>'documents_source_document_key' = $1)::integer
        AS package_documents,
      (SELECT count(*) FROM council.import_batch
       WHERE diagnostics->>'package_key' = $1)::integer
        AS import_batches
  `, [fixture.packageKey]);
  assert(
    blockedWriteRows[0].package_documents === 0
      && blockedWriteRows[0].import_batches === 0,
    "Blocked agenda-item resolution created council rows.",
  );
  const ready = await councilBindings(baseUrl, fixture.packageKey, fixture.meetingKey);
  assert(ready.ready && ready.documents.length === 5, "Exact agenda-item binding preview failed.");
  assert(
    ready.documents.filter((document) => document.documentRole !== "agenda")
      .every((document) => document.resolvedAgendaItemId),
    "Supporting documents did not resolve.",
  );
  assert(
    ready.documents.find((document) => document.documentRole === "agenda")
      ?.resolvedAgendaItemId === null,
    "Agenda document was incorrectly bound.",
  );
  const first = await councilImport(baseUrl, fixture.packageKey, fixture.meetingKey);
  assert(first.diagnostics.added === 5, "First council import did not add five documents.");
  const { rows: importedRows } = await client.query(`
    SELECT pd.package_document_id, pd.package_document_key,
           pd.agenda_item_id, pd.business_item_id,
           pd.page_start, pd.page_end, pd.source_order, pd.is_active
    FROM council.package_document pd
    WHERE pd.meeting_id = $1 AND pd.is_active
    ORDER BY pd.source_order
  `, [fixture.meetingId]);
  assert(importedRows.length === 5, "Council package-document row count is incorrect.");
  assert(importedRows[0].agenda_item_id === null, "Imported agenda document was bound.");
  assert(
    importedRows.slice(1).every((document) => document.agenda_item_id !== null),
    "Imported supporting documents are not fully bound.",
  );
  assert(
    importedRows[0].business_item_id === null
      && importedRows.slice(1).every(
        (document) => document.business_item_id === fixture.businessItemId,
      ),
    "Council business-item inheritance is incorrect.",
  );
  assert(
    JSON.stringify(importedRows.map((document) => [document.page_start, document.page_end]))
      === JSON.stringify([[1, 1], [2, 2], [3, 3], [4, 4], [5, 6]]),
    "Imported council document ranges are incorrect.",
  );
  const activeIdsBefore = importedRows.map((row) => row.package_document_id).join("|");
  const second = await councilImport(baseUrl, fixture.packageKey, fixture.meetingKey);
  assert(
    second.diagnostics.added === 0
      && second.diagnostics.changed === 0
      && second.diagnostics.unchanged === 5,
    "Repeated council import was not idempotent.",
  );
  const { rows: rerunRows } = await client.query(`
    SELECT package_document_id, package_document_key
    FROM council.package_document
    WHERE meeting_id = $1 AND is_active
    ORDER BY source_order
  `, [fixture.meetingId]);
  assert(
    rerunRows.map((row) => row.package_document_id).join("|") === activeIdsBefore,
    "Repeated council import changed active document identity.",
  );
  const importedPreview = await councilBindings(baseUrl, fixture.packageKey, fixture.meetingKey);
  assert(
    importedPreview.importStatus === "completed"
      && importedPreview.importBatchId === second.importBatchId,
    "Imported binding preview did not expose the latest completed batch.",
  );
  console.log(JSON.stringify({
    bindingPreview: {
      documents: ready.documents.length,
      supportingDocumentsResolved: 4,
      agendaUnbound: true,
    },
    import: {
      packageDocuments: importedRows.length,
      pageRanges: importedRows.map((document) => [document.page_start, document.page_end]),
      firstRunAdded: first.diagnostics.added,
      rerunUnchanged: second.diagnostics.unchanged,
    },
    controls: {
      meetingRequired: true,
      missingAgendaItemBlocked: true,
    },
  }, null, 2));
} catch (error) {
  error.message = `${error.message}\n${diagnostics}`;
  throw error;
} finally {
  await stopServer(child);
  if (fixture) {
    await client.query("DELETE FROM council.meeting WHERE meeting_id = $1", [fixture.meetingId]);
    await client.query(
      "DELETE FROM council.source_document WHERE metadata->>'documents_source_document_id' = $1",
      [String(fixture.sourceDocumentId)],
    );
    await client.query(
      "DELETE FROM council.import_batch WHERE diagnostics->>'package_key' = $1",
      [fixture.packageKey],
    );
    await client.query(
      "DELETE FROM documents.source_document WHERE source_document_id = $1",
      [fixture.sourceDocumentId],
    );
  }
  const after = await permanentFingerprint(client);
  assert(after === before, "Permanent council rows changed during live verification.");
  const { rows: remaining } = await client.query(`
    SELECT
      (SELECT count(*) FROM documents.source_document
       WHERE metadata->>'verification_scope' = 'ephemeral-council-import')::integer
        AS document_sources,
      (SELECT count(*) FROM council.meeting
       WHERE metadata->>'verification_scope' = 'ephemeral-council-import')::integer
        AS council_meetings,
      (SELECT count(*) FROM council.source_document
       WHERE metadata->>'verification_scope' = 'ephemeral-council-import')::integer
        AS council_sources,
      (SELECT count(*) FROM council.import_batch
       WHERE diagnostics->>'package_key' LIKE 'agenda-package-council-import-%')::integer
        AS import_batches
  `);
  assert(
    remaining[0].document_sources === 0
      && remaining[0].council_meetings === 0
      && remaining[0].council_sources === 0
      && remaining[0].import_batches === 0,
    "Ephemeral council-import rows remain.",
  );
  await client.end();
}
