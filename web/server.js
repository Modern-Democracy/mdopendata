import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = process.env.REPO_ROOT || path.resolve(__dirname, "..");
const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT || 3000);

const ledgerPath = path.join(
  repoRoot,
  "data",
  "zoning",
  "charlottetown-draft",
  "review",
  "section-equivalence-review.csv",
);

const publicDir = path.join(__dirname, "public");
const jsonCache = new Map();

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char;
    }
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  const [headers, ...records] = rows;
  return records
    .filter((record) => record.length === headers.length)
    .map((record) =>
      Object.fromEntries(headers.map((header, index) => [header, record[index] ?? ""])),
    );
}

function parseSectionKey(sectionKey) {
  const parts = sectionKey.split("|");
  const fileIndex = parts.indexOf("file");
  const sectionIndex = parts.indexOf("section");
  return {
    filePath: fileIndex >= 0 ? parts[fileIndex + 1] : "",
    sectionId: sectionIndex >= 0 ? parts[sectionIndex + 1] : "",
  };
}

async function loadJson(repoRelativePath) {
  const normalized = path.normalize(repoRelativePath);
  const absolute = path.resolve(repoRoot, normalized);
  if (!absolute.startsWith(path.resolve(repoRoot))) {
    throw new Error("Refusing to read outside repository root.");
  }
  if (!jsonCache.has(absolute)) {
    jsonCache.set(absolute, JSON.parse(await readFile(absolute, "utf8")));
  }
  return jsonCache.get(absolute);
}

async function loadSection(sectionKey) {
  const parsed = parseSectionKey(sectionKey);
  if (!parsed.filePath || !parsed.sectionId) {
    return null;
  }
  const document = await loadJson(parsed.filePath);
  const sections = document.raw_data?.sections_raw ?? [];
  const section = sections.find((candidate) => candidate.section_id === parsed.sectionId);
  if (!section) {
    return null;
  }
  return {
    filePath: parsed.filePath,
    sectionId: parsed.sectionId,
    label: section.section_label_raw,
    title: section.section_title_raw,
    citations: section.citations ?? {},
    clauses: (section.clauses_raw ?? []).map((clause) => ({
      label: clause.clause_label_raw,
      text: clause.clause_text_raw,
      citations: clause.citations ?? {},
      sourceOrder: clause.source_order,
    })),
  };
}

async function loadReviewRows() {
  const csv = await readFile(ledgerPath, "utf8");
  return parseCsv(csv).map((row, index) => ({
    ...row,
    row_index: index,
  }));
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

async function serveStatic(response, requestPath) {
  const safePath = requestPath === "/" ? "/index.html" : requestPath;
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
  };

  try {
    const body = await readFile(absolute);
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
      await sendJson(response, { source: ledgerPath, rows: summarizeRows(rows) });
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
        loadSection(row.current_section_key),
        loadSection(row.draft_section_key),
      ]);
      await sendJson(response, { row, currentSection, draftSection });
      return;
    }

    await serveStatic(response, url.pathname);
  } catch (error) {
    response.writeHead(500, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ error: error.message }));
  }
});

server.listen(port, host, () => {
  console.log(`mdopendata web listening on http://${host}:${port}`);
});
