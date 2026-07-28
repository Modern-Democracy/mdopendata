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
const negativePackageKey = "agenda-package-d529b04147218eaf379ab063";

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
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (child.exitCode !== null) {
      throw new Error(`Server exited with ${child.exitCode}.`);
    }
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

async function preview(baseUrl, packageKey) {
  const response = await fetch(
    `${baseUrl}/api/document-ingestion/packages/${packageKey}/reuse-preview`,
    { method: "POST" },
  );
  const payload = await response.json();
  assert(
    response.ok,
    `${packageKey} returned ${response.status}: ${JSON.stringify(payload)}`,
  );
  return payload;
}

async function blockedHandoff(baseUrl, packageKey, expectedMessage) {
  const response = await fetch(
    `${baseUrl}/api/document-ingestion/packages/${packageKey}/reuse-preview/assembly-plan`,
    { method: "POST" },
  );
  const payload = await response.json();
  assert(response.status === 409, `${packageKey} handoff returned ${response.status}.`);
  assert(payload.error === expectedMessage, `${packageKey} handoff error is incorrect.`);
}

async function controlFingerprint(client) {
  const { rows } = await client.query(`
    SELECT jsonb_build_object(
      'source_documents', (
        SELECT jsonb_agg(to_jsonb(sd) ORDER BY sd.source_document_id)
        FROM documents.source_document sd
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'package_extractions', (
        SELECT jsonb_agg(to_jsonb(pe) ORDER BY pe.package_extraction_id)
        FROM documents.package_extraction pe
        JOIN documents.source_document sd USING (source_document_id)
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'source_pages', (
        SELECT jsonb_agg(to_jsonb(sp) ORDER BY sp.source_page_id)
        FROM documents.source_page sp
        JOIN documents.source_document sd USING (source_document_id)
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'page_classifications', (
        SELECT jsonb_agg(to_jsonb(pc) ORDER BY pc.page_classification_id)
        FROM documents.page_classification pc
        JOIN documents.source_page sp USING (source_page_id)
        JOIN documents.source_document sd USING (source_document_id)
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'model_gaps', (
        SELECT jsonb_agg(to_jsonb(mg) ORDER BY mg.model_gap_id)
        FROM documents.model_gap mg
        JOIN documents.source_document sd USING (source_document_id)
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'assemblies', (
        SELECT jsonb_agg(to_jsonb(pda) ORDER BY pda.package_document_assembly_id)
        FROM documents.package_document_assembly pda
        JOIN documents.source_document sd USING (source_document_id)
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'extracted_documents', (
        SELECT jsonb_agg(to_jsonb(ped) ORDER BY ped.package_extracted_document_id)
        FROM documents.package_extracted_document ped
        JOIN documents.package_extraction pe USING (package_extraction_id)
        JOIN documents.source_document sd USING (source_document_id)
        WHERE sd.source_document_key = ANY($1::text[]) AND sd.is_active
      ),
      'council_package_document_count', (
        SELECT count(*) FROM council.package_document
      )
    )::text AS fingerprint
  `, [[positivePackageKey, negativePackageKey]]);
  return rows[0].fingerprint;
}

async function createEphemeralPositivePackage(client) {
  const suffix = randomUUID().replaceAll("-", "").slice(0, 16);
  const packageKey = `agenda-package-live-handoff-${suffix}`;
  const { rows } = await client.query(`
    WITH source AS (
      INSERT INTO documents.source_document (
        ingest_batch_id, source_document_key, jurisdiction_key,
        jurisdiction_name_raw, municipality_raw, province, country,
        document_family_key, document_type_key, title_raw, repo_relpath,
        source_url, mime_type, page_count, source_file_hash, published_date,
        acquired_at, metadata, natural_key, content_hash
      )
      SELECT ingest_batch_id, $2, jurisdiction_key,
        jurisdiction_name_raw, municipality_raw, province, country,
        document_family_key, document_type_key, title_raw || ' [live handoff verification]',
        repo_relpath, source_url, mime_type, page_count, source_file_hash,
        published_date, acquired_at,
        metadata || jsonb_build_object('verification_scope', 'ephemeral-live-handoff'),
        'documents:source-document:' || $2, content_hash
      FROM documents.source_document
      WHERE source_document_key = $1 AND is_active
      RETURNING source_document_id
    ), extraction AS (
      INSERT INTO documents.package_extraction (
        source_document_id, extraction_status, unresolved_template_count,
        pipeline_version, diagnostics, natural_key, content_hash
      )
      SELECT source_document_id, 'awaiting_template_approval', 6,
        'agenda-package-reuse-live-verification-v1',
        '{"verification_scope":"ephemeral-live-handoff"}'::jsonb,
        'documents:package-extraction:' || $2 || ':1',
        repeat('0', 64)
      FROM source
    )
    SELECT source_document_id FROM source
  `, [positivePackageKey, packageKey]);
  assert(rows.length === 1, "Ephemeral source document was not created.");
  const sourceDocumentId = rows[0].source_document_id;
  await client.query(`
    INSERT INTO documents.source_page (
      source_document_id, page_number, page_label_raw, source_locator,
      text_raw, text_extraction_status, width, height, render_dpi,
      metadata, natural_key, content_hash
    )
    SELECT $2, sp.page_number, sp.page_label_raw, $3 || '#page=' || sp.page_number,
      sp.text_raw, sp.text_extraction_status, sp.width, sp.height, sp.render_dpi,
      sp.metadata || jsonb_build_object('verification_scope', 'ephemeral-live-handoff'),
      'documents:source-page:' || $3 || ':' || sp.page_number,
      sp.content_hash
    FROM documents.source_page sp
    JOIN documents.source_document sd USING (source_document_id)
    WHERE sd.source_document_key = $1 AND sd.is_active AND sp.is_active
    ORDER BY page_number
  `, [positivePackageKey, sourceDocumentId, packageKey]);
  return { packageKey, sourceDocumentId };
}

async function verifySuccessfulHandoff(baseUrl, client, ephemeral) {
  const endpoint = `${baseUrl}/api/document-ingestion/packages/${ephemeral.packageKey}/reuse-preview/assembly-plan`;
  const firstResponse = await fetch(endpoint, { method: "POST" });
  const first = await firstResponse.json();
  assert(firstResponse.ok, `Successful handoff returned ${firstResponse.status}: ${JSON.stringify(first)}`);
  assert(first.status === "draft", "Successful handoff did not create a draft assembly.");
  assert(first.documents?.length === 5, "Successful handoff document count is incorrect.");
  assert(first.reuseHandoff?.reused === false, "First handoff was incorrectly reported as reused.");
  assert(
    JSON.stringify(first.documents.map((document) => [document.pageStart, document.pageEnd]))
      === JSON.stringify([[1, 1], [2, 2], [3, 3], [4, 4], [5, 6]]),
    "Successful handoff page ranges are incorrect.",
  );

  const { rows: stateRows } = await client.query(`
    SELECT
      pe.extraction_status,
      pe.unresolved_template_count,
      count(DISTINCT pc.page_classification_id)::integer AS classification_count,
      count(DISTINCT pc.page_classification_id) FILTER (
        WHERE pc.classification_source = 'reviewer'
          AND pc.review_status = 'accepted'
          AND pc.metadata->>'approved_action' = 'reuse_preview_handoff'
          AND pc.metadata->>'approved_profile_sha256' IS NOT NULL
      )::integer AS accepted_reuse_count,
      count(DISTINCT pda.package_document_assembly_id)::integer AS assembly_count,
      count(DISTINCT pda.package_document_assembly_id) FILTER (
        WHERE pda.status = 'draft'
          AND pda.primary_agenda_item_key IS NULL
          AND pda.assembly_rule->>'source' = 'approved_reuse_preview'
      )::integer AS draft_reuse_count,
      count(DISTINCT ped.package_extracted_document_id)::integer AS extracted_document_count
    FROM documents.source_document sd
    JOIN documents.package_extraction pe
      ON pe.source_document_id = sd.source_document_id AND pe.is_active
    LEFT JOIN documents.source_page sp
      ON sp.source_document_id = sd.source_document_id AND sp.is_active
    LEFT JOIN documents.page_classification pc
      ON pc.source_page_id = sp.source_page_id AND pc.is_active
    LEFT JOIN documents.package_document_assembly pda
      ON pda.source_document_id = sd.source_document_id AND pda.is_active
    LEFT JOIN documents.package_extracted_document ped
      ON ped.package_extraction_id = pe.package_extraction_id AND ped.is_active
    WHERE sd.source_document_id = $1 AND sd.is_active
    GROUP BY pe.package_extraction_id
  `, [ephemeral.sourceDocumentId]);
  const state = stateRows[0];
  assert(state.extraction_status === "awaiting_document_assembly", "Package state is incorrect after handoff.");
  assert(state.unresolved_template_count === 0, "Handoff left unresolved templates.");
  assert(state.classification_count === 6 && state.accepted_reuse_count === 6, "Accepted page assignments are incomplete.");
  assert(state.assembly_count === 5 && state.draft_reuse_count === 5, "Draft assembly rows are incomplete.");
  assert(state.extracted_document_count === 0, "Handoff created extracted documents.");

  const { rows: beforeRerun } = await client.query(`
    SELECT
      max(pc.page_classification_id)::text AS max_classification_id,
      max(pda.package_document_assembly_id)::text AS max_assembly_id
    FROM documents.source_document sd
    LEFT JOIN documents.source_page sp ON sp.source_document_id = sd.source_document_id
    LEFT JOIN documents.page_classification pc ON pc.source_page_id = sp.source_page_id
    LEFT JOIN documents.package_document_assembly pda ON pda.source_document_id = sd.source_document_id
    WHERE sd.source_document_id = $1
  `, [ephemeral.sourceDocumentId]);
  const secondResponse = await fetch(endpoint, { method: "POST" });
  const second = await secondResponse.json();
  assert(secondResponse.ok && second.reuseHandoff?.reused === true, "Repeated handoff was not idempotent.");
  const { rows: afterRerun } = await client.query(`
    SELECT
      max(pc.page_classification_id)::text AS max_classification_id,
      max(pda.package_document_assembly_id)::text AS max_assembly_id
    FROM documents.source_document sd
    LEFT JOIN documents.source_page sp ON sp.source_document_id = sd.source_document_id
    LEFT JOIN documents.page_classification pc ON pc.source_page_id = sp.source_page_id
    LEFT JOIN documents.package_document_assembly pda ON pda.source_document_id = sd.source_document_id
    WHERE sd.source_document_id = $1
  `, [ephemeral.sourceDocumentId]);
  assert(
    JSON.stringify(beforeRerun[0]) === JSON.stringify(afterRerun[0]),
    "Repeated handoff created additional database rows.",
  );
  return state;
}

const port = await availablePort();
const client = new Client(databaseConfig);
await client.connect();
const controlsBefore = await controlFingerprint(client);
let ephemeral = null;
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
    AGENDA_PACKAGE_REUSE_PROFILE:
      "data/document-ingestion/profiles/charlottetown-council-public-meeting/v1/profile.json",
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
  ephemeral = await createEphemeralPositivePackage(client);
  const successfulHandoff = await verifySuccessfulHandoff(baseUrl, client, ephemeral);
  const positive = await preview(
    baseUrl,
    positivePackageKey,
  );
  assert(positive.status === "needs_review", "Positive package status is incorrect.");
  assert(positive.documents?.length === 5, "Positive package document count is incorrect.");
  assert(
    positive.documents.every((item) => item.fit_class === "exact"),
    "Positive package contains a non-exact document.",
  );
  assert(
    positive.coverage?.assigned_pages === 6
      && positive.coverage?.unknown_pages === 0
      && positive.coverage?.conflicting_pages === 0
      && positive.coverage?.omitted_pages === 0,
    "Positive package coverage is incomplete.",
  );

  const negative = await preview(
    baseUrl,
    negativePackageKey,
  );
  assert(negative.status === "blocked", "Negative package must remain blocked.");
  assert(
    negative.coverage?.total_pages === 453
      && negative.coverage?.omitted_pages === 0,
    "Negative package accounting is incomplete.",
  );
  assert(
    negative.documents.every(
      (item) => item.policy_evaluation?.outcome !== "auto_approved",
    ),
    "Negative package contains an automatic approval.",
  );
  await blockedHandoff(
    baseUrl,
    negativePackageKey,
    "Reuse-preview handoff requires complete, conflict-free package coverage.",
  );
  await blockedHandoff(
    baseUrl,
    positivePackageKey,
    "An approved package assembly already exists.",
  );
  console.log(JSON.stringify({
    positive: {
      status: positive.status,
      documents: positive.documents.length,
      coverage: positive.coverage,
    },
    negative: {
      status: negative.status,
      documents: negative.documents.length,
      coverage: negative.coverage,
    },
    handoffGuards: {
      blockedNegative: true,
      preservedApprovedAssembly: true,
    },
    successfulHandoff: {
      classifications: successfulHandoff.accepted_reuse_count,
      draftAssemblyDocuments: successfulHandoff.draft_reuse_count,
      extractedDocuments: successfulHandoff.extracted_document_count,
      idempotentRerun: true,
    },
  }, null, 2));
} catch (error) {
  error.message = `${error.message}\n${diagnostics}`;
  throw error;
} finally {
  await stopServer(child);
  if (ephemeral) {
    await client.query(
      "DELETE FROM documents.source_document WHERE source_document_id = $1",
      [ephemeral.sourceDocumentId],
    );
  }
  const controlsAfter = await controlFingerprint(client);
  assert(controlsAfter === controlsBefore, "Permanent control package rows changed during live verification.");
  if (ephemeral) {
    const { rows } = await client.query(`
      SELECT count(*)::integer AS remaining
      FROM documents.source_document
      WHERE source_document_key = $1
    `, [ephemeral.packageKey]);
    assert(rows[0].remaining === 0, "Ephemeral live-verification package was not removed.");
  }
  await client.end();
}
