#!/usr/bin/env node

import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const webRoot = path.join(root, "web");

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
    if (child.exitCode !== null) throw new Error(`Review server exited with ${child.exitCode}.`);
    try {
      await fetch(`${baseUrl}/internal/pdf-inventory-review`);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error("Review server did not start.");
}

async function stopServer(child) {
  if (child.exitCode !== null) return;
  child.kill();
  await Promise.race([
    new Promise((resolve) => child.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

async function withServer(environment, checks) {
  const port = await availablePort();
  const child = spawn(process.execPath, ["server.js"], {
    cwd: webRoot,
    env: {
      ...process.env,
      REPO_ROOT: root,
      HOST: "127.0.0.1",
      PORT: String(port),
      PDF_INVENTORY_REVIEW_ENABLED: "0",
      PDF_INVENTORY_REVIEW_WRITE_ENABLED: "0",
      DEMO_MODE: "0",
      ...environment,
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
    await checks(baseUrl);
  } catch (error) {
    error.message = `${error.message}\n${diagnostics}`;
    throw error;
  } finally {
    await stopServer(child);
  }
}

async function expectStatus(baseUrl, requestPath, status, options) {
  const response = await fetch(`${baseUrl}${requestPath}`, options);
  assert(response.status === status, `${requestPath} returned ${response.status}; expected ${status}.`);
  return response;
}

await withServer({}, async (baseUrl) => {
  const portal = await expectStatus(baseUrl, "/", 200);
  assert((await portal.text()).includes("Municipal portal"), "Existing portal route regressed.");
  const context = await expectStatus(baseUrl, "/api/portal/context?role=staff&route=/documents", 200);
  assert((await context.json()).rolePreset === "staff", "Existing portal context API regressed.");
  await expectStatus(baseUrl, "/internal/pdf-inventory-review", 404);
  await expectStatus(baseUrl, "/pdf-inventory-review/app.js", 404);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 404);
  console.log("ok - disabled routes are unavailable");
});

await withServer({
  PDF_INVENTORY_REVIEW_ENABLED: "1",
  DEMO_MODE: "1",
  HOST: "0.0.0.0",
}, async (baseUrl) => {
  await expectStatus(baseUrl, "/internal/pdf-inventory-review", 404);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 404);
  console.log("ok - demo mode denies review routes");
});

await withServer({ PDF_INVENTORY_REVIEW_ENABLED: "1", HOST: "0.0.0.0" }, async (baseUrl) => {
  await expectStatus(baseUrl, "/internal/pdf-inventory-review", 404);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 404);
  console.log("ok - non-loopback bind denies review routes");
});

await withServer({ PDF_INVENTORY_REVIEW_ENABLED: "1" }, async (baseUrl) => {
  const shell = await expectStatus(baseUrl, "/internal/pdf-inventory-review?page=24", 200);
  const shellText = await shell.text();
  assert(shellText.includes("PDF inventory review"), "Review shell title is missing.");
  assert(shellText.includes("app.js"), "Review shell script is missing.");
  assert(shellText.includes("Draw new box"), "Stage 1 edit controls are missing.");
  assert(shellText.includes("Content associations"), "Stage 1 relationship controls are missing.");
  assert(shellText.includes("Cancel source"), "Association source cancellation is missing.");
  assert(shellText.includes("Edit internal structure"), "Internal-region controls are missing.");
  assert(shellText.includes("Redetect table grid"), "Table grid redetection control is missing.");
  assert(shellText.includes("Redetect table grid after resize"), "Resize grid-redetection option is missing.");
  assert(shellText.includes("Apply cell span"), "Version 2 cell-span control is missing.");
  assert(shellText.includes("Row span"), "Row-span input is missing.");
  assert(shellText.includes("Column span"), "Column-span input is missing.");
  assert(shellText.includes("Find similar"), "Document propagation discovery control is missing.");
  assert(shellText.includes("Apply selected"), "Document propagation apply control is missing.");
  assert(shellText.includes("Reject selected"), "Document propagation rejection control is missing.");
  assert(shellText.includes("Promote template"), "Immutable-template promotion control is missing.");
  assert(shellText.includes("Sample review"), "Sample-review policy control is missing.");
  assert(shellText.includes("Auto approve"), "Automatic-approval policy control is missing.");
  assert(shellText.includes("Suspend policy"), "Policy suspension control is missing.");
  for (const selectionLabel of ["Cell", "Row", "Column"]) {
    assert(shellText.includes(`>${selectionLabel}</button>`), `${selectionLabel} selection control is missing.`);
  }
  const appScript = await (await expectStatus(baseUrl, "/pdf-inventory-review/app.js", 200)).text();
  assert(appScript.includes("payload.page_updates"), "The client does not apply incremental page updates.");
  assert(!appScript.includes("await initialize();"), "The client still performs a full reload after every write.");
  assert(appScript.includes("associationSelection"), "Relationship-aware endpoint selection is missing.");
  assert(appScript.includes("if (result) { state.linkSource = null"), "Failed links would incorrectly clear the source selection.");
  assert(appScript.includes("effectiveSpan"), "Effective span rendering is missing.");
  assert(appScript.includes('"merge_table_cells"'), "Logical-cell merge command is missing.");
  assert(appScript.includes('"split_table_cell"'), "Logical-cell split command is missing.");
  assert(appScript.includes('"set_table_cell_span"'), "Explicit span command is missing.");
  assert(appScript.includes('["table_title", "Table Title"]'), "Table-title cell control is missing.");
  assert(appScript.includes('["title", "Title"]'), "Formatted-text title control is missing.");
  assert(appScript.includes("propagation-preview"), "Propagation preview API integration is missing.");
  assert(appScript.includes('"apply_template"'), "Atomic propagation command is missing.");
  assert(appScript.includes('"auto_approve"'), "Policy-governed automatic command is missing.");
  assert(appScript.includes("template-policy"), "Template-policy API integration is missing.");
  const expectedTypeOrder = ['["title", "Title"]', '["formatted_text", "Formatted Text"]', '["table", "Table"]', '["chart", "Graph/Chart"]', '["other_visual", "Diagram/Other Visual"]', '["map", "Map"]', '["table_of_contents", "Table of Contents"]', '["header", "Header"]', '["footer", "Footer"]', '["page_number", "Page Number"]', '["divider", "Divider"]', '["signature", "Signature"]'];
  let priorTypePosition = -1;
  for (const typeText of expectedTypeOrder) {
    const position = appScript.indexOf(typeText);
    assert(position > priorTypePosition, `Block type is missing or out of order: ${typeText}`);
    priorTypePosition = position;
  }

  const documentsResponse = await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 200);
  assert(documentsResponse.headers.get("cache-control") === "no-store", "Document API must use no-store.");
  const documents = await documentsResponse.json();
  const document = documents.documents?.[0];
  assert(document?.document_key === "ctown-budget-2026-2027", "Pilot document key is incorrect.");
  assert(document?.schema_version === 1, "Default reviewer must remain on schema version 1.");
  assert(document?.page_count === 154, "Pilot page count is incorrect.");
  assert(document?.complete_page_count === 154, "Complete page count is incorrect.");
  assert(document?.blocked_page_count === 0, "Blocked page count is incorrect.");
  assert(document?.ocr_page_count === 1, "OCR page count is incorrect.");
  assert(Number.isInteger(document?.block_count) && document.block_count > 0, "Stage 1 reviewed block count is invalid.");
  assert(Number.isInteger(document?.financial_block_count) && document.financial_block_count <= document.block_count, "Stage 1 financial candidate count is invalid.");
  assert(Number.isInteger(document?.block_review_page_count) && document.block_review_page_count >= 0, "Stage 1 review-page count is invalid.");
  assert(Number.isInteger(document?.relationship_count) && document.relationship_count >= 0, "Stage 1 relationship count is invalid.");
  assert(document?.validation?.status === "valid", "Canonical validation did not pass.");

  const artifactResponse = await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/artifacts",
    200,
  );
  const artifact = await artifactResponse.json();
  assert(artifact.artifact?.artifact_type === "source_evidence", "Artifact type is incorrect.");
  assert(artifact.artifact?.source?.page_count === 154, "Artifact source page count is incorrect.");
  assert(artifact.block_artifact?.artifact_type === "block_inventory", "Stage 1 artifact type is incorrect.");
  assert(artifact.block_artifact?.block_count === document.block_count, "Stage 1 artifact block count disagrees with the document summary.");

  const pagesResponse = await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/pages",
    200,
  );
  const pages = await pagesResponse.json();
  assert(pages.pages?.length === 154, "Page inventory does not contain 154 pages.");
  assert(pages.pages.reduce((total, page) => total + page.block_count, 0) === document.block_count, "Page block counts disagree with the document summary.");
  assert(pages.pages.reduce((total, page) => total + page.financial_block_count, 0) === document.financial_block_count, "Page financial counts disagree with the document summary.");
  const page24 = pages.pages.find((page) => page.page_number === 24);
  assert(page24?.embedded_word_count === 4, "Page 24 embedded-word count is incorrect.");
  assert(page24?.ocr_status === "completed", "Page 24 OCR fallback is missing.");
  assert(page24?.ocr_word_count > 4, "Page 24 OCR evidence count is missing.");
  assert(page24?.block_count > 0, "Page 24 Stage 1 blocks are missing.");
  assert(page24?.block_inventory_status === "needs_review", "Page 24 Stage 1 status is incorrect.");
  assert(pages.pages.filter((page) => page.ocr_status === "completed").length === 1, "Unexpected OCR pages found.");

  const detailResponse = await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/pages/24",
    200,
  );
  const detail = await detailResponse.json();
  assert(detail.page?.page_key === "ctown-budget-2026-2027:p024", "Page 24 key is incorrect.");
  assert(detail.evidence?.ocr?.status === "completed", "Page 24 OCR detail is incorrect.");
  assert(detail.block_inventory?.blocks?.length === page24.block_count, "Page 24 block detail is inconsistent.");
  assert(Array.isArray(detail.block_inventory?.relationships), "Stage 1 page relationships are missing.");

  const page10 = await (await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/pages/10", 200)).json();
  const page10Text = page10.block_inventory.blocks.find((block) => block.block_type === "formatted_text");
  assert(page10Text?.regions?.length > 0, "Formatted-text internal regions are missing on page 10.");

  const renderResponse = await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/assets/render/24",
    200,
  );
  assert(renderResponse.headers.get("content-type") === "image/png", "Render content type is incorrect.");
  assert(renderResponse.headers.get("x-content-sha256") === detail.evidence.render.sha256, "Render hash header is incorrect.");
  assert((await renderResponse.arrayBuffer()).byteLength > 10000, "Render asset is empty.");

  const embeddedResponse = await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/assets/embedded-words/24",
    200,
  );
  const embedded = await embeddedResponse.json();
  assert(embedded.word_count === 4 && embedded.words?.length === 4, "Embedded-word evidence is incorrect.");

  const ocrResponse = await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/assets/ocr-words/24",
    200,
  );
  const ocr = await ocrResponse.json();
  assert(ocr.word_count === page24.ocr_word_count, "OCR-word evidence count is inconsistent.");

  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents/unknown/pages/24", 404);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/pages/0", 404);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/assets/file/24", 404);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents?path=../docs", 400);
  await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 405, { method: "POST" });
  await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/commands",
    403,
    { method: "POST", headers: { "content-type": "application/json" }, body: "{}" },
  );
  console.log("ok - enabled Stage 0 and Stage 1 read APIs");
});

await withServer({
  PDF_INVENTORY_REVIEW_ENABLED: "1",
  PDF_INVENTORY_REVIEW_SCHEMA_VERSION: "2",
}, async (baseUrl) => {
  const documents = await (
    await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 200)
  ).json();
  const document = documents.documents?.[0];
  assert(document?.schema_version === 2, "Explicit version 2 reviewer did not load the shadow workspace.");
  assert(document?.page_count === 154, "Version 2 reviewer page count is incorrect.");
  const artifacts = await (
    await expectStatus(
      baseUrl,
      "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/artifacts",
      200,
    )
  ).json();
  assert(artifacts.artifact?.schema_version === 2, "Version 2 source artifact is not active.");
  assert(artifacts.block_artifact?.schema_version === 2, "Version 2 block artifact is not active.");
  assert(artifacts.review_artifact?.schema_version === 2, "Version 2 review artifact is not active.");
  const beforeBlockHash = document.block_artifact_sha256;
  const beforeReviewHash = document.review_artifact_sha256;
  const preview = await (
    await expectStatus(
      baseUrl,
      "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/propagation-preview",
      200,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          document_key: "ctown-budget-2026-2027",
          source_block_key: "ctown-budget-2026-2027:p018:body",
          expected_artifact_sha256: beforeBlockHash,
          expected_review_artifact_sha256: beforeReviewHash,
        }),
      },
    )
  ).json();
  assert(preview.scope === "current_document", "Propagation preview escaped document scope.");
  assert(preview.candidates.some((candidate) => candidate.applicable), "Propagation preview found no positive control.");
  assert(preview.candidates.some((candidate) => candidate.fit_class === "material_variation"), "Propagation preview found no material negative control.");
  assert(preview.candidates.every((candidate) => candidate.policy_evaluation?.outcome === "review_required"), "Unregistered patterns must require review.");
  assert(preview.registry?.template === null && preview.registry?.policy === null, "Canonical pilot unexpectedly contains promoted template policy artifacts.");
  const registry = await (
    await expectStatus(
      baseUrl,
      "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/template-policy",
      200,
    )
  ).json();
  assert(Array.isArray(registry.templates) && registry.templates.length === 0, "Canonical template registry is not empty.");
  assert(Array.isArray(registry.policies) && registry.policies.length === 0, "Canonical policy registry is not empty.");
  await expectStatus(
    baseUrl,
    "/api/internal/pdf-inventory-review/documents/ctown-budget-2026-2027/template-policy",
    403,
    { method: "POST", headers: { "content-type": "application/json" }, body: "{}" },
  );
  const after = (await (await expectStatus(baseUrl, "/api/internal/pdf-inventory-review/documents", 200)).json()).documents[0];
  assert(after.block_artifact_sha256 === beforeBlockHash, "Propagation preview changed the block artifact.");
  assert(after.review_artifact_sha256 === beforeReviewHash, "Propagation preview changed the review artifact.");
  console.log("ok - explicit version 2 shadow workspace is readable");
});
